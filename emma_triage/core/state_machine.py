from models.schemas import TriageSession, CollectedData

PHASE_CONFIG = {
    1: {
        "name": "Greeting & Consent",
        "max_turns": 2,
        "required_slots": ["language", "consent_given"],
    },
    2: {
        "name": "Chief Complaint",
        "max_turns": 3,
        "required_slots": ["chief_complaint", "body_location", "onset"],
    },
    3: {
        "name": "OPQRST Assessment",
        "max_turns": 6,
        "required_slots": ["pain_severity", "pain_quality", "duration_hours"],
    },
    4: {
        "name": "Associated Symptoms",
        "max_turns": 4,
        "required_slots": ["associated_symptoms"],
    },
    5: {
        "name": "Medical History",
        "max_turns": 4,
        "required_slots": [],  # best effort, no hard requirements
    },
    6: {
        "name": "Patient Details",
        "max_turns": 2,
        "required_slots": ["age_group"],
    },
    7: {
        "name": "Triage Decision",
        "max_turns": 1,
        "required_slots": [],
    },
    8: {
        "name": "Routing Action",
        "max_turns": 2,
        "required_slots": [],
    },
}

MAX_PHASE = 8

#Core State Machine Functions
def increment_turn(session: TriageSession) -> TriageSession:
    """
    - Func called everytime when patient speaks
    """
    session.turns_in_phase+=1
    return session

def should_advance_phase(session: TriageSession) -> bool:
    """
    Returns True if either:
    - All required slots for current phase are filled, OR
    - Max turns for current phase has been reached
    """
    phase = session.current_phase
    
    # Already at last phase
    if phase >= MAX_PHASE:
        return False
    
    config = PHASE_CONFIG.get(phase,{})
    max_turns = config.get("max_turns",2)
    required_slots = config.get("required_slots",[])
    
    #Checking if max turns are hit
    if session.turns_in_phase >= max_turns:
        return True
    
    #Checking if all the required slots are filled
    data = session.collected_data.model_dump()
    all_filled = True
    for slot in required_slots:
        value = data.get(slot)
        if value is None or value == [] or value == "":
            all_filled = False
            break

    if required_slots and all_filled:
        return True

    return False


#Moves to next phase and resets the turn counter
def advance_phase(session: TriageSession) -> TriageSession:
   
    if session.current_phase<MAX_PHASE:
        session.current_phase+=1
        session.turns_in_phase=0
    return session

def update_collected_data(session: TriageSession, extracted: dict) -> TriageSession:
    """
    Merges LLM-extracted data into the session.
    Only updates fields that are present in extracted dict
    and not already filled in the session.
    """
    data = session.collected_data.model_dump()
    
    for key, value in extracted.items():
        
        #Skip empty extractions
        if value is None or value == "" or value == []:
            continue
        
        #Skip unkown fields
        if key not in data:
            continue
        
        existing = data.get(key)
        if existing is None or existing == [] or existing == "":
            data[key] = value
        
    session.collected_data = CollectedData(**data)
    return session

def is_session_complete(session: TriageSession) -> bool:
    """
    Returns True when conversation has reached phase 8
    and max turns hit or routing is done.
    """
    return session.current_phase >= MAX_PHASE and session.turns_in_phase >= 1


def get_phase_name(phase: int) -> str:
    return PHASE_CONFIG.get(phase, {}).get("name", "Unknown Phase")


def get_missing_slots(session: TriageSession) -> list[str]:
    """
    Returns list of required slots that are still None.
    Used by scoring engine to flag incomplete data.
    """
    phase = session.current_phase
    config = PHASE_CONFIG.get(phase, {})
    required_slots = config.get("required_slots", [])
    data = session.collected_data.model_dump()
    missing = []

    for slot in required_slots:
        value = data.get(slot)
        if value is None or value == [] or value == "":
            missing.append(slot)

    return missing