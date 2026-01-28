import json
import os
from dotenv import load_dotenv
import googlemaps
import random
import re
from thefuzz import process

load_dotenv()

# Load the menu with absolute path safety
base_dir = os.path.dirname(os.path.abspath(__file__))
menu_path = os.path.join(base_dir, "latestMenu.json")
with open(menu_path, 'r', encoding='utf-8') as f:
    menu_data = json.load(f)

#Func to convert "$5.99" to 5.99
def parse_price(price_str:str) -> float:
    if not price_str: return 0.0
   
    # removing '$' and take first part if there's extra text
    clean_str = price_str.replace("$","").split()[0]
    try:
        return float(clean_str)
    except ValueError:
        return 0.0

full_menu = menu_data.get("menu",{})

all_valid_names = []
for sections, items in full_menu.items():
    if isinstance(items, list):
        for item in items:
            name = item.get("name")
            if name: 
                all_valid_names.append(name.lower())
            
            variations = item.get("voice_variations", [])
            all_valid_names.extend([v.lower() for v in variations if v])

#Helper func to  fuzzy name matching
def fuzzy(item_name:str)->str:
        best_match, score = process.extractOne(item_name.lower(), all_valid_names)

        if score < 80:
            print(f"NO CONFIDENT MATCH FOUND FOR {item_name}, THE BEST MATCH IS FOR {best_match} WITH A SCORE OF {score}")
            return item_name
        else:
            print(f"BEST MATCH FOUND FOR {item_name}, THE BEST MATCH IS FOR {best_match} WITH A SCORE OF {score} ")
            return best_match

def get_price(item_name: str, quantity: int, dish_type: str) -> float:
    
    lookup_name = fuzzy(item_name.strip()) #dish name
    item_type = dish_type.lower().strip() #To check if the dish has gravy/dry option pricing
    full_menu = menu_data.get("menu",{})

    for sections, items in full_menu.items(): 
        if isinstance(items,list):              #Ex: Dosa Sec in menu data
            for item in items:
                if item.get("name","").lower() == lookup_name:  
                    try:
                        price_data = item.get("price")
                        if not price_data:
                            # If no simple price, checking under price options
                            # If key doesn't exis: returns None or raises error depending on access
                            options = item.get("price_options", {})
                            if options and item_type in options:
                                price_data = options[item_type]
                            else:
                                # Check for variations (e.g. Naan methods)
                                variations = item.get("variations", [])
                                found_var = False
                                for var in variations:
                                    if item_type and item_type in var.get("type", "").lower():
                                        price_data = var.get("price")
                                        found_var = True
                                        break
                                
                                if not found_var:
                                    return 0.0 # Return 0 if type not found or no options
        
                        return parse_price(price_data) * quantity
                    except (KeyError, TypeError, AttributeError):
                        return 0.0
                
                #Else: Checking for voice variations
                if "voice_variations" in item:
                    variations=item.get("voice_variations",[])      
                    for v in variations:
                        if v.lower()==lookup_name:
                            try:
                                price_data = item.get("price")
                                if not price_data:
                                    options = item.get("price_options", {})
                                    if options and item_type in options:
                                        price_data = options[item_type]
                                    else:
                                        # Check for variations (e.g. Naan methods)
                                        variations = item.get("variations", [])
                                        found_var = False
                                        for var in variations:
                                            if item_type and item_type in var.get("type", "").lower():
                                                price_data = var.get("price")
                                                found_var = True
                                                break
                                        
                                        if not found_var:
                                            return 0.0
                                return parse_price(price_data) * quantity
                            except (KeyError, TypeError, AttributeError):
                                return 0.0
    print(f"Item name: {item_name} NOT FOUND in menu")
    return 0.0

