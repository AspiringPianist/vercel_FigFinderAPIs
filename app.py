import os
import google.generativeai as genai
import streamlit as st
from datetime import date
import pdfkit
import sqlite3
import pandas as pd
import googlemaps
import tavily
# Initialize the application's title and subtitle
st.title('FigFinder AI')
st.subheader('Plan your next trip with AI')

# User input section in the sidebar
st.sidebar.header('Enter details to generate a travel plan:')
api_key = st.sidebar.text_input('Enter Your Google API Key', type="password")
source = st.sidebar.text_input('Source', 'New York')
destination = st.sidebar.text_input('Destination', 'Los Angeles')
date_input = st.sidebar.date_input('Travel Start Date', min_value=date.today())
date = date_input.strftime('%Y-%m-%d')
budget = st.sidebar.number_input('Budget', min_value=100, value=1000, step=100)
duration = st.sidebar.slider('Duration (days)', 1, 90, 7)
username = st.sidebar.text_input('Username')
password = st.sidebar.text_input('Password', type='password')
# Currency selector
currencies = ['USD', 'EUR', 'GBP', 'JPY', 'AUD']  # Add more currencies as needed
selected_currency = st.sidebar.selectbox('Select Currency', currencies)

# Additional user preferences
st.sidebar.subheader('Your Preferences:')
language_preference = st.sidebar.selectbox('Language Preference', ['English', 'Spanish', 'French', 'German', 'Japanese'], index=0)
interests = st.sidebar.text_input('Interests', 'historical sites, nature')
past_travel = st.sidebar.text_input('Past Travel Destinations', 'Paris, Tokyo')
dietary_restrictions = st.sidebar.text_input('Dietary Restrictions', 'None')
activity_level = st.sidebar.selectbox('Activity Level', ['Low', 'Moderate', 'High'])
specific_interests = st.sidebar.text_input('Specific Interests', 'art museums, hiking trails')
accommodation_preference = st.sidebar.selectbox('Accommodation Preference', ['Hotel', 'Hostel', 'Apartment', 'No Preference'])
travel_style = st.sidebar.selectbox('Travel Style', ['Relaxed', 'Fast-Paced', 'Adventurous', 'Cultural', 'Family-Friendly'])
must_visit_landmarks = st.sidebar.text_input('Must-Visit Landmarks', 'e.g., Eiffel Tower, Grand Canyon')
destinations = st.sidebar.multiselect('Select destinations to compare', ['New York', 'Los Angeles', 'Chicago', 'Miami'])

# Function to create a detailed message for the AI
@st.cache_data
def get_personalized_travel_plan(user_preferences, trip_details, api_key, selected_currency):
    genai.configure(api_key="AIzaSyC8QK1LuKtLdaCHM8cDj-Rttu1sNJ_J69s")
    tavily_results = search_tavily(f"{user_preferences['interests']} in {trip_details['destination']}")

    message = (
    f"Create a detailed travel itinerary in {user_preferences['language_preference']} focused on attractions, restaurants, and activities for a trip from "
    f"{trip_details['source']} to {trip_details['destination']}, starting on {trip_details['date']}, lasting for "
    f"{trip_details['duration']} days, within a budget of {selected_currency} {trip_details['budget']}. This should include daily timings, "
    f"preferences for {user_preferences['accommodation_preference']} accommodations, a {user_preferences['travel_style']} travel style, "
    f"and interests in {user_preferences['interests']}. Past travel includes {user_preferences['past_travel']}, dietary restrictions include "
    f"{user_preferences['dietary_restrictions']}, and the activity level is {user_preferences['activity_level']}. "
    f"Must-visit landmarks include {user_preferences['must_visit_landmarks']}. Also, provide a travel checklist relevant to the destination and duration. "
    f"Use the following search results to enhance the itinerary: {tavily_results}"
    )
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(message)
    return response.text
def search_tavily(query):
    client = tavily.TavilyClient(api_key="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")
    results = client.search(query)
    return results

def export_to_pdf(content):
    pdfkit.from_string(content, 'travel_plan.pdf')
    st.download_button(
        label="Download Travel Plan as PDF",
        data=open('travel_plan.pdf', 'rb'),
        file_name="travel_plan.pdf",
        mime="application/pdf"
    )
def compare_destinations(user_preferences, trip_details, api_key, selected_currency, destinations):
    comparisons = []
    for dest in destinations:
        tavily_results = search_tavily(f"{user_preferences['interests']} in {dest}")
        plan = get_personalized_travel_plan(user_preferences, trip_details, api_key, selected_currency, tavily_results)

        comparisons.append((dest, plan))

    for dest, plan in comparisons:
        st.subheader(f"Plan for {dest}")
        st.markdown(plan)

budget_categories = ['Accommodation', 'Food', 'Activities', 'Transportation', 'Miscellaneous']
budget_splits = {}

for category in budget_categories:
    budget_splits[category] = st.sidebar.slider(f'{category} Budget (%)', 0, 100, 20)

total_percentage = sum(budget_splits.values())
if total_percentage != 100:
    st.sidebar.warning(f"Total budget allocation is {total_percentage}%. Please adjust to 100%.")

# Collecting user preferences and trip details for travel planning
user_preferences = {
    'language_preference': language_preference,
    'interests': interests,
    'past_travel': past_travel,
    'dietary_restrictions': dietary_restrictions,
    'activity_level': activity_level,
    'specific_interests': specific_interests,
    'accommodation_preference': accommodation_preference,
    'travel_style': travel_style,
    'must_visit_landmarks': must_visit_landmarks
}
trip_details = {
    'source': source,
    'destination': destination,
    'date': date,
    'budget': budget,
    'duration': duration
}

# Button to generate the travel plan
if st.sidebar.button('Generate Travel Plan'):
    if api_key and source and destination and date and budget and duration:
        with st.spinner('Generating Travel Plan...'):
            response = get_personalized_travel_plan(user_preferences, trip_details, api_key, selected_currency)
            if response:
                st.markdown(response)
                #export_to_pdf(response)
        st.success('Here is your personalized travel plan in ' + language_preference)
        #.markdown(response)
    else:
        st.error('Please fill in all the fields to generate the travel plan.')

if st.sidebar.button('Compare Destinations'):
    compare_destinations(user_preferences, trip_details, api_key, selected_currency, destinations)