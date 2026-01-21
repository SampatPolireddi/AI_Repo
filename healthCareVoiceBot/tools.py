import os
import requests
from dotenv import load_dotenv

load_dotenv()

MEDPLUM_CLIENT_ID = os.getenv("MEDPLUM_CLIENT_ID")
MEDPLUM_CLIENT_SECRET = os.getenv("MEDPLUM_CLIENT_SECRET")

MEDPLUM_TOKEN_URL = "https://api.medplum.com/oauth2/token"
MEDPLUM_FHIR_URL = "https://api.medplum.com/fhir/R4"

def get_medplum_token():  
    response = requests.post(
        MEDPLUM_TOKEN_URL,
        auth = (MEDPLUM_CLIENT_ID, MEDPLUM_CLIENT_SECRET),
        data={"grant_type":"client_credentials"}
    )
    if response.status_code!=200:
        print(f"Auth failed: {response.text}")
        return None
    return response.json().get("access_token")

def check_patient_db(name:str)->str:
    print(f"Searching Medplum for '{name}'...")
    
    token = get_medplum_token()
    if not token: return None
    
    headers = {"Authorization": f"Bearer {token}"}
    search_term = name.split(" ")[0]
    
    url = f"{MEDPLUM_FHIR_URL}/Patient?name:contains={search_term}"
    resp = requests.get(url, headers=headers)
    entries = resp.json().get("entry", [])
   
    if len(entries) > 0:
        patient = entries[0]["resource"]
        
        try:
            name_list = patient.get('name', [{}])[0]
            first = name_list.get('given', [''])[0]
            last = name_list.get('family', '')
            full_name = f"{first} {last}".strip()
            dob = patient.get('birthDate', 'Unknown')
            pt_id = patient.get('id', 'Unknown')
            
            return {
                "name": full_name,
                "dob": dob,
                "id": pt_id
            }
        except:
            return None
    else:
        print(f"NOT FOUND: {name}")
        return None

def create_patient_db(first_name:str, last_name:str, dob:str) ->str:
    
    print(f"Creating patient:'{first_name} {last_name} with dob: {dob}")
    
    token = get_medplum_token()
    if not token:
        return "ERROR_AUTH"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "resourceType": "Patient",
        "name": [
            {
                "use":"official",
                "given":[first_name],
                "family": last_name
            }
        ],
        "birthDate": dob
    }
    
    try:
        resp = requests.post(f"{MEDPLUM_FHIR_URL}/Patient", json=payload, headers=headers)
        
        if resp.status_code == 201:
            return f"Success: Registered {first_name} {last_name}."
        else:
            return f"Failed: Medplum returned {resp.status_code} - {resp.text}"
            
    except Exception as e:
        return f"Failed: Connection error {str(e)}"