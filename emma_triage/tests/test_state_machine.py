from models.schemas import TriageSession, CollectedData
from core.state_machine import (
    increment_turn,
    should_advance_phase,
    advance_phase,
    update_collected_data,
    is_session_complete,
    get_missing_slots
)

passed = 0
failed = 0

def check(test_name, condition):
    global passed, failed
    if condition:
        print(f"PASS | {test_name}")
        passed += 1
    else:
        print(f"FAIL | {test_name}")
        failed += 1

# ============================================================
# TEST 1: Fresh session starts at phase 1
# ============================================================
session = TriageSession()
check("Fresh session starts at phase 1", session.current_phase == 1)
check("Fresh session starts at turn 0", session.turns_in_phase == 0)

# ============================================================
# TEST 2: increment_turn works
# ============================================================
session = increment_turn(session)
check("Turn increments to 1", session.turns_in_phase == 1)
session = increment_turn(session)
check("Turn increments to 2", session.turns_in_phase == 2)

# ============================================================
# TEST 3: Max turns triggers advance
# ============================================================
session = TriageSession()
session.turns_in_phase = 2  # phase 1 max is 2
check("Should advance when max turns hit", should_advance_phase(session) == True)

# ============================================================
# TEST 4: Required slots filled triggers advance
# ============================================================
session = TriageSession()
session.current_phase = 2
session.turns_in_phase = 1  # only 1 turn but slots filled
session.collected_data.chief_complaint = "headache"
session.collected_data.body_location = "behind eyes"
session.collected_data.onset = "acute"
check("Should advance when required slots filled", should_advance_phase(session) == True)

# ============================================================
# TEST 5: Missing slots prevents advance
# ============================================================
session = TriageSession()
session.current_phase = 2
session.turns_in_phase = 1
session.collected_data.chief_complaint = "headache"
# body_location and onset still None
check("Should NOT advance when slots missing", should_advance_phase(session) == False)

# ============================================================
# TEST 6: advance_phase resets turn counter
# ============================================================
session = TriageSession()
session.turns_in_phase = 3
session = advance_phase(session)
check("Phase advances from 1 to 2", session.current_phase == 2)
check("Turn counter resets to 0", session.turns_in_phase == 0)

# ============================================================
# TEST 7: update_collected_data fills empty slots
# ============================================================
session = TriageSession()
session = update_collected_data(session, {
    "chief_complaint": "chest pain",
    "body_location": "left side",
    "onset": "acute"
})
check("chief_complaint filled", session.collected_data.chief_complaint == "chest pain")
check("body_location filled", session.collected_data.body_location == "left side")
check("onset filled", session.collected_data.onset == "acute")

# ============================================================
# TEST 8: update_collected_data does NOT overwrite existing data
# ============================================================
session = TriageSession()
session.collected_data.chief_complaint = "headache"
session = update_collected_data(session, {"chief_complaint": "chest pain"})
check("Existing slot not overwritten", session.collected_data.chief_complaint == "headache")

# ============================================================
# TEST 9: is_session_complete
# ============================================================
session = TriageSession()
session.current_phase = 8
session.turns_in_phase = 1
check("Session complete at phase 8", is_session_complete(session) == True)

session = TriageSession()
session.current_phase = 5
check("Session not complete at phase 5", is_session_complete(session) == False)

# ============================================================
# TEST 10: get_missing_slots
# ============================================================
session = TriageSession()
session.current_phase = 2
session.collected_data.chief_complaint = "headache"
# body_location and onset still missing
missing = get_missing_slots(session)
check("Missing slots detected", "body_location" in missing and "onset" in missing)
check("Filled slot not in missing", "chief_complaint" not in missing)

# ============================================================
print(f"\n{passed} passed, {failed} failed")