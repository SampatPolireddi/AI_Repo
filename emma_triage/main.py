import asyncio
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router, active_sessions, create_ultravox_call
from api.websocket_handler import handle_ultravox_session
from models.schemas import TriageSession
import uuid

app = FastAPI(
    title="EMMA Medical Triage Agent",
    description="Voice-based medical triage system powered by Ultravox",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

# POST /start — Creates call + starts WebSocket handler
# This is the main entry point for starting a triage session
@app.post("/start")
async def start_triage(background_tasks: BackgroundTasks):
    """
    Creates a new Ultravox call and starts the WebSocket
    handler as a background task.
    Returns joinUrl for the patient to connect.
    """
    # Create fresh session
    session = TriageSession()
    session.session_id = str(uuid.uuid4())

    # Create Ultravox call
    ultravox_response = await create_ultravox_call(session.session_id)
    call_id = ultravox_response.get("callId")
    join_url = ultravox_response.get("joinUrl")

    # Store session
    active_sessions[session.session_id] = session

    # Start WebSocket handler in background
    # This runs concurrently while FastAPI handles other requests
    background_tasks.add_task(
        handle_ultravox_session,
        join_url=join_url,
        call_id=call_id,
        session=session,
        active_sessions=active_sessions
    )

    return {
        "session_id": session.session_id,
        "call_id": call_id,
        "join_url": join_url,
        "status": "started",
        "message": "Triage session started. Use join_url to connect patient."
    }



# GET /health — Health check
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "active_sessions": len(active_sessions),
        "service": "EMMA Medical Triage Agent"
    }