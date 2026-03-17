# EMMA — Medical Triage Voice Agent

A voice-based medical triage agent built with Python (FastAPI) and Ultravox.

## Architecture

EMMA uses a multi-stage pipeline:

- **Stage 1** — Deterministic red flag engine (regex + keyword matching). Runs synchronously on every patient utterance before any LLM call. Handles L1/L2 emergencies.
- **Stage 1b** — Async LLM safety net. Non-blocking secondary check for edge cases.
- **Stage 2** — LLM clinical reasoning (GPT). Returns L3/L4/L5 triage level with confidence score.
- **Stage 3** — Confidence gate. Routes to clinician review if confidence < 0.75.

## Project Structure
```
emma_triage/
├── main.py                  # FastAPI app entry point
├── config.py                # API keys and settings (use .env)
├── requirements.txt         # Dependencies
├── core/
│   ├── red_flag_engine.py   # Stage 1 deterministic safety gate
│   ├── state_machine.py     # 8-phase conversation controller
│   ├── scoring.py           # Stage 2 + 3 clinical scoring pipeline
│   └── prompts.py           # Phase-based system prompts
├── api/
│   ├── routes.py            # FastAPI endpoints
│   └── websocket_handler.py # Ultravox WebSocket runtime loop
├── models/
│   └── schemas.py           # Pydantic data models
├── tests/
│   ├── test_red_flag.py     # Red flag engine tests
│   ├── test_state_machine.py# State machine tests
│   └── test_full_pipeline.py# End-to-end simulation tests
└── test_outputs/            # Saved test transcripts
```

## Setup
```bash
# Clone the repo
git clone <your-repo-url>
cd emma_triage

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API keys
```

## Environment Variables

Create a `.env` file with:
```
ULTRAVOX_API_KEY=your_ultravox_key
OPENAI_API_KEY=your_openai_key
CONFIDENCE_THRESHOLD=0.75
```

## Running the Server
```bash
uvicorn main:app --reload --port 8000
```

## Running Tests
```bash
# Red flag engine tests
python -m tests.test_red_flag

# State machine tests
python -m tests.test_state_machine

# Full pipeline simulation
python -m tests.test_full_pipeline
```

## Triage Levels

| Level | Name | Wait Time | Examples |
|-------|------|-----------|---------|
| L1 | Immediate | NOW | Cardiac arrest, stroke, severe breathing difficulty |
| L2 | Emergent | < 15 min | Chest pain, high fever, severe pain 8-10 |
| L3 | Urgent | 30-60 min | Moderate pain 5-7, persistent vomiting |
| L4 | Less Urgent | 1-2 hrs | Minor cuts, cold/flu, mild pain |
| L5 | Non-Urgent | Telehealth | Prescription refills, minor rash |

## Tech Stack

- Python 3.12
- FastAPI
- Ultravox (voice AI)
- OpenAI GPT (clinical scoring)
- Pydantic
- WebSockets