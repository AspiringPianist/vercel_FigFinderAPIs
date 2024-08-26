import streamlit as st
import google.generativeai as genai
from datetime import datetime, timedelta
import calendar_utils as cal_utils
from travel_plan_parser import parse_travel_plan
from tavily_api import get_tavily_search_results
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import plotly.graph_objects as go
import pdfkit
import os
from google_auth_oauthlib.flow import Flow
import json
from streamlit_oauth import OAuth2Component
from google.auth.transport.requests import Request
from supabase import create_client

# Initialize Streamlit app
st.set_page_config(page_title="FigFinder AI", layout="wide")

# Custom CSS
st.markdown("""
<style>
    body {
        background-color: #e6f3ff;
        color: #333333;
    }
    .stApp {
        background-color: #ffffff;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        padding: 20px;
        animation: fadeIn 0.5s ease-in-out;
    }
    .stButton > button {
        background-color: #4da6ff;
        color: white;
        border-radius: 5px;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #3385cc;
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    }
    .stTextInput > div > div > input {
        border-color: #4da6ff;
    }
    .stSelectbox > div > div > select {
        border-color: #4da6ff;
    }
    h1, h2, h3 {
        color: #0066cc;
    }
    .stPlotlyChart {
        animation: slideIn 0.5s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
    @keyframes slideIn {
        from { transform: translateY(20px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
</style>
""", unsafe_allow_html=True)


st.title('FigFinder AI')
st.subheader('Plan your next group trip with AI')

SUPABASE_URL = "https://oxekkilbifeicbrqvbue.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im94ZWtraWxiaWZlaWNicnF2YnVlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MjQ2MDM1NDcsImV4cCI6MjA0MDE3OTU0N30.2_KMELwEcpWj2q6WWJh92qWMk0aREIysbOTBDM1iwlc"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize session state variables
if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {}
if 'trip_details' not in st.session_state:
    st.session_state.trip_details = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = ""
if 'calendar_creds' not in st.session_state:
    st.session_state.calendar_creds = {}
if 'token' not in st.session_state:
    st.session_state.token = None
if 'suggested_dates' not in st.session_state:
    st.session_state.suggested_dates = []

client_id = "647775398332-gq8t0dkgs4u4pe18anbftm65dkojj9hl.apps.googleusercontent.com"
client_secret = "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"
redirect_uri = "http://localhost:8501/callback/"  # For local testing
oauth2 = OAuth2Component(client_id, client_secret, redirect_uri,
                         authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
                         token_endpoint="https://oauth2.googleapis.com/token")

# Sidebar navigation
st.sidebar.title("🧭 Navigation")
sidebar_selection = st.sidebar.radio("Select Option", ["🏠 Travel Planner", "📅 Group Calendar", "💬 Chat History"])

# Function to refresh the token if it's expired
def refresh_credentials(creds):
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def google_auth_flow():
    flow = Flow.from_client_secrets_file(
        './credentials.json',
        scopes=['https://www.googleapis.com/auth/calendar']
    )
    flow.redirect_uri = "http://localhost:8501/callback/"  # Update this with your Streamlit app's URL

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    st.session_state.oauth_state = state
    st.markdown(f"Please [click here]({authorization_url}) to authorize access to your Google Calendar.")

    code = st.text_input("Enter the authorization code:")
    if code:
        flow.fetch_token(code=code)
        creds = flow.credentials
        return creds
    return None

