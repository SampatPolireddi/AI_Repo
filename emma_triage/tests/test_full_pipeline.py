import asyncio
from models.schemas import TriageSession
from core.red_flag_engine import check_red_flag, get_emergency_script
from core.state_machine import (
    increment_turn,
    should_advance_phase,
    advance_phase,
    update_collected_data,
    is_session_complete
)
from core.prompts import get_extraction_prompt, get_phase_prompt
from core.scoring import run_scoring_pipeline
from openai import AsyncOpenAI
from config import OPENAI_API_KEY
import json
import os
from datetime import datetime

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ============================================================
# TRANSCRIPT SAVER
# ============================================================

def save_transcript(content: str, test_name: str):
    """Saves test output to a timestamped file in test_outputs/"""
    os.makedirs("test_outputs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = test_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"test_outputs/{safe_name}_{timestamp}.txt"
    with open(filename, "w") as f:
        f.write(content)
    print(f"\n📄 Transcript saved to: {filename}")


# ============================================================
# SIMULATED CONVERSATION
# Mimics a real patient going through all 8 phases
# ============================================================

SIMULATED_CONVERSATION = [
    # Phase 1 - Greeting & Consent
    "English please",
    "Yes I consent",

    # Phase 2 - Chief Complaint
    "I have a bad headache",
    "It's behind my eyes and forehead",
    "It came on gradually over the past day",

    # Phase 3 - OPQRST
    "It started yesterday afternoon",
    "Bright light makes it worse, lying down helps a bit",
    "It feels like a throbbing pressure",
    "It doesn't really spread anywhere",
    "I'd say about a 6 out of 10",
    "It's been going on for about 18 hours now",

    # Phase 4 - Associated Symptoms
    "I also have some nausea and sensitivity to light, no fever though",

    # Phase 5 - Medical History
    "I have a history of migraines, I take sumatriptan when they happen",
    "No allergies",
    "No recent hospitalizations",

    # Phase 6 - Patient Details
    "I'm an adult, around 35",
    "No I'm not pregnant",
]

# ============================================================
# RED FLAG TEST CONVERSATION
# Tests that red flag engine interrupts correctly
# ============================================================

RED_FLAG_CONVERSATION = [
    "English please",
    "Yes I consent",
    "I have chest pain and I can't breathe",  # should trigger here
    "It's getting worse",                      # should never reach here
]


# ============================================================
# EXTRACTION HELPER
# ============================================================

async def extract_data(patient_text: str) -> dict:
    """Runs extraction prompt against patient utterance."""
    try:
        prompt = get_extraction_prompt(patient_text)
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            max_completion_tokens=300,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.choices[0].message.content
        if not raw:
            return {}
        raw = raw.strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"  [EXTRACTION ERROR] {e}")
        return {}


# ============================================================
# MAIN SIMULATION
# ============================================================

