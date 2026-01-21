from fastapi import FastAPI
from main import route_and_run
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    role: str
    message: str
    
@app.get("/", response_class=HTMLResponse)
async def root():
    try:
        with open("templates/index.html") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>UI not found. File not found</h1>"


@app.post("/chat")
async def chat(request: ChatRequest):
    
    result = await route_and_run(request.role, request.message)
    
    final_response = None
    
    for msg in reversed(result.messages):
        if isinstance(msg.content, str):
            final_response = msg.content
            break
    
    return{"role": request.role, "message":request.message, "response":final_response}


