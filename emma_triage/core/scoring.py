import json
from openai import AsyncOpenAI
from models.schemas import TriageSession, TriageOutput
from config import OPENAI_API_KEY, CONFIDENCE_THRESHOLD

client=AsyncOpenAI(api_key=OPENAI_API_KEY)

#Routing Map logic
ROUTING_MAP = {
    "L3":"urgent_appointment",
    "L4":"standard_appointment",
    "L5":"telehealth"
}

ESCALATION_MAP={
    "L1":"911",
    "L2":"911"
}

#Helper func to transcript for scoring
def format_transcript(transcript: list[dict])->str:
    """
    Converts raw transcript list into a readable string
    for the scoring prompt.
    """
    lines=[]
    for entry in transcript:
        role = entry.get("role","unknown").upper()
        text = entry.get("text","")
        lines.append(f"{role}:{text}")
    
    return "\n".join(lines)

#STAGE 2: LLM Clinical Reasoning
async def run_stage_2(session: TriageSession) -> dict:
    """
    Sends collected patient data to OpenAI for clinical scoring.
    OpenAI can ONLY return L3, L4, or L5.
    Returns parsed and L1/L2 validated dict from response.
    """
    patient_data = session.collected_data.model_dump_json(indent=2)
    transcript_summary = format_transcript(session.transcript)
    
    prompt = f"""
                You are a clinical triage scoring engine for a medical voice assistant.
                Analyze the patient data below and assign a triage level.

                CRITICAL RULES:
                - You can ONLY return L3, L4, or L5 as triage_level
                - NEVER return L1 or L2 — those are handled by a separate safety system
                - Return ONLY valid JSON matching the output schema below
                - No preamble, no explanation outside the JSON
                - No markdown, no code blocks

                Patient Collected Data:
                {patient_data}

                Conversation Summary:
                {transcript_summary}

                Output Schema — return exactly this structure:
                {{
                    "triage_level": "L3 or L4 or L5 only",
                    "confidence": 0.0 to 1.0,
                    "clinical_reasoning": "narrative explanation for clinician audit",
                    "recommended_speciality": "e.g. General Practice, Cardiology, or null",
                    "recommended_timeframe": "e.g. Within 30 minutes, Today, This week",
                    "follow_up_flags": ["list of conditions to watch for"],
                    "self_care_guidance": "for L4/L5 only, or null",
                    "review_flag": true or false,
                    "differential_notes": "alternative diagnoses considered, or null"
                }}

                Return JSON only:"""
    
    response = await client.chat.completions.create(
    model="gpt-5-mini",
    max_completion_tokens=2000,
    messages=[
        {
            "role": "system",
            "content": "You are a clinical triage scoring engine. Always respond with valid JSON only. No markdown, no code blocks, no explanation."
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    )
    
    # Debug info
    finish_reason = response.choices[0].finish_reason
    raw = response.choices[0].message.content
    refusal = response.choices[0].message.refusal

    print(f"[FINISH REASON] {finish_reason}")
    print(f"[REFUSAL] {refusal}")
    print(f"[RAW CONTENT] '{raw}'")

    # Check for None or empty BEFORE any string operations
    if not raw:
        raise ValueError(
            f"Model returned empty response. "
            f"Finish reason: {finish_reason} | "
            f"Refusal: {refusal}"
        )

    raw = raw.strip()

    # Strip markdown if model wraps in code blocks
    if raw.startswith("```"):
        parts = raw.split("```")
        raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]

    raw = raw.strip()

    print(f"[SCORING CLEANED] '{raw[:100]}'")

    if not raw:
        raise ValueError("Model returned empty response after markdown stripping")

    result = json.loads(raw)
    
    return result

#STAGE 3: CONFIDENCE GATE
def run_stage_3(stage_2_result:dict) -> dict:
    """
    Evaluates confidence score against threshold from config.
    If below threshold, flags for clinician review.
    Does not modify triage level — only sets review_required.
    """
    confidence = stage_2_result.get("confidence",0.0)
    
    if confidence<CONFIDENCE_THRESHOLD:
        stage_2_result["review_required"]=True
    else:
        stage_2_result["review_required"]=False
    
    return stage_2_result

#FINAL OUTPUT ASSEMBLY
def assemble_output(
    stage_2_result: dict,
    session: TriageSession
) -> TriageOutput:
    """
    Combines Stage 2 and Stage 3 results with session metadata
    into a final TriageOutput object.
    escalation_required will always be False here since L1/L2
    are blocked from reaching this function.
    """
    triage_level = stage_2_result.get("triage_level", "L3")
    escalation_required = triage_level in ["L1", "L2"]
    routing_action = ROUTING_MAP.get(triage_level, "standard_appointment")

    return TriageOutput(
        triage_level=triage_level,
        confidence=stage_2_result.get("confidence", 0.0),
        routing_action=routing_action,
        escalation_required=escalation_required,
        escalation_contact=ESCALATION_MAP.get(triage_level, None),
        recommended_speciality=stage_2_result.get("recommended_speciality"),
        self_care_guidance=stage_2_result.get("self_care_guidance"),
        stage_1_rule_triggered=session.escalated,
        rule_id=None,
        review_required=stage_2_result.get("review_required", False),
        llm_reasoning_summary=stage_2_result.get("clinical_reasoning")
    )

# MAIN SCORING PIPELINE
#Called after reaching phase 7

async def run_scoring_pipeline(session: TriageSession) -> TriageOutput:
    """
    Runs Stage 2 → Stage 3 → assembles final output.
    Only called after phase 6 is complete and
    collected_data is fully or partially populated.
    """
    # Stage 2: LLM clinical reasoning
    stage_2_result = await run_stage_2(session)

    # Stage 3: confidence gate
    stage_2_result = run_stage_3(stage_2_result)

    # Assemble final output
    output = assemble_output(stage_2_result, session)

    return output