async def simulate_conversation(conversation: list[str], test_name: str):
    """
    Simulates a full patient conversation through the pipeline.
    No Ultravox, no voice — pure text simulation.
    Saves full transcript to test_outputs/ folder.
    """
    header = f"\n{'='*60}\nTEST: {test_name}\n{'='*60}\n"
    print(header)
    transcript_log = header

    session = TriageSession()
    session.session_id = "test-session-001"

    for i, patient_text in enumerate(conversation):

        turn_header = (
            f"\n[TURN {i+1}] Patient: '{patient_text}'\n"
            f"  Phase: {session.current_phase} | "
            f"Turn in phase: {session.turns_in_phase}"
        )
        print(turn_header)
        transcript_log += turn_header + "\n"

        # ── STAGE 1: Red Flag Check ──
        flagged, category, matched_term = check_red_flag(patient_text)

        if flagged:
            flag_output = (
                f"  🚨 RED FLAG TRIGGERED\n"
                f"  Category:         {category}\n"
                f"  Matched term:     '{matched_term}'\n"
                f"  Emergency Script: {get_emergency_script(category)}\n"
                f"\n  ❌ CALL ESCALATED — pipeline stopped"
            )
            print(flag_output)
            transcript_log += flag_output + "\n"
            session.escalated = True
            session.active = False

            final_state = (
                f"\n--- FINAL SESSION STATE ---\n"
                f"Phase reached:  {session.current_phase}\n"
                f"Escalated:      {session.escalated}\n"
                f"Red flags:      {session.collected_data.red_flags_triggered}\n"
            )
            print(final_state)
            transcript_log += final_state

            save_transcript(transcript_log, test_name)
            return session

        # ── Extraction ──
        extracted = await extract_data(patient_text)
        if extracted:
            ext_line = f"  Extracted: {extracted}"
            print(ext_line)
            transcript_log += ext_line + "\n"
            session = update_collected_data(session, extracted)

        # ── State Machine ──
        session = increment_turn(session)

        if should_advance_phase(session):
            old_phase = session.current_phase
            session = advance_phase(session)
            advance_line = (
                f"  ✅ PHASE ADVANCE: {old_phase} → {session.current_phase}"
            )
            print(advance_line)
            transcript_log += advance_line + "\n"

        # ── Scoring at phase 7 ──
        if session.current_phase == 7 and session.turns_in_phase == 0:
            scoring_header = "\n  🏥 RUNNING SCORING PIPELINE..."
            print(scoring_header)
            transcript_log += scoring_header + "\n"

            try:
                output = await run_scoring_pipeline(session)
                scoring_output = (
                    f"  Triage Level:           {output.triage_level}\n"
                    f"  Confidence:             {output.confidence}\n"
                    f"  Routing:                {output.routing_action}\n"
                    f"  Review Needed:          {output.review_required}\n"
                    f"  Recommended Speciality: {output.recommended_speciality}\n"
                    f"  Reasoning:              {output.llm_reasoning_summary}\n"
                )
                print(scoring_output)
                transcript_log += scoring_output + "\n"

            except Exception as e:
                error_line = f"  [SCORING ERROR] {e}"
                print(error_line)
                transcript_log += error_line + "\n"

        # ── Session complete ──
        if is_session_complete(session):
            complete_line = "\n  ✅ SESSION COMPLETE"
            print(complete_line)
            transcript_log += complete_line + "\n"
            break

    # ── Final session state ──
    final_state = (
        f"\n--- FINAL SESSION STATE ---\n"
        f"Phase reached:       {session.current_phase}\n"
        f"Escalated:           {session.escalated}\n"
        f"Chief complaint:     {session.collected_data.chief_complaint}\n"
        f"Body location:       {session.collected_data.body_location}\n"
        f"Onset:               {session.collected_data.onset}\n"
        f"Pain severity:       {session.collected_data.pain_severity}\n"
        f"Pain quality:        {getattr(session.collected_data, 'pain_quality', 'N/A')}\n"
        f"Duration hours:      {session.collected_data.duration_hours}\n"
        f"Associated symptoms: {session.collected_data.associated_symptoms}\n"
        f"Medical history:     {session.collected_data.medical_history}\n"
        f"Medications:         {session.collected_data.medications}\n"
        f"Allergies:           {session.collected_data.allergies}\n"
        f"Age group:           {session.collected_data.age_group}\n"
        f"Red flags:           {session.collected_data.red_flags_triggered}\n"
    )
    print(final_state)
    transcript_log += final_state

    save_transcript(transcript_log, test_name)
    return session


# ============================================================
# MAIN
# ============================================================

async def main():
    # Test 1: Normal full conversation
    await simulate_conversation(
        SIMULATED_CONVERSATION,
        "NORMAL TRIAGE FLOW - Headache Patient"
    )

    # Test 2: Red flag interruption
    await simulate_conversation(
        RED_FLAG_CONVERSATION,
        "RED FLAG INTERRUPTION - Cardiac Emergency"
    )


if __name__ == "__main__":
    asyncio.run(main())