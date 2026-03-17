from pydantic import BaseModel
from typing import Optional
import uuid

class VitalSigns(BaseModel):
    temperature: Optional[float] = None
    breathing_difficulty: Optional[bool] = None

class CollectedData(BaseModel):
    #Phase1
    language: Optional[str] = None
    consent_given: Optional[bool] = None

    #Phase2
    chief_complaint: Optional[str] = None
    body_location: Optional[str] = None
    onset: Optional[str] = None
    
    #Phase3
    pain_severity: Optional[int] = None
    pain_quality: Optional[str] = None
    pain_provocation: Optional[str] = None
    provocation: Optional[str] = None
    radiation: Optional[str] = None
    duration_hours: Optional[float] = None
    
    #Phase4
    associated_symptoms: list[str] = []
    vital_signs_reported: VitalSigns = VitalSigns()
    
    # Phase 5
    medical_history: list[str] = []
    medications: list[str] = []
    allergies: list[str] = []
    
    # Phase 6
    age_group: Optional[str] = None  # pediatric | adult | geriatric
    pregnancy: Optional[bool] = None
    
    # Meta
    region: str = "USA"
    language_code: str = "en-US"
    red_flags_triggered: list[str] = []

class TriageSession(BaseModel):
    session_id: str = ""
    current_phase: int = 1
    turns_in_phase: int = 0
    collected_data: CollectedData = CollectedData()
    transcript: list[dict] = []
    escalated: bool = False
    active: bool = True
    
    def new(self) -> "TriageSession":
        self.session_id = str(uuid.uuid4())
        return self

class TriageOutput(BaseModel):
    triage_level: str  # L1 | L2 | L3 | L4 | L5
    confidence: float
    routing_action: str
    escalation_required: bool
    escalation_contact: Optional[str] = None
    recommended_speciality: Optional[str] = None
    self_care_guidance: Optional[str] = None
    stage_1_rule_triggered: bool = False
    rule_id: Optional[str] = None
    review_required: bool = False
    llm_reasoning_summary: Optional[str] = None