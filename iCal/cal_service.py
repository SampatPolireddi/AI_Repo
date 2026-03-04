import os
import datetime
import caldav
from caldav.elements import dav
from dotenv import load_dotenv

load_dotenv()
ICLOUD_USERNAME = os.getenv("ICLOUD_USERNAME")
ICLOUD_APP_SPECIFIC_PASSWORD = os.getenv("ICLOUD_APP_SPECIFIC_PASSWORD")

#Returns primary cal
def get_calendar():
    client = caldav.DAVClient(
        url="https://caldav.icloud.com/",
        username=ICLOUD_USERNAME,
        password=ICLOUD_APP_SPECIFIC_PASSWORD
    )
    principal = client.principal()
    calendars = principal.calendars()
    
    if not calendars:
        raise Exception("No calendars found")

    best_match = None
    selected_cal = None
    cal_map = {}
    
    print(f"Found {len(calendars)} calendars:")
    for calendar in calendars:
        display_name = "Unknown"
        try:
            properties = calendar.get_properties([dav.DisplayName])
            display_name = properties.get(dav.DisplayName, "Unknown")
        except Exception as e:
            print(f"Warning: Could not fetch properties for calendar: {e}")
            display_name = str(calendar)
            
        print(f" - {display_name}")
        cal_map[display_name] = calendar

        ignored_keywords = ["holiday", "birthday", "siri", "contact", "subscribed", "reminders", "tasks"] #These are specific to my calendar. May vary
        is_ignored = any(keyword in display_name.lower() for keyword in ignored_keywords)
        
        if not is_ignored:
            try:
                if "reminders" in str(calendar.url).lower():
                    is_ignored = True
            except:
                pass

        if not best_match and not is_ignored:
            best_match = calendar

    # Prioritize Home, then Calendar, then Work, then Personal 
    #Specific to my apple acc. Could vary
    for name in ["Home", "Calendar", "Work", "Personal"]:
        # Case-insensitive check
        for map_name, cal in cal_map.items():
            if name.lower() == map_name.lower():
                selected_cal = cal
                break
        if selected_cal:
            break

    if not selected_cal:
        selected_cal = best_match
        
    if not selected_cal:
        # Fallback: try to find any calendar that isn't obviously a task list or read-only
        for calendar in calendars:
            name_check = str(calendar).lower()
            if "reminders" not in name_check and "holiday" not in name_check and "subscribed" not in name_check:
                selected_cal = calendar
                break
                
    if not selected_cal:
        selected_cal = calendars[0]
    
    print(f"Selected calendar object: {selected_cal}")
    return selected_cal

#Returns all events on given date
def check_availability(date: str) -> str:
    if not date:
        return "Error: Date is required."
        
    calendar = get_calendar()
    try:
        # Handle potential ISO format with time included by stripping it
        if "T" in date:
            date = date.split("T")[0]
            
        query_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "Invalid date format. Please use YYYY-MM-DD."

    events = calendar.search(
        start=datetime.datetime.combine(query_date, datetime.time.min),
        end=datetime.datetime.combine(query_date, datetime.time.max),
        event=True, expand=True
    )
    
    if not events:
        return "No existing appointments. The doctor is available all day."
    
    result = []
    for event in events:
        c = event.icalendar_component
        uid = c.get('uid')
        summary = c.get('summary')
        
        dtstart = c.get('dtstart')
        dtend = c.get('dtend')
        
        if dtstart:
            if isinstance(dtstart.dt, datetime.datetime):
                start = dtstart.dt.strftime('%H:%M')
            else:
                start = "All Day"
        else:
            start = "Unknown"
            
        if dtend:
            if isinstance(dtend.dt, datetime.datetime):
                end = dtend.dt.strftime('%H:%M')
            else:
                end = "All Day"
        else:
            end = "Unknown"
            
        result.append(f"- {summary}: {start} to {end}")
        
    return "Existing appointments (Doctor is busy during these times):\n" + "\n".join(result)

#Creates new event in cal
def book_appointment(patient_name:str, start_time:str, end_time:str)->str:
    if not patient_name or not start_time or not end_time:
        return "Error: Missing required fields (patient_name, start_time, end_time)."

    calendar = get_calendar()
    try:
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)
    except ValueError:
        return "Error: Invalid time format. Use ISO 8601."
    
    try:
        event = calendar.save_event(
            dtstart = start_dt, dtend = end_dt,
            summary=f"Appointment: {patient_name}"
        )
        uid = event.icalendar_component.get('uid')
        return f"Booked for {patient_name}. ID: {uid}"
    except Exception as e:
        print(f"Error booking appointment: {e}")
        return f"Error booking appointment: {str(e)}"