def get_personalized_travel_plan(user_preferences, trip_details, calendar_events, chat_history=None):
    search_query = f"Travel tips and attractions for {trip_details['destination']}"
    search_results = get_tavily_search_results(search_query)
    
    search_content = ""
    if search_results:
        for result in search_results[:5]:
            search_content += f"- {result['title']}: {result['content']}\n"
    
    message = (
        f"Create a detailed travel itinerary in {user_preferences['language_preference']} for a group trip from "
        f"{trip_details['source']} to {trip_details['destination']}, starting on {trip_details['start_date']}, lasting for "
        f"{trip_details['duration']} days, within a budget of {trip_details['budget']}. Include preferences for {user_preferences['accommodation_preference']} accommodations, "
        f"a {user_preferences['travel_style']} travel style, and interests in {user_preferences['interests']}. "
        f"Dietary restrictions: {user_preferences['dietary_restrictions']}. Activity level: {user_preferences['activity_level']}. "
        f"Must-visit landmarks: {user_preferences['must_visit_landmarks']}."
        f"\n\nConsider these calendar events during the trip: {calendar_events}"
        f"\n\nAdditional information from search:\n{search_content}"
    )
    
    if chat_history:
        message += f"\n\nAlso consider this chat history for additional context:\n{chat_history}"
    
    genai.configure(api_key="AIzaSyC8QK1LuKtLdaCHM8cDj-Rttu1sNJ_J69s")
    model = genai.GenerativeModel('gemini-pro')
    
    response = model.generate_content(message)
    response_text = response.text
    
    parsed_plan = parse_travel_plan(response_text, trip_details['start_date'], trip_details['duration'])
    return response_text, parsed_plan

if sidebar_selection == "🏠 Travel Planner":
    with st.container():
        st.header("Travel Planner")
        
        col1, col2 = st.columns(2)
        with col1:
            st.session_state.trip_details['source'] = st.text_input('Source', 'New York')
            st.session_state.trip_details['duration'] = st.slider('Duration (days)', 1, 90, 7)
            st.session_state.trip_details['budget'] = st.number_input('Budget', min_value=100, value=1000, step=100)
        with col2:
            st.session_state.trip_details['destination'] = st.text_input('Destination', 'Los Angeles')
            st.session_state.user_preferences['language_preference'] = st.selectbox('Language Preference', ['English', 'Spanish', 'French', 'German', 'Japanese'], index=0)

        col3, col4 = st.columns(2)
        with col3:
            st.session_state.user_preferences['interests'] = st.text_input('Interests', 'historical sites, nature')
            st.session_state.user_preferences['activity_level'] = st.selectbox('Activity Level', ['Low', 'Moderate', 'High'])
            st.session_state.user_preferences['travel_style'] = st.selectbox('Travel Style', ['Relaxed', 'Fast-Paced', 'Adventurous', 'Cultural', 'Family-Friendly'])
        with col4:
            st.session_state.user_preferences['dietary_restrictions'] = st.text_input('Dietary Restrictions', 'None')
            st.session_state.user_preferences['accommodation_preference'] = st.selectbox('Accommodation Preference', ['Hotel', 'Hostel', 'Apartment', 'No Preference'])
            st.session_state.user_preferences['must_visit_landmarks'] = st.text_input('Must-Visit Landmarks', 'e.g., Eiffel Tower, Grand Canyon')

    if st.button("Suggest Travel Dates", key="suggest_dates"):
        if st.session_state.calendar_creds:
            if st.session_state.suggested_dates:
                st.session_state.trip_details['start_date'] = st.selectbox(
                    "Select a start date", 
                    options=st.session_state.suggested_dates,
                    format_func=lambda x: x.strftime("%Y-%m-%d")
                )
            else:
                potential_dates = cal_utils.analyze_combined_calendar(list(st.session_state.calendar_creds.values()), st.session_state.trip_details['duration'])
                if potential_dates:
                    st.session_state.trip_details['start_date'] = st.selectbox(
                        "Select a start date", 
                        options=potential_dates,
                        format_func=lambda x: x.strftime("%Y-%m-%d")
                    )
                else:
                    st.warning("No suitable dates found in the next year. Please try a shorter duration or check your calendar.")
        else:
            st.warning("Please connect at least one Google Calendar to get date suggestions.")

