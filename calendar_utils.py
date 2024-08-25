import os.path
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from googleapiclient.errors import HttpError
from travel_plan_parser import TravelEvent
from typing import List
from datetime import datetime, timedelta
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_google_calendar(token_file='token.json'):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_calendar_events(service, calendar_id='primary', time_min=None, time_max=None):
    if not time_min:
        time_min = datetime.utcnow().isoformat() + 'Z'
    if not time_max:
        time_max = (datetime.utcnow() + timedelta(days=365)).isoformat() + 'Z'
    
    events_result = service.events().list(calendarId=calendar_id, timeMin=time_min,
                                          timeMax=time_max, singleEvents=True,
                                          orderBy='startTime').execute()
    return events_result.get('items', [])
def add_travel_plan_to_calendar(service, travel_plan_events: List[TravelEvent], calendar_id='primary'):
    for event in travel_plan_events:
        start_datetime = f"{event.date}T{event.start_time}:00"
        end_datetime = f"{event.date}T{event.end_time}:00"
        
        calendar_event = {
            'summary': event.title,
            'description': event.description,
            'start': {
                'dateTime': start_datetime,
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': end_datetime,
                'timeZone': 'UTC',
            },
        }
        
        try:
            service.events().insert(calendarId=calendar_id, body=calendar_event).execute()
            print(f"Event created: {event.title}")
        except HttpError as error:
            print(f"An error occurred: {error}")

def get_upcoming_events(service):
    now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])

    event_list = []
    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))
        summary = event['summary']
        event_list.append((start, end, summary))
    return event_list

def create_group_calendar(service, calendar_info):
    calendar = calendar_info
    try:
        created_calendar = service.calendars().insert(body=calendar).execute()
        return created_calendar['id']
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def add_event_to_calendar(service, calendar_id, event):
    try:
        event = service.events().insert(calendarId=calendar_id, body=event).execute()
        return event['id']
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

def clear_calendar(service, calendar_id):
    try:
        events = service.events().list(calendarId=calendar_id).execute()
        for event in events.get('items', []):
            service.events().delete(calendarId=calendar_id, eventId=event['id']).execute()
    except HttpError as error:
        print(f'An error occurred: {error}')

def get_user_calendar_events():
    creds = authenticate_google_calendar()
    service = build('calendar', 'v3', credentials=creds)
    return get_upcoming_events(service)

if __name__ == '__main__':
    events = get_upcoming_events()
    for event in events:
        print(event)


def analyze_combined_calendar(user_creds_list, duration_days):
    combined_events = []
    for user_creds in user_creds_list:
        user = user_creds['email']
        creds = user_creds['credentials']
        service = build('calendar', 'v3', credentials=creds)
        events = get_calendar_events(service)
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            combined_events.append({
                'user': user,
                'summary': event['summary'],
                'start': datetime.fromisoformat(start.replace('Z', '+00:00')),
                'end': datetime.fromisoformat(end.replace('Z', '+00:00'))
            })
    
    combined_events.sort(key=lambda x: x['start'])
    
    # Find potential travel dates
    today = datetime.now()
    end_date = today + timedelta(days=365)
    potential_dates = []
    
    current_date = today
    while current_date < end_date:
        is_free_period = True
        for i in range(duration_days):
            check_date = current_date + timedelta(days=i)
            if any(event['start'].date() <= check_date.date() <= event['end'].date() for event in combined_events):
                is_free_period = False
                break
        
        if is_free_period:
            potential_dates.append(current_date)
        
        current_date += timedelta(days=1)
    
    return potential_dates[:5]  # Return top 5 potential start dates

def get_events_during_period(calendar_creds, start_date, end_date):
    events_during_period = []
    for user, creds in calendar_creds.items():
        service = build('calendar', 'v3', credentials=creds)
        events = get_calendar_events(service, time_min=start_date.isoformat() + 'Z', time_max=end_date.isoformat() + 'Z')
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            events_during_period.append({
                'user': user,
                'summary': event['summary'],
                'start': start,
                'end': end
            })
    return events_during_period