import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core.tools import FunctionTool
from db_tools import (
    # Patient functions
    get_patient, get_patient_by_name, create_patient, update_patient_contact, get_patient_history,
    # Doctor functions
    get_doctor, get_doctor_by_specialization, get_all_doctors, create_doctor, update_doctor_availability,
    # Appointment functions
    count_appointments, create_appointment, get_appointments_by_patient, get_appointments_by_doctor,
    # Prescription functions
    create_prescription, get_prescription, get_prescriptions_by_appointment, get_prescription_by_patient,
    # Health Insight functions
    create_health_insight, get_health_insight
)
from dotenv import load_dotenv
from autogen_agentchat.conditions import MaxMessageTermination
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

model_client=OpenAIChatCompletionClient(
    model="gpt-5-nano",
    api_key=os.getenv("OPENAI_API_KEY")
)

#Function Tools

# Patient tools
get_patient_tool = FunctionTool(get_patient, description="Get patient information by patient_id")
get_patient_by_name_tool = FunctionTool(get_patient_by_name, description="Search for patient by name")
create_patient_tool = FunctionTool(create_patient, description="Register a new patient")
update_patient_contact_tool = FunctionTool(update_patient_contact, description="Update patient contact information")
get_patient_history_tool = FunctionTool(get_patient_history, description="Get complete patient history including appointments and prescriptions")

# Doctor tools
get_doctor_tool = FunctionTool(get_doctor, description="Get doctor information by doctor_id")
get_doctor_by_specialization_tool = FunctionTool(get_doctor_by_specialization, description="Find doctors by specialization and day availability")
get_all_doctors_tool = FunctionTool(get_all_doctors, description="Get all doctors in the system")
create_doctor_tool = FunctionTool(create_doctor, description="Add a new doctor to the system")
update_doctor_availability_tool = FunctionTool(update_doctor_availability, description="Update doctor's availability schedule")

# Appointment tools
count_appointments_tool = FunctionTool(count_appointments, description="Count scheduled appointments for a doctor on a specific date")
create_appointment_tool = FunctionTool(create_appointment, description="Create a new appointment")
get_appointments_by_patient_tool = FunctionTool(get_appointments_by_patient, description="Get all appointments for a patient")
get_appointments_by_doctor_tool = FunctionTool(get_appointments_by_doctor, description="Get appointments for a doctor, optionally filtered by date")

# Prescription tools
create_prescription_tool = FunctionTool(create_prescription, description="Create a new prescription")
get_prescription_tool = FunctionTool(get_prescription, description="Get prescription by prescription_id")
get_prescriptions_by_appointment_tool = FunctionTool(get_prescriptions_by_appointment, description="Get all prescriptions for an appointment")
get_prescription_by_patient_tool = FunctionTool(get_prescription_by_patient, description="Get all prescriptions for a patient")

# Health Insight tools
create_health_insight_tool = FunctionTool(create_health_insight, description="Store health insights and recommendations for a patient")
get_health_insight_tool = FunctionTool(get_health_insight, description="Get all health insights for a patient")

#Agents
#1
receptionist=AssistantAgent(
    name="receptionist",
    model_client=model_client,
    tools=[
        # Patient tools
        get_patient_tool,
        get_patient_by_name_tool,
        create_patient_tool,
        update_patient_contact_tool,
        # Doctor tools
        get_doctor_by_specialization_tool,
        # Appointment tools
        count_appointments_tool,
        create_appointment_tool,
        get_appointments_by_patient_tool,
    ],
    system_message="""
    You are the Receptionist Agent for a healthcare management system.

    Your responsibilities:
    - Register new patients in the system
    - Book and manage appointments
    - Update patient contact information
    - Check doctor availability and schedule appointments

    IMPORTANT DATA FORMATS:
    - Specializations in database: "Cardiology", "Neurology", "Orthopedics" (NOT "Cardiologist")
    - Days in database: "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun" (SHORT FORM, not "Monday")

    When booking appointments:
    1. Check if patient exists, if not register them first
    2. Convert user's day request to short form (Monday → Mon, Tuesday → Tue, etc.)
    3. Convert specialization (cardiologist → Cardiology, neurologist → Neurology, etc.)
    4. Query doctors using correct format: get_doctor_by_specialization(specialization="Cardiology", day="Mon")
    5. Check appointment counts to find doctor with least appointments
    6. If multiple doctors have same count, choose alphabetically
    7. Create appointment with status "Scheduled"
    8. Provide brief confirmation ONLY

    CRITICAL:
    - Always use "Mon"/"Tue"/etc for days, and "Cardiology"/"Neurology"/etc for specializations.
    - DO NOT ask for confirmations or additional preferences
    - DO NOT offer backup options, reminders, notes, or caregiver access
    - JUST book the appointment and confirm it was done
    - Keep responses under 2 sentences
    """
)

