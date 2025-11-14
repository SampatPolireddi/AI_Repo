import asyncio
from datetime import datetime, timedelta
from agents import route_and_run
from db_tools import (
    create_doctor, create_patient, db, appointments_collection, doctors_collection, prescriptions_collection
)


async def clear_database():
    
    print("Clearing database...")
    await db.patients.delete_many({})
    await db.doctors.delete_many({})
    await db.appointments.delete_many({})
    await db.prescriptions.delete_many({})
    await db.insights.delete_many({})
    print("Database cleared!\n")


async def seed_data():
    print("Seeding database with test data...")
    
    # Add test doctors
    await create_doctor("D001", "Dr. Smith", "Cardiology", ["Mon", "Wed", "Fri"])
    await create_doctor("D002", "Dr. Jones", "Cardiology", ["Tue", "Thu"])
    await create_doctor("D003", "Dr. Patel", "Neurology", ["Mon", "Tue", "Wed", "Thu", "Fri"])
    
    # Add test patient
    await create_patient("P001", "John Doe", 45, "Male", "555-1234", ["Diabetes"])
    
    print("Database seeded!\n")
    
async def test_appointment_booking():
    print("\n" + "="*70)
    print("TEST 1: PATIENT - Book Appointment")
    print("="*70)
    
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_day = (datetime.now() + timedelta(days=1)).strftime("%a")
    
    result = await route_and_run(
        user_role = "patient",
        user_message = f"Book an appointment for  John Doe with a cardiologist on {tomorrow_day} ({tomorrow_date})"
    )
    
    final_response = None
    for msg in reversed(result.messages):
        if isinstance(msg.content, str):
            final_response = msg.content
            break

    print("🤖 Agent Response: ")
    print(final_response)
    print()
    
    #Cross checking in database
    print("🔍 Database Contents:")
    print("\n📋 ALL APPOINTMENTS:")
    all_appointments = await appointments_collection.find({}).to_list(length=None)
    
    if all_appointments:
        for apt in all_appointments:
            print(f"   - Appointment ID: {apt['appointment_id']}")
            print(f"     Patient: {apt['patient_id']}")
            print(f"     Doctor: {apt['doctor_id']}")
            print(f"     Date: {apt['date']}")
            print(f"     Status: {apt['status']}")
            print()
    else:
        print("   (No appointments in database)")
    
    return result

async def test_doctor_prescription():
    
    print("\n" + "="*70)
    print("🧪 TEST 2: DOCTOR - Generate Prescription")
    print("="*70)
    
    # Get any appointment to use
    appointments = await appointments_collection.find({}).to_list(length=None)
    
    if not appointments:
        print("⚠️  No appointments found! Run test_patient_booking first.")
        return
    
    # Use the first appointment
    appointment = appointments[0]
    patient_id = appointment['patient_id']
    appointment_id = appointment['appointment_id']
    
    print(f"📋 Using appointment: {appointment_id}\n")
    
    # Run the test
    result = await route_and_run(
        user_role="doctor",
        user_message=f"Generate a prescription for patient {patient_id}, appointment {appointment_id}. "
                     f"Prescribe: Aspirin 100mg once daily, Metformin 500mg twice daily"
    )
    
    # Extract final response
    final_response = None
    for msg in reversed(result.messages):
        if isinstance(msg.content, str):
            final_response = msg.content
            break
    
    print("🤖 Agent Response:")
    print(final_response)
    print()
    
    # Simple verification - just show ALL prescriptions
    print("🔍 Database Contents:")
    print("\n💊 ALL PRESCRIPTIONS:")
    all_prescriptions = await prescriptions_collection.find({}).to_list(length=None)
    
    if all_prescriptions:
        for rx in all_prescriptions:
            print(f"   - Prescription ID: {rx['prescription_id']}")
            print(f"     Appointment: {rx['appointment_id']}")
            print(f"     Medicines: {rx['medicines']}")
            print()
    else:
        print("   (No prescriptions in database)")
    
    return result


async def test_admin_add_doctor():
    
    print("\n" + "="*70)
    print("🧪 TEST 3: ADMIN - Add Doctor")
    print("="*70)
    
    # Run the test
    result = await route_and_run(
        user_role="admin",
        user_message="Add a new doctor: Dr. Williams, specialization Orthopedics, "
                     "available Monday, Wednesday, Friday"
    )
    
    # Extract final response
    final_response = None
    for msg in reversed(result.messages):
        if isinstance(msg.content, str):
            final_response = msg.content
            break
    
    print("🤖 Agent Response:")
    print(final_response)
    print()
    
    # Simple verification - just show ALL doctors
    print("🔍 Database Contents:")
    print("\n👨‍⚕️ ALL DOCTORS:")
    all_doctors = await doctors_collection.find({}).to_list(length=None)
    
    if all_doctors:
        for doc in all_doctors:
            print(f"   - Doctor ID: {doc['doctor_id']}")
            print(f"     Name: {doc['name']}")
            print(f"     Specialization: {doc['specialization']}")
            print(f"     Availability: {doc['availability']}")
            print()
    else:
        print("   (No doctors in database)")
    
    return result


async def main():
    print("\n🏥 Healthcare AI System - Test Suite")
    print("=" * 60)
    
    # Seed database first
    await clear_database()
    await seed_data()
    
    # Run tests
    try:
        await test_appointment_booking()
        await test_doctor_prescription() 
        await test_admin_add_doctor()      
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
