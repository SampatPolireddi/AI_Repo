import os
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_agentchat.teams import SelectorGroupChat
from autogen_core.tools import FunctionTool
from autogen_agentchat.conditions import MaxMessageTermination
from dotenv import load_dotenv
from ehr_project.tools import create_patient_db
import asyncio

load_dotenv()

async def run_admin_agent(instruction: str) -> str:
    model_client=OpenAIChatCompletionClient(
        model="gpt-5-nano",
        api_key=os.getenv("OPENAI_API_KEY")
    )

    register_tool = FunctionTool(
            create_patient_db, 
            description="Creates a new patient. Extracts first_name, last_name, and dob from the user prompt."
        )

    registrar = AssistantAgent(
            name="registrar",
            model_client=model_client,
            tools=[register_tool],
            system_message="""
            You are a Hospital Registrar.
            Your ONLY job is to register new patients.
            
            PROTOCOL:
            1. Parse the user instruction for 'first_name', 'last_name', and 'dob'.
            2. If 'dob' is missing, assume '1990-01-01'.
            3. Call the 'create_patient_db' tool.
            4. Reply with a short, spoken-style confirmation (e.g., "I've successfully registered John Doe.").
            """
        )

    response = await registrar.run(task=instruction)

    final_text = response.messages[-1].content
    print(f"AGENT RESPONSE: {final_text}")
        
    return final_text
