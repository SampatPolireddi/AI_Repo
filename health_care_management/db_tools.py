from motor.motor_asyncio import AsyncIOMotorClient
from typing import Dict, List, Optional
from datetime import datetime

mongo_client= AsyncIOMotorClient("mongodb://localhost:27017")

db=mongo_client["healthcare_db"]

# Collections
patients_collection = db["patients"]
doctors_collection = db["doctors"]
appointments_collection = db["appointments"]
prescriptions_collection = db["prescriptions"]
insights_collection = db["insights"]

#Receptionist Funcs
async def count_appointments(doctor_id:str, date:str) -> int:
    
    appointments= await appointments_collection.count_documents({
        "doctor_id": doctor_id,
        "date": date,
        "status": "Scheduled"
    })   
    return appointments

async def create_appointment(appointment_id:str, patient_id:str, doctor_id:str, date:str) -> Dict:
    appointment= {
        "appointment_id": appointment_id,
        "patient_id": patient_id,
        "doctor_id":doctor_id,
        "date": date,
        "status":"Scheduled"
    }
    
    await appointments_collection.insert_one(appointment)
    
    return {"Status": "Success","Appointment_Id": appointment_id, "Message": f"Appointment has been made for patient id {patient_id}"}

async def get_appointments_by_patient(patient_id:str) -> List[Dict]:
    appointments = await appointments_collection.find({"patient_id":patient_id}).to_list(length=None)

    # Format appointments for user-friendly display
    formatted_appointments = []
    for apt in appointments:
        formatted_apt = {
            "appointment_id": apt.get("appointment_id"),
            "patient_id": apt.get("patient_id"),
            "doctor_id": apt.get("doctor_id"),
            "date": apt.get("date"),
            "status": apt.get("status")
        }
        formatted_appointments.append(formatted_apt)

    return formatted_appointments

async def get_appointments_by_doctor(doctor_id:str, date:str = None) -> List[Dict]:
    query = {"doctor_id": doctor_id}

    if date is not None:
        query["date"] = date

    doc_appointments = await appointments_collection.find(query).to_list(length=None)

    # Format appointments for user-friendly display
    formatted_appointments = []
    for apt in doc_appointments:
        formatted_apt = {
            "appointment_id": apt.get("appointment_id"),
            "patient_id": apt.get("patient_id"),
            "doctor_id": apt.get("doctor_id"),
            "date": apt.get("date"),
            "status": apt.get("status")
        }
        formatted_appointments.append(formatted_apt)

    return formatted_appointments



#Patient Funcs
async def get_patient(patient_id: str) -> Optional[Dict]:
    patient= await patients_collection.find_one({"patient_id": patient_id})

    if patient:
        # Format patient for user-friendly display (remove MongoDB _id)
        formatted_patient = {
            "patient_id": patient.get("patient_id"),
            "name": patient.get("name"),
            "age": patient.get("age"),
            "gender": patient.get("gender"),
            "contact": patient.get("contact"),
            "medical_history": patient.get("medical_history", [])
        }
        return formatted_patient

    return None

async def get_patient_by_name(name:str) -> Optional[Dict]:
    patient= await patients_collection.find_one({"name": name})

    if patient:
        # Format patient for user-friendly display (remove MongoDB _id)
        formatted_patient = {
            "patient_id": patient.get("patient_id"),
            "name": patient.get("name"),
            "age": patient.get("age"),
            "gender": patient.get("gender"),
            "contact": patient.get("contact"),
            "medical_history": patient.get("medical_history", [])
        }
        return formatted_patient

    return None

async def create_patient(patient_id:str, name: str, age:int, gender:str, contact:str, medical_history: List[str]=None) -> Dict:
    if medical_history is None:
        medical_history=[]
    
    patient={
        "patient_id": patient_id, 
        "name": name, 
        "age": age,
        "gender": gender, 
        "contact": contact, 
        "medical_history": medical_history
    }
    
    await patients_collection.insert_one(patient)
    return {"status":"success","patient_id": patient_id, "name": name, "age": age, "gender": gender, "contact": contact, "medical_history": medical_history}

async def update_patient_contact(patient_id: str, contact: str) -> Dict:
    
    result = await patients_collection.update_one({"patient_id":patient_id},{"$set": {"contact": contact}})
    
    if result.modified_count>0:
        return {"Status": "Success", "Message":"Contact Updated"}
    
    return {"Status":"Failed","Message":"Patient not found"}

async def get_patient_history(patient_id:str) -> Dict:
    patient = await patients_collection.find_one({"patient_id":patient_id})
    
    appointments = await appointments_collection.find({"patient_id":patient_id}).to_list(length=None)
    
    appointment_ids = [apt["appointment_id"] for apt in appointments]
    
    if appointment_ids:
        prescriptions = await prescriptions_collection.find({"appointment_id":{"$in": appointment_ids}}).to_list(length=None)
    else:
        prescriptions=[]
    
    return {"patient":patient, "appointments":appointments,"prescriptions":prescriptions}

async def create_health_insight(patient_id:str, risk_score:float, recommendations: List[str] = None) -> Dict:
    if recommendations is None:
        recommendations=[]
    
    health_insight = {
        "patient_id":patient_id,
        "risk_score": risk_score,
        "recommendations": recommendations,
        "created_at": datetime.now().isoformat()
    }

    await insights_collection.insert_one(health_insight)
    return {"Status":"Success", "Message": f"Successfully insert the health insight for patient ID: {patient_id}"}

