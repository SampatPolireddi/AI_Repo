from core.red_flag_engine import check_red_flag, get_emergency_script

tests = [
    # SHOULD trigger
    ("I have chest pain",                True,  "cardiac"),
    ("I cant breathe properly",          True,  "respiratory"),
    ("worst headache of my life",        True,  "neurological"),
    ("I want to kill myself",            True,  "mental_health"),
    ("I was in a major accident",        True,  "trauma"),
    ("my throat is closing",             True,  "respiratory"),
    ("I think im having a heart attack", True,  "cardiac"),
    ("I took all my pills",              True,  "mental_health"),

    # should NOT trigger
    ("I have a mild headache",           False, None),
    ("my knee hurts a little",           False, None),
    ("I feel a bit dizzy",               False, None),
    ("I have a sore throat",             False, None),
]

passed = 0
failed = 0

for text, expected_flag, expected_category in tests:
    flagged, category, matched_term = check_red_flag(text)
    status = "PASS" if flagged == expected_flag else "FAIL"
    if status == "PASS":
        passed += 1
    else:
        failed += 1
    print(f"{status} | {text}")
    if status == "FAIL":
        print(f"     expected={expected_flag} got={flagged} category={category} matched={matched_term}")

print(f"\n{passed} passed, {failed} failed")


print("\n--- Emergency Scripts ---")
from core.red_flag_engine import get_emergency_script
print(get_emergency_script("cardiac"))
print(get_emergency_script("mental_health"))
print(get_emergency_script(None))