elif sidebar_selection == "📅 Group Calendar":
    st.header("Group Calendar")

    if 'token' not in st.session_state or 'access_token' not in st.session_state:
        result = oauth2.authorize_button("Authorize Google Calendar", 
                                         scope="https://www.googleapis.com/auth/calendar", redirect_uri=redirect_uri)
        if result:
            st.session_state.token = result
            st.rerun()

    if 'token' in st.session_state or 'access_token' in st.session_state:
        token_info = st.session_state.token
        if 'access_token' in st.session_state:
            token_info = st.session_state.access_token
            
        
        if isinstance(token_info, dict) and 'token' in token_info and 'access_token' in token_info['token']:
            credentials_data = {
                "token": token_info['token']['access_token'],
                "refresh_token": token_info['token'].get('refresh_token'),
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": client_id,
                "client_secret": client_secret,
                "scopes": ["https://www.googleapis.com/auth/calendar"]
            }
            
            creds = Credentials(**credentials_data)
            
            try:
                service = build('calendar', 'v3', credentials=creds)
                calendar_list = service.calendarList().list().execute()
                st.success("Successfully connected to Google Calendar!")
                
                # Get user email
                profile_info = service.calendarList().get(calendarId='primary').execute()
                email = profile_info['id']
                
                # Store the credentials in Supabase and session state
                try:
                    supabase.table("figfinder_data").upsert({
                        "email": email, 
                        "token": json.dumps({
                            "access_token": token_info['token']['access_token'],
                            "refresh_token": token_info['token'].get('refresh_token'),
                            "token_uri": "https://oauth2.googleapis.com/token",
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "scopes": ["https://www.googleapis.com/auth/calendar"]
                        })
                    }).execute()
                    st.success(f'Credentials stored for {email}')
                    
                    # Store in session state
                    st.session_state.calendar_creds[email] = creds
                    
                except Exception as e:
                    st.error(f"Error storing data in Supabase: {str(e)}")
                    st.error("Please check your Supabase setup and ensure it has the correct permissions.")
                
                
                # Display calendar information
                st.write("Your calendars:")
                for calendar in calendar_list['items']:
                    st.write(f"- {calendar['summary']}")
                    
            except Exception as e:
                st.error(f"Error connecting to Google Calendar: {str(e)}")
        else:
            st.error("Invalid token information. Please try authenticating again.")
            if 'token' in st.session_state:
                del st.session_state.token

    # Deta fetch section
    with st.expander("Connected Users"):
        try:
            response = supabase.table("figfinder_data").select("email").execute()
            connected_users = response.data
            for user in connected_users:
                st.write(user["email"])
        except Exception as e:
            st.error(f"Error fetching data from Supabase: {str(e)}")
            st.error("Please check your Supabase API key and ensure it has the correct permissions.")
            connected_users = []

    if st.button("Show Combined Calendar", key="show_calendar"):
        combined_events = []
        user_creds_list = []
        response = supabase.table("figfinder_data").select("email, token").execute()
        connected_users = response.data
        for user in connected_users:
            try:
                creds_json = json.loads(user["token"])
                
                # Check if creds_json has the expected structure
                access_token = creds_json['access_token']
                refresh_token = creds_json.get('refresh_token')

                creds = Credentials(
                    token=access_token,
                    refresh_token=refresh_token,
                    token_uri="https://oauth2.googleapis.com/token",
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=["https://www.googleapis.com/auth/calendar"]
                )
                user_creds_list.append({
                    'email': user['email'],
                    'credentials': creds
                })
                service = build('calendar', 'v3', credentials=creds)
                events = cal_utils.get_calendar_events(service)
                for event in events:
                    start = event['start'].get('dateTime', event['start'].get('date'))
                    end = event['end'].get('dateTime', event['end'].get('date'))
                    combined_events.append({
                        'user': user["email"],
                        'summary': event['summary'],
                        'start': datetime.fromisoformat(start.replace('Z', '+00:00')),
                        'end': datetime.fromisoformat(end.replace('Z', '+00:00'))
                    })
            except Exception as e:
                st.error(f"Error processing credentials for user {user['email']}: {str(e)}")
                continue

        fig = go.Figure()
        for event in combined_events:
            fig.add_trace(go.Bar(
                x=[event['start'], event['end']],
                y=[event['user']],
                orientation='h',
                name=event['summary'],
                hoverinfo='text',
                text=f"{event['summary']}<br>{event['start']} - {event['end']}",
            ))

        fig.update_layout(
            title="Combined Calendar",
            xaxis_title="Date",
            yaxis_title="User",
            height=400 + (len(connected_users) * 50),
            showlegend=False,
            plot_bgcolor='rgba(230, 243, 255, 0.8)',
            paper_bgcolor='rgba(230, 243, 255, 0.8)',
        )

        fig.update_traces(hoverinfo="text", hovertemplate=None)
        fig.update_layout(hovermode="closest")

        st.plotly_chart(fig)

        if 'trip_details' in st.session_state and 'duration' in st.session_state.trip_details:
            potential_dates = cal_utils.analyze_combined_calendar(user_creds_list, st.session_state.trip_details['duration'])
            if potential_dates:
                st.subheader("Potential Travel Dates")
                st.session_state.suggested_dates = potential_dates  # Save the suggested dates
                for date in potential_dates:
                    st.write(date.strftime("%Y-%m-%d"))
                
                # Add a button to save the suggested dates
                if st.button("Save Suggested Dates"):
                    st.success("Suggested dates have been saved and can be used in the Travel Planner.")
            else:
                st.warning("No suitable dates found for the specified duration. Try adjusting the trip duration.")
        else:
            st.info("Set your trip details in the Travel Planner to see potential travel dates.")

