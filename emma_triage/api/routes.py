import httpx
from fastapi import APIRouter, HTTPException
from models.schemas import TriageSession, CollectedData
from core.prompts import get_phase_prompt
from config import ULTRAVOX_API_KEY, ULTRAVOX_BASE_URL
import uuid

router = APIRouter()

#Local deployment
active_sessions:dict[str,TriageSession] = {}

#Helper func for ultravox call
async def create_ultravox_call(session_id:str)->dict:
    """
    Calls Ultravox API to create a new call.
    Returns the full response including joinUrl.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{ULTRAVOX_BASE_URL}/calls",
            headers={
                "X-API-Key": ULTRAVOX_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "systemPrompt": get_phase_prompt(1),
                "model": "fixie-ai/ultravox",
                "voice": "Mark",
                "temperature": 0.3,
                "firstSpeaker": "FIRST_SPEAKER_AGENT",
                "metadata": {"session_id": session_id}
            }
        )

        if response.status_code != 201:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Ultravox API error: {response.text}"
            )

        return response.json()

#POST calls
@router.post("/calls")
async def start_call():
    """
    Creates a new Ultravox call and a fresh TriageSession.
    Returns joinUrl for the frontend to connect the patient.
    """
     # Create fresh session
    session = TriageSession()
    session.session_id = str(uuid.uuid4())

    # Create Ultravox call
    ultravox_response = await create_ultravox_call(session.session_id)

    # Store call ID on session for later use
    call_id = ultravox_response.get("callId")
    join_url = ultravox_response.get("joinUrl")

    if not join_url:
        raise HTTPException(
            status_code=500,
            detail="Ultravox did not return a joinUrl"
        )

    # Store session in memory
    active_sessions[session.session_id] = session

    return {
        "session_id": session.session_id,
        "call_id": call_id,
        "join_url": join_url,
        "phase": session.current_phase,
        "phase_name": "Greeting & Consent"
    }
    
#GET calls
@router.get("/calls/{session_id}")
async def get_session(session_id: str):
    """
    Returns current state of a triage session.
    Useful for clinician dashboard monitoring.
    """
    session = active_sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    return {
        "session_id": session.session_id,
        "current_phase": session.current_phase,
        "turns_in_phase": session.turns_in_phase,
        "escalated": session.escalated,
        "active": session.active,
        "collected_data": session.collected_data.model_dump(),
        "transcript_length": len(session.transcript)
    }

#DELETE calls
@router.delete("/calls/{session_id}")
async def end_call(session_id: str):
    """
    Ends a call early and marks session as inactive.
    Does not delete session data — keeps it for audit.
    """
    session = active_sessions.get(session_id)

    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session {session_id} not found"
        )

    session.active = False
    active_sessions[session_id] = session

    return {
        "session_id": session_id,
        "status": "ended",
        "message": "Session marked as inactive"
    }

#GET calls(for lisiting all active sessions)
@router.get("/calls")
async def list_sessions():
    """
    Returns summary of all sessions.
    For local dev and clinician dashboard use only.
    """
    return {
        "total": len(active_sessions),
        "sessions": [
            {
                "session_id": s.session_id,
                "current_phase": s.current_phase,
                "escalated": s.escalated,
                "active": s.active
            }
            for s in active_sessions.values()
        ]
    }