import uvicorn
from fastapi import FastAPI, Request
from cal_service import check_availability, book_appointment

app = FastAPI()

@app.post('/webhook')
async def handle_retell_webhook(request:Request):
    data = await request.json()
    args = data.get("args",{})
    tool_name = data.get("name")
    
    result = None
    
    if tool_name == 'check_availability':
        result = check_availability(args.get("date"))
    elif tool_name == "book_appointment":
        result = book_appointment(args.get("patient_name"), args.get("start_time"), args.get("end_time"))
        
    response = {"result":result}
    if "response_id" in data:
        response["response_id"] = data["response_id"]
    
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)