async def get_health_insight(patient_id:str) -> List[Dict]:

    insights = await insights_collection.find({"patient_id":patient_id}).to_list(length=None)

    # Format insights for user-friendly display
    formatted_insights = []
    for insight in insights:
        formatted_insight = {
            "patient_id": insight.get("patient_id"),
            "risk_score": insight.get("risk_score"),
            "recommendations": insight.get("recommendations", []),
            "created_at": insight.get("created_at")
        }
        formatted_insights.append(formatted_insight)

    return formatted_insights

#Doctor Funcs
async def get_doctor_by_specialization(specialization: str, day: str) -> List[Dict]:
    doctors = await doctors_collection.find({"specialization": specialization, "availability": day}).to_list(length=None)

    # Format doctors for user-friendly display
    formatted_doctors = []
    for doctor in doctors:
        formatted_doctor = {
            "doctor_id": doctor.get("doctor_id"),
            "name": doctor.get("name"),
            "specialization": doctor.get("specialization"),
            "availability": ", ".join(doctor.get("availability", []))
        }
        formatted_doctors.append(formatted_doctor)

    return formatted_doctors

async def get_all_doctors() -> List[Dict]:
    doctors = await doctors_collection.find({}).to_list(length=None)

    # Format doctors for user-friendly display
    formatted_doctors = []
    for doctor in doctors:
        formatted_doctor = {
            "doctor_id": doctor.get("doctor_id"),
            "name": doctor.get("name"),
            "specialization": doctor.get("specialization"),
            "availability": ", ".join(doctor.get("availability", []))
        }
        formatted_doctors.append(formatted_doctor)

    return formatted_doctors
    
async def get_doctor(doctor_id:str) -> Optional[Dict]:
    doctor = await doctors_collection.find_one({"doctor_id":doctor_id})

    if doctor:
        # Format doctor for user-friendly display
        formatted_doctor = {
            "doctor_id": doctor.get("doctor_id"),
            "name": doctor.get("name"),
            "specialization": doctor.get("specialization"),
            "availability": ", ".join(doctor.get("availability", []))
        }
        return formatted_doctor

    return None

async def create_doctor(doctor_id: str, name: str, specialization: str, availability: List[str]) -> Dict:
    
    doctor = {
        "doctor_id": doctor_id,
        "name": name,
        "specialization": specialization,
        "availability": availability
    }
    
    await doctors_collection.insert_one(doctor)
    return {"Status":"Success", "doctor_id":doctor_id, "message": f"Dr. {name} added succesfully"}

async def update_doctor_availability(doctor_id: str, availability: List[str]) -> Dict:
   
    result = await doctors_collection.update_one(
        {"doctor_id": doctor_id},
        {"$set": {"availability": availability}}
    )
    
    if result.modified_count > 0:
        return {"status": "success", "message": "Doctor availability updated"}
    return {"status": "failed", "message": "Doctor not found"}



#Prescription Funcs
async def create_prescription(prescription_id:str, appointment_id:str, medicines:List[Dict]) -> Dict:
    
    prescription = {
        "prescription_id": prescription_id,
        "appointment_id": appointment_id,
        "medicines": medicines
    }
    await prescriptions_collection.insert_one(prescription)
    return {"Status":"Success", "Message": f"Prescription ID: {prescription_id} has been added successfuly"}

async def get_prescription(prescription_id:str) -> Optional[Dict]:
    prescription_identified = await prescriptions_collection.find_one({"prescription_id":prescription_id})

    if prescription_identified:
        # Format prescription for user-friendly display
        formatted_prescription = {
            "prescription_id": prescription_identified.get("prescription_id"),
            "appointment_id": prescription_identified.get("appointment_id"),
            "medicines": prescription_identified.get("medicines", [])
        }
        return formatted_prescription

    return None

async def get_prescriptions_by_appointment(appointment_id:str) -> List[Dict]:
    prescription_identified_by_appointment = await prescriptions_collection.find({"appointment_id":appointment_id}).to_list(length=None)

    # Format prescriptions for user-friendly display
    formatted_prescriptions = []
    for presc in prescription_identified_by_appointment:
        formatted_presc = {
            "prescription_id": presc.get("prescription_id"),
            "appointment_id": presc.get("appointment_id"),
            "medicines": presc.get("medicines", [])
        }
        formatted_prescriptions.append(formatted_presc)

    return formatted_prescriptions

async def get_prescription_by_patient(patient_id:str) -> List[Dict]:

    appointments = await appointments_collection.find({"patient_id": patient_id}).to_list(length=None)

    appointment_ids = [apt["appointment_id"] for apt in appointments]

    if not appointment_ids:
        return []

    prescriptions = await prescriptions_collection.find({
        "appointment_id": {"$in": appointment_ids}}).to_list(length=None)

    # Format prescriptions for user-friendly display
    formatted_prescriptions = []
    for presc in prescriptions:
        formatted_presc = {
            "prescription_id": presc.get("prescription_id"),
            "appointment_id": presc.get("appointment_id"),
            "medicines": presc.get("medicines", [])
        }
        formatted_prescriptions.append(formatted_presc)

    return formatted_prescriptions

