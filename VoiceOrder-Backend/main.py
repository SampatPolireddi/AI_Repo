from fastapi import FastAPI, Request
from pydantic import BaseModel
import asyncio
import json
from dotenv import load_dotenv

from tools import calculate_order, validate_delivery_address, customer_details, get_price

# Load environment variables
load_dotenv()
app = FastAPI()

class PriceRequest(BaseModel):
    item_name: str
    quantity: int
    
@app.post("/price")
async def price(request: PriceRequest):
    print(f"Calculating price for {request.quantity} * {request.item_name}")
    price = tools.get_price(request.item_name, request.quantity)
    return {"price": price}

@app.post("/webhook")
async def ultravox_conection(request: Request):
    data = await request.json()
    print(f"Incoming Webhook Data: {json.dumps(data, indent=2)}")
    
    # Infer tool based on payload keys
    if "cart_items" in data and "first_name" not in data:
        print("Detected Tool: calculate_order")
        return calculate_order(data.get("cart_items"))
        
    elif "address_txt" in data:
        print("Detected Tool: validate_delivery_address")
        return validate_delivery_address(data.get("address_txt"))
    
    elif "first_name" in data and "cart_items" in data:
        print("Detected Tool: customer_details")
        return customer_details(
            data.get("first_name"),
            data.get("last_name"),
            data.get("phone"),
            data.get("address"),
            data.get("cart_items")
        )
    
    elif "item_name" in data and "quantity" in data:
        print("Detected Tool: get_price")
        return get_price(
            data.get("item_name"),
            data.get("quantity"),
            data.get("dish_type", "standard")
        )

    print("Error: Unknown Tool signature")
    return {"error": "Could not identify tool from arguments"}

    print("Error: Unknown Tool signature")
    return {"error": "Could not identify tool from arguments"}

@app.post("/webhook")
async def ultravox_conection(request: Request):
    data = await request.json()
    print(f"Incoming Webhook Data: {json.dumps(data, indent=2)}")
    return dispatch_tool(data)