def calculate_order(cart_items: dict) -> dict:
    # Ex: cart_items={'gobi_manchurian': [1, 'gravy', 'notes'], ...}
    total_price = 0.0
    breakdown = []
    
    for item_name, details in cart_items.items():
        qty = details[0]
        style = details[1]
        notes = details[2] if len(details) > 2 else ""
        
        # Calculate line item price
        # get_price returns total for that quantity. e.g. 2 * 12.99
        line_price = get_price(item_name, qty, style)
        unit_price = line_price / qty if qty > 0 else 0.0
        
        total_price += line_price
        
        breakdown.append({
            "item": item_name,
            "quantity": qty,
            "style": style,
            "notes": notes,
            "unit_price": unit_price,
            "line_total": line_price
        })

    return {
        "total_price": total_price,
        "breakdown": breakdown
    }

GMAPS_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
gmaps = googlemaps.Client(key=GMAPS_KEY)

def validate_delivery_address(address_txt:str) ->dict:
    SERVICEABLE_ZIPS = ["75034", "75035", "75033", "75093"]
    SERVICEABLE_CITIES = ["frisco", "plano"]
    try:
        response = gmaps.addressvalidation(
            [address_txt],
            enableUspsCass = True #US addresses
        )
        result = response.get('result',{})
        verdict = result.get('verdict',{})
        usps_data = result.get('uspsData',{})

        # Extracting dpv info from gmap response
        dpv = usps_data.get('dpvConfirmation','')

        """
        DPV "Y": The address is 100% confirmed.
        DPV "D": The street and building are correct, but the Apartment/Suite is missing.
        DPV "S": The street and building are correct, but the Apartment/Suite is wrong (e.g., they said "Apt 5" but only Apts 1-4 exist).
        DPV "N": The house number simply doesn't exist on that street.
        """

        #Handling missing apt number
        if dpv in ['D','S'] or verdict.get('possibleNextAction') == 'CONFIRM_ADD_SUBPREMISES':
            return{
                "valid": False,
                "status": "missing_subpremise",
                "message": "Could you please provide the apartment or suite number?"
            }
        
        #Handling invalid apt number
        if dpv == 'N' or verdict.get('validationGranularity') not in ['PREMISE',"SUBPREMISE"]:
            return{
                "valid": False,
                "status": "invalid_address",
                "message": "Could not find the specified house number, could you please repeat the full address"
            }
        
        #Checking if address is in servicable zips
        std_address = usps_data.get('standardizedAddress',{})
        zip_code = std_address.get('zipCode','').split('-')[0][:5] #Slicing the first 5 numbers of zip, ex: 75034-1234
        city = std_address.get('city','').lower()

        if zip_code in SERVICEABLE_ZIPS or city in SERVICEABLE_CITIES:
            return{
                "valid":True,
                "status": "success",
                "message": "Address verified",
                "formatted_address": result.get('address',{}).get('formattedAddress')
            }
        else:
            return{
                "valid":False,
                "status": "out_of_range",
                "message": "The given address is outside our delivery zone. Shall we do a pickup order instead?"
            }
    except Exception as e:
        print(f"Address Validation Error: {e}")
        return{
            "valid":False,
            "message": "Having trouble in verifying the address, could you please repeat the complete address"
            }


def customer_details(first_name:str, last_name:str, phone:str, address:str, cart_items:dict) -> dict:
    try:
        clean_first = first_name.strip().capitalize()
        clean_last = last_name.strip().capitalize()
        clean_phone = re.sub(r'\D','', str(phone))

        #Checking if phone numb is 10 digits
        if len(clean_phone) !=10:
            return{
                "success": False,
                "message": "The phone number is invalid. Please repeat your phone number"
            }
        
        order_id = random.randint(100, 999) #Assigning random int for testing purpose
        
        #Customer record using the passed items
        customer_record = {
            "Full name": f"{clean_first} {clean_last}",
            "Phone": clean_phone,
            "address": address,
            "order_id": order_id,
            "order_details": cart_items
        }
        print(f"Customer Record: {customer_record}")

        return{
            "success": True,
            "message": f"Thank you, {clean_first} your order has been placed",
            "order_id": f"Order id: {order_id}"
        }
    except Exception as e:
        print(f"Customer Details Error: {e}")
        return{
            "success": False,
            "message": "ERROR, please try again"
        }

