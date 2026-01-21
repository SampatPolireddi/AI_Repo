import uvicorn
from fastapi import FastAPI, Request
from ehr_project.tools import check_patient_db
from ehr_project.agents import run_admin_agent

app = FastAPI()

@app.post("/get-patient-status")
async def handle_fast_check(request: Request):
   
    payload = await request.json()
    args = payload.get("args", {})
    full_name = args.get("patient_name")
    
    if not full_name: 
        return {"result": "I didn't catch the name."}

   
    print(f"Checking {full_name}")
    result = check_patient_db(full_name)
    
    if result:
        return {"result": f"I found {result['name']}, born {result['dob']}."}
    else:
        return {"result": "Patient not found."}


#For registring a patient(more latency)
@app.post("/consult-agent")
async def handle_agent_request(request: Request):

    payload = await request.json()
    args = payload.get("args", {})
    instruction = args.get("instruction")
    
    if not instruction:
        return {"result": "No instruction provided"}
    
    try:
        agent_response = await run_admin_agent(instruction)
        return {"result": agent_response}
        
    except Exception as e:
        print(f"Agent Error: {e}")
        return {"result": "I'm having trouble connecting to the registrar."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)