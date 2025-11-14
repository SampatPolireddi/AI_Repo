import asyncio
from datetime import datetime, timedelta
from agents import team
from db_tools import create_doctor, create_patient, db

async def clear_database():
    print("🧹 Clearing database...")
    await db.patients.delete_many({})
    await db.doctors.delete_many({})
    await db.appointments.delete_many({})
    await db.prescriptions.delete_many({})
    await db.insights.delete_many({})
    print("✅ Cleared!\n")

async def seed_data():
    print("🌱 Seeding database...")
    await create_doctor("D001", "Dr. Smith", "Cardiology", ["Mon", "Wed", "Fri"])
    await create_doctor("D002", "Dr. Jones", "Cardiology", ["Tue", "Thu", "Sat"])
    await create_patient("P001", "John Doe", 45, "Male", "555-1234", ["Diabetes"])
    print("✅ Seeded!\n")

async def test_appointment():
    tomorrow_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tomorrow_day = (datetime.now() + timedelta(days=1)).strftime("%a")
    
    task = f"""
USER ROLE: patient
USER REQUEST: Book an appointment for John Doe with a cardiologist on {tomorrow_day} ({tomorrow_date})
"""
    
    print(f"📝 Request: Book appointment for {tomorrow_day} ({tomorrow_date})")
    print("🔄 Running team...\n")
    
    result = await team.run(task=task)
    
    print("\n💬 Conversation:")
    for msg in result.messages:
        print(f"\n[{msg.source}]:")
        print(msg.content)
        print("-" * 60)

async def main():
    await clear_database()  # ← Clear first!
    await seed_data()
    await test_appointment()

if __name__ == "__main__":
    asyncio.run(main())