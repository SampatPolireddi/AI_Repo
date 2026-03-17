import re

# ============================================================
# LAYER 1: KEYWORD MATCHING
# ============================================================

RED_FLAG_KEYWORDS = {
    "cardiac": [
        "chest pain", "heart attack", "chest tightness",
        "chest pressure", "my heart is stopping", "heart is stopping",
        "left arm pain", "jaw pain with chest"
    ],
    "neurological": [
        "stroke", "face drooping", "facial drooping",
        "arm weakness", "arm is weak", "cant speak", "can't speak",
        "sudden severe headache", "worst headache of my life",
        "sudden headache", "seizure", "having a seizure",
        "facial numbness", "sudden numbness", "sudden confusion"
    ],
    "respiratory": [
        "can't breathe", "cannot breathe", "cant breathe",
        "choking", "throat closing", "throat is closing",
        "anaphylaxis", "allergic reaction", "severe allergic",
        "blue lips", "lips are blue", "not breathing",
        "stopped breathing", "trouble breathing"
    ],
    "trauma": [
        "major accident", "car accident", "head injury",
        "hit my head", "unconscious", "unresponsive",
        "severe bleeding", "bleeding out", "wont stop bleeding",
        "won't stop bleeding", "stab wound", "stabbed",
        "gunshot", "shot", "fell from"
    ],
    "mental_health": [
        "want to die", "kill myself", "killing myself",
        "suicide", "suicidal", "end my life", "ending my life",
        "overdose", "took all my pills", "took too many pills",
        "want to hurt myself", "self harm", "self-harm"
    ]
}

# ============================================================
# LAYER 2: REGEX PATTERNS
# Catches variations keyword matching would miss
# ============================================================

RED_FLAG_PATTERNS = [
    # Breathing variations
    (r"\b(can'?t|cannot|not\s+able\s+to)\s+breath(e|ing)?\b", "respiratory"),
    (r"\b(difficulty|difficultly|hard\s+time)\s+breath(e|ing)\b", "respiratory"),
    (r"\bshortness\s+of\s+breath\b", "respiratory"),
    (r"\bno\s+(air|oxygen)\b", "respiratory"),

    # Cardiac variations
    (r"\bchest\s+(pain|pressure|tightness|heaviness|discomfort)\b", "cardiac"),
    (r"\b(crushing|squeezing|stabbing)\s+(chest|pain)\b", "cardiac"),
    (r"\bheart\s+(attack|stopping|racing\s+uncontrollably)\b", "cardiac"),

    # Neurological variations
    (r"\bworst\s+headache(\s+of\s+my\s+life)?\b", "neurological"),
    (r"\bsudden\s+(severe\s+)?(headache|numbness|weakness|confusion)\b", "neurological"),
    (r"\b(face|arm|leg)\s+(drooping|numb|paralyz)\b", "neurological"),
    (r"\bcan'?t\s+(speak|talk|move|see)\s+(properly|at all|suddenly)?\b", "neurological"),

    # Trauma variations
    (r"\b(bleeding\s+(heavily|profusely|uncontrollably))\b", "trauma"),
    (r"\b(passed|blacked)\s+out\b", "trauma"),
    (r"\b(not\s+responding|not\s+waking\s+up)\b", "trauma"),

    # Mental health variations
    (r"\b(want(ing)?|going|plan(ning)?)\s+to\s+(kill|hurt|harm)\s+(my)?self\b", "mental_health"),
    (r"\b(took|taken|swallowed)\s+(too\s+many|all\s+(my|the))\s+(pills|medication|tablets)\b", "mental_health"),
]

#Main Check Func
#Runs synchronously on every user utterance
def check_red_flag(text:str)->tuple[bool, str| None, str| None]: #Returns (true/false, category, matched term)
    
    normalized = text.lower().strip()
    
    #Layer 1: Keyword Scan
    for category, keywords in RED_FLAG_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                return True, category, kw
    
    # Layer 2: Regex Scan
    for pattern, category in RED_FLAG_PATTERNS:
        match = re.search(pattern, normalized)
        if match:
            return True, category, match.group()
    
    return False, None, None

#Emergency Response Scripts
EMERGENCY_SCRIPTS = {
    "cardiac": (
        "I need you to listen carefully. What you've described sounds like "
        "a cardiac emergency. Please call 911 immediately or have someone "
        "take you to the nearest emergency room right now. Do not drive yourself. "
        "Is there someone with you who can help?"
    ),
    "neurological": (
        "What you're describing could be a serious neurological emergency like "
        "a stroke. Please call 911 immediately. Do not wait. "
        "Is there someone with you right now?"
    ),
    "respiratory": (
        "You may be having a severe breathing emergency. "
        "Please call 911 immediately or have someone take you to the ER right now. "
        "Do not drive yourself. Is there someone with you who can help?"
    ),
    "trauma": (
        "This sounds like a serious medical emergency. "
        "Please call 911 immediately. If there is severe bleeding, "
        "apply pressure to the wound. Is there someone with you right now?"
    ),
    "mental_health": (
        "I hear you and I want you to be safe. "
        "Please call 988, which is the Suicide and Crisis Lifeline, right now. "
        "You can also call 911 or go to your nearest emergency room. "
        "Is there someone with you or nearby who can stay with you?"
    ),
    "default": (
        "What you've described sounds like a medical emergency. "
        "Please call 911 immediately or have someone take you to the "
        "nearest emergency room right now. Do not drive yourself."
    )
}

def get_emergency_script(category: str | None) -> str:
    if category and category in EMERGENCY_SCRIPTS:
        return EMERGENCY_SCRIPTS[category]
    return EMERGENCY_SCRIPTS["default"]