#2
doctor_assistant=AssistantAgent(
    name="doctor_assistant",
    model_client=model_client,
     tools=[
        # Patient tools
        get_patient_tool,
        get_patient_history_tool,
        # Prescription tools
        create_prescription_tool,
        get_prescriptions_by_appointment_tool,
        get_prescription_by_patient_tool,
    ],
    system_message="""
    You are the Doctor Assistant Agent - a clinical support system.

    Your responsibilities:
    - Generate prescriptions for patients after appointments
    - Retrieve and summarize patient medical history
    - Summarize patient symptoms and visit notes
    - Help doctors with clinical documentation

    You work exclusively with DOCTOR role users.

    When generating prescriptions:
    - Link prescription to appointment_id
    - Include medicine name, dosage, and frequency
    - Store in Prescriptions collection

    When retrieving patient history:
    - Pull from Patients collection (medical_history field)
    - Summarize past appointments
    - Include relevant prescriptions

    You have READ access to: Patients, Appointments, Prescriptions
    You have WRITE access to: Prescriptions

    CRITICAL:
    - DO NOT ask for confirmations
    - JUST execute the task and provide brief confirmation
    - Keep responses under 2 sentences
    """
)

#3
health_insight=AssistantAgent(
    name="health_insight",
    model_client=model_client,
    tools=[
        # Patient tools
        get_patient_tool,
        get_patient_history_tool,
        # Health Insight tools
        create_health_insight_tool,
        get_health_insight_tool,
    ],
    system_message="""
    You are the Health Insight Agent - a data analytics and risk assessment system.

    Your responsibilities:
    - Analyze patient vitals and health data
    - Calculate and flag health risk scores
    - Provide lifestyle and health recommendations
    - Identify patterns in patient data

    When analyzing patient health:
    1. Review patient medical history and vitals
    2. Calculate risk scores (0.0 to 1.0 scale)
    3. Generate actionable recommendations
    4. Store insights in Insights collection

    Your recommendations should include:
    - Dietary suggestions
    - Exercise recommendations
    - Preventive care advice
    - Follow-up suggestions

    You have READ access to: Patients, Appointments, Prescriptions
    You have WRITE access to: Insights

    CRITICAL:
    - DO NOT ask for confirmations
    - JUST execute the analysis and provide brief results
    - Keep responses under 3 sentences
    """
)

#4
admin=AssistantAgent(
    name="admin",
    model_client=model_client,
     tools=[
        # Doctor tools
        get_doctor_tool,
        get_all_doctors_tool,
        create_doctor_tool,
        update_doctor_availability_tool,
    ],
    system_message="""
    You are the Admin Agent - responsible for system operations and data management.

    Your responsibilities:
    - Add, update, and manage doctor records
    - Manage staff information
    - Monitor data consistency across collections
    - Handle doctor availability schedules

    When managing doctors:
    - Add new doctors with specialization and availability
    - Update existing doctor schedules
    - Ensure data consistency (e.g., no appointments scheduled when doctor unavailable)

    You have WRITE access to: Doctors
    You have READ access to: All collections for consistency checks

    CRITICAL:
    - DO NOT ask for confirmations
    - JUST execute the task and provide brief confirmation
    - Keep responses under 2 sentences
    """
)

selector_prompt = """You are a routing agent for a healthcare management system.

Your job is to select the appropriate agent based on the user's role and request.

ROUTING RULES:
1. If user role is "patient" OR request is about appointments/registration → select "receptionist"
2. If user role is "doctor" OR request is about prescriptions/patient history → select "doctor_assistant"
3. If request is about health analytics/risk scores/insights → select "health_insight"
4. If user role is "admin" OR request is about managing doctors/staff → select "admin"

EXAMPLES:
- "USER ROLE: patient, REQUEST: book appointment" → receptionist
- "USER ROLE: patient, REQUEST: show my appointments" → receptionist
- "USER ROLE: doctor, REQUEST: generate prescription" → doctor_assistant
- "USER ROLE: doctor, REQUEST: patient history" → doctor_assistant
- "USER ROLE: admin, REQUEST: add new doctor" → admin
- "Analyze patient health data" → health_insight

IMPORTANT:
- Respond with ONLY the agent name: "receptionist", "doctor_assistant", "health_insight", or "admin"
- No explanations, no additional text
- Look for "USER ROLE:" in the message to help decide
"""

team = SelectorGroupChat(
    participants=[receptionist, doctor_assistant, health_insight, admin],
    model_client=model_client,
    selector_prompt=selector_prompt,
    termination_condition=MaxMessageTermination(max_messages=15),
    allow_repeated_speaker=False,  # Prevent same agent speaking twice in a row
)

async def route_and_run(user_role: str, user_message: str):
    
    task = f"""USER ROLE: {user_role}
    USER REQUEST: {user_message}"""
    
    result = await team.run(task=task)
    return result