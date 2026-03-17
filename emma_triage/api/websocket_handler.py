import json
import asyncio
import httpx
import websockets
from openai import AsyncOpenAI
from models.schemas import TriageSession
from core.red_flag_engine import check_red_flag, get_emergency_script
from core.state_machine import (
    increment_turn,
    should_advance_phase,
    advance_phase,
    update_collected_data,
    is_session_complete
)
from core.prompts import get_phase_prompt, get_extraction_prompt
from core.scoring import run_scoring_pipeline
from config import ULTRAVOX_API_KEY, ULTRAVOX_BASE_URL, OPENAI_API_KEY

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

#ULTRAVOX API HELPERS
async def update_ultravox_prompt(call_id: str, new_prompt: str):
    """
    Swaps the system prompt mid-call when phase advances.
    Uses Ultravox stage update endpoint.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ULTRAVOX_BASE_URL}/calls/{call_id}/stages",
            headers={
                "X-API-Key": ULTRAVOX_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "systemPrompt": new_prompt,
                "temperature": 0.3,
            }
        )
        return response.status_code == 200

async def inject_emergency_message(call_id: str, category: str):
    """
    Forces EMMA to say the hardcoded emergency script.
    Called immediately when red flag is detected.
    Does NOT rely on LLM — uses hardcoded script only.
    """
    script = get_emergency_script(category)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ULTRAVOX_BASE_URL}/calls/{call_id}/stages",
            headers={
                "X-API-Key": ULTRAVOX_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "systemPrompt": (
                    f"Say EXACTLY this and nothing else: '{script}' "
                    f"Then immediately hang up."
                ),
                "temperature": 0.0,
            }
        )
        return response.status_code == 200

async def end_ultravox_call(call_id: str):
    """
    Sends hangup signal to Ultravox.
    """
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{ULTRAVOX_BASE_URL}/calls/{call_id}",
            headers={"X-API-Key": ULTRAVOX_API_KEY}
        )
        return response.status_code == 200

#EXTRACTION: Pulls structured data from patient's input
async def extract_data_from_utterance(patient_text: str) -> dict:
    """
    Calls GPT-5-mini with extraction prompt to pull structured
    data from patient utterance.
    Returns dict of extracted fields. Empty dict if extraction fails.
    """
    try:
        prompt = get_extraction_prompt(patient_text)
        response = await openai_client.chat.completions.create(
            model="gpt-5-mini",
            max_completion_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content.strip()

        # Strip markdown if model wraps in code blocks
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        return json.loads(raw)

    except Exception as e:
        # Extraction failure is non-fatal — session continues
        # with whatever slots were already filled
        print(f"[EXTRACTION ERROR] {e}")
        return {}

# STAGE 1B: Async safety net
# Runs after every utterance — non-blocking
# Can only log alerts, cannot affect call routing
async def run_stage_1b(patient_text: str, session_id: str):
    """
    Secondary LLM safety check that runs async after Stage 1.
    Checks for L1/L2 signals Stage 1 may have missed due to
    unusual phrasing or culturally specific descriptions.
    CANNOT modify routing or delay patient response.
    Only logs alerts to console (dashboard in production).
    Target latency: under 3 seconds (non-blocking).
    """
    try:
        prompt = f"""You are a medical safety monitor.
                    Read the patient utterance below and determine if it contains
                    any life-threatening emergency signals that a keyword scanner
                    may have missed — unusual phrasing, indirect descriptions,
                    or culturally specific expressions of L1/L2 symptoms.

                    L1/L2 categories: cardiac, neurological, respiratory, trauma, mental health crisis.

                    Patient said: "{patient_text}"

                    Return JSON only:
                    {{
                        "l1_l2_detected": true or false,
                        "category": "cardiac | neurological | respiratory | trauma | mental_health | null",
                        "reasoning": "brief explanation or null",
                        "confidence": 0.0 to 1.0
                    }}"""
        
        response = await openai_client.chat.completions.create(
            model="gpt-5-mini",
            max_completion_tokens=200,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        
        # Log alert if Stage 1b detects something Stage 1 missed
        if result.get("l1_l2_detected"):
            print(
                f"[STAGE_1B_ALERT] session={session_id} "
                f"category={result.get('category')} "
                f"confidence={result.get('confidence')} "
                f"reasoning={result.get('reasoning')}"
            )

    except Exception as e:
        # Stage 1b failure is non-fatal
        print(f"[STAGE_1B_ERROR] {e}")

######################
#MAIN WEBSOCKET HANDLER
#######################
async def handle_ultravox_session(join_url: str,call_id: str,session: TriageSession,active_sessions: dict):
    """
    Main runtime loop for a single triage call.
    Connects to Ultravox WebSocket and processes all events.
    Wires together: red flag engine, state machine,
    extraction, scoring pipeline.
    """
    print(f"[SESSION START] session_id={session.session_id}")

    try:
        async with websockets.connect(join_url) as ws:
            async for raw_message in ws:
                event = json.loads(raw_message)
                event_type = event.get("type")

                # ── Call ended by Ultravox ──
                if event_type == "state":
                    if event.get("state") == "ended":
                        print(f"[CALL ENDED] session_id={session.session_id}")
                        session.active = False
                        active_sessions[session.session_id] = session
                        break

                # ── Transcript event ──
                if event_type == "transcript":
                    role = event.get("role")
                    is_final = event.get("final", False)
                    text = event.get("text", "").strip()

                    # Skip non-final or empty transcripts
                    if not is_final or not text:
                        continue
                    
                    # Log EMMA utterances to transcript only
                    if role == "agent":
                        session.transcript.append({
                            "role": "agent",
                            "text": text
                        })
                        active_sessions[session.session_id] = session
                        continue
                    
                     # ── Patient utterance — full pipeline ──
                    if role == "user":
                        print(f"[USER] {text}")

                        ######
                        #STAGE 1: RED FLAG CHECK
                        # Runs synchronously — nothing else happens
                        # until this returns
                        ######
                        flagged, category, matched_term = check_red_flag(text)

                        if flagged:
                            print(
                                f"[RED FLAG] category={category} "
                                f"matched='{matched_term}'"
                            )

                            # Log to session
                            session.escalated = True
                            session.active = False
                            session.collected_data.red_flags_triggered.append(
                                matched_term
                            )
                            session.transcript.append({
                                "role": "user",
                                "text": text,
                                "red_flag": True,
                                "category": category
                            })
                            active_sessions[session.session_id] = session

                            # Inject emergency script into Ultravox
                            await inject_emergency_message(call_id, category)

                            # Stage 1b fires async — non-blocking
                            # Even on flag, runs to catch any additional signals
                            asyncio.create_task(
                                run_stage_1b(text, session.session_id)
                            )

                            # End the call
                            await asyncio.sleep(8)  # let emergency script play
                            await end_ultravox_call(call_id)
                            break
                        
                        ########
                        #STAGE 1B: Async safety net
                        # Fires immediately, non-blocking
                        ########
                        asyncio.create_task(
                            run_stage_1b(text, session.session_id)
                        )

                        #####
                        #EXTRACTION: Pull structured data
                        #####
                        extracted = await extract_data_from_utterance(text)
                        if extracted:
                            session = update_collected_data(session, extracted)
                            print(f"[EXTRACTED] {extracted}")
                        
                        #######
                        #STATE MACHINE: Turn + phase logic
                        #######
                        session = increment_turn(session)

                        session.transcript.append({
                            "role": "user",
                            "text": text
                        })
                        
                        # Check phase advance
                        if should_advance_phase(session):
                            session = advance_phase(session)
                            print(
                                f"[PHASE ADVANCE] → phase {session.current_phase}"
                            )

                            # Update Ultravox with new phase prompt
                            new_prompt = get_phase_prompt(session.current_phase)
                            await update_ultravox_prompt(call_id, new_prompt)
                        
                        #######
                        # SCORING: Run when phase 7 is reached
                        #######
                        if session.current_phase == 7 and session.turns_in_phase == 0:
                            print(f"[SCORING] Running pipeline...")
                            try:
                                output = await run_scoring_pipeline(session)
                                print(
                                    f"[TRIAGE RESULT] "
                                    f"level={output.triage_level} "
                                    f"confidence={output.confidence} "
                                    f"routing={output.routing_action} "
                                    f"review={output.review_required}"
                                )

                                # Update phase 7 prompt with triage result
                                result_prompt = (
                                    get_phase_prompt(7) +
                                    f"\n\nTriage Level: {output.triage_level}"
                                    f"\nRouting: {output.routing_action}"
                                    f"\nTimeframe: {output.review_required}"
                                )
                                await update_ultravox_prompt(call_id, result_prompt)

                            except Exception as e:
                                print(f"[SCORING ERROR] {e}")
                                
                        # Save updated session
                        active_sessions[session.session_id] = session

                        # Check if session is complete
                        if is_session_complete(session):
                            print(
                                f"[SESSION COMPLETE] "
                                f"session_id={session.session_id}"
                            )
                            session.active = False
                            active_sessions[session.session_id] = session
                            break
    except websockets.exceptions.ConnectionClosed:
        print(f"[WS CLOSED] session_id={session.session_id}")
        session.active = False
        active_sessions[session.session_id] = session

    except Exception as e:
        print(f"[SESSION ERROR] session_id={session.session_id} error={e}")
        session.active = False
        active_sessions[session.session_id] = session

    print(f"[SESSION END] session_id={session.session_id}")            