elif sidebar_selection == "💬 Chat History":
    st.header("Chat History")
    st.session_state.chat_history = st.text_area("Paste your group chat history here:", height=300)
    if st.button("Save Chat History", key="save_chat"):
        st.success("Chat history saved successfully!")

if st.button("Generate Travel Suggestion", key="generate_suggestion"):
    if st.session_state.trip_details and st.session_state.user_preferences and 'start_date' in st.session_state.trip_details:
        with st.spinner('🌍 Generating your personalized travel plan...'):
            try:
                start_date = st.session_state.trip_details['start_date']
                end_date = start_date + timedelta(days=st.session_state.trip_details['duration'])
                
                calendar_events = []
                response = supabase.table("figfinder_data").select("email, token").execute()
                connected_users = response.data
                for user in connected_users:
                    try:
                        creds_json = json.loads(user["token"])
                        creds_json['client_id'] = client_id
                        creds_json['client_secret'] = client_secret
                        creds = Credentials.from_authorized_user_info(creds_json)
                        
                        # Refresh the token if it's expired
                        creds = refresh_credentials(creds)
                        
                        service = build('calendar', 'v3', credentials=creds)
                        events = cal_utils.get_calendar_events(service, time_min=start_date.isoformat() + 'Z', time_max=end_date.isoformat() + 'Z')
                        calendar_events.extend(events)
                        
                        # Update the session state with the refreshed credentials
                        st.session_state.calendar_creds[user['email']] = creds
                    except Exception as e:
                        st.warning(f"Error processing calendar for user {user['email']}: {str(e)}")
                        continue

                response_text, parsed_plan = get_personalized_travel_plan(
                    st.session_state.user_preferences,
                    st.session_state.trip_details,
                    calendar_events,
                    st.session_state.chat_history
                )
                
                if response_text:
                    st.markdown(response_text)
                    
                    # Export to PDF
                    pdfkit.from_string(response_text, 'travel_plan.pdf')
                    with open('travel_plan.pdf', 'rb') as f:
                        pdf_bytes = f.read()
                    st.download_button(
                        label="Download Travel Plan as PDF",
                        data=pdf_bytes,
                        file_name="travel_plan.pdf",
                        mime="application/pdf"
                    )

                    if parsed_plan.events:
                        if st.button("Add to Google Calendar", key="add_to_calendar"):
                            for user, creds in st.session_state.calendar_creds.items():
                                try:
                                    service = build('calendar', 'v3', credentials=creds)
                                    cal_utils.add_travel_plan_to_calendar(service, parsed_plan.events)
                                except Exception as e:
                                    st.warning(f"Error adding events to calendar for user {user}: {str(e)}")
                            st.success("Travel plan added to Google Calendar(s)!")
                    else:
                        st.warning("No events could be parsed from the travel plan. Unable to add to calendar.")

                st.success('Here is your personalized travel plan')
            except Exception as e:
                st.error(f"An error occurred while generating the travel plan: {str(e)}")
    else:
        st.error('Please fill in all the necessary details and select a start date before generating a travel suggestion.')


# Footer
st.markdown("""
---
<div style="text-align: center; color: #666666;">
    Made with ❤️ by FigFinder AI Team | <a href="https://your-website.com">Visit our website</a>
</div>
""", unsafe_allow_html=True)
