from flask import Flask, request, jsonify, render_template
from calendar_utils import authenticate_google_calendar, get_upcoming_events, create_group_calendar, add_event_to_calendar, clear_calendar, get_calendar_events
from group_utils import Group, User
from googleapiclient.discovery import build
from datetime import datetime
from flask import abort
from flask_cors import CORS
from group_utils import Group
import openai, json

def verify_group_exists(group_id):
    try:
        Group.get_group_by_id(group_id)
        return True
    except ValueError:
        return False


app = Flask(__name__)
CORS(app)  # This enables CORS for all routes

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/schedule/analyze', methods=['POST'])
def analyze_availability():
    data = request.json
    with open('groups_database.json', 'r') as f:
        groups_data = json.load(f)
    group_id = data.get('groupId')
    preferences = data.get('preferences')

    # Fetch group data
    group_info = groups_data.get(group_id)
    if not group_info:
        return jsonify({"error": "Group not found"}), 404

    # Construct the prompt for the AI
    system_content = "You are an AI assistant that analyzes group availability and preferences for travel planning."
    user_content = f"Analyze the availability for group '{group_info['name']}' with travel dates {group_info['travel_dates']} and the following preferences: {preferences}"


    client = openai.OpenAI(
        api_key="d546f9f2469f46799b08a638d01fbd98",
        base_url="https://api.aimlapi.com/",
    )
    
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=512,
    )
    
    analysis = chat_completion.choices[0].message.content
    
    return jsonify({
        "analysis": {
            "optimalSlots": analysis
        }
    })

@app.route('/api/schedule/suggest', methods=['POST'])
def generate_suggestions():
    data = request.json
    group_id = data.get('groupId')
    preferences = data.get('preferences')
    # Fetch group data
    with open('groups_database.json', 'r') as f:
        groups_data = json.load(f)
    group_info = groups_data.get(group_id)
    if not group_info:
        return jsonify({"error": "Group not found"}), 404

    # Construct the prompt for the AI
    system_content = "You are an AI assistant that generates travel schedule suggestions based on group preferences."
    user_content = f"Generate travel schedule suggestions for group '{group_info['name']}' with travel dates {group_info['travel_dates']} and the following preferences: {preferences}"

    client = openai.OpenAI(
        api_key="d546f9f2469f46799b08a638d01fbd98",
        base_url="https://api.aimlapi.com/",
    )
    
    chat_completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ],
        temperature=0.7,
        max_tokens=512,
    )
    
    suggestions = chat_completion.choices[0].message.content
    
    return jsonify({
        "suggestions": suggestions
    })


@app.route('/api/connect-calendar', methods=['POST'])
def connect_calendar():
    creds = authenticate_google_calendar()
    if creds:
        return jsonify({"message": "Calendar connected successfully."}), 200
    else:
        return jsonify({"error": "Failed to connect calendar."}), 400

@app.route('/api/calendar/providers', methods=['GET'])
def get_calendar_providers():
    pass


@app.route('/api/groups/create', methods=['POST'])
def create_group():
    data = request.json
    travel_dates = data['travelDates'].split('/')
    new_group = Group(data['name'], data['description'], travel_dates)
    return jsonify({"groupId": new_group.id, "message": "Group created successfully."}), 201

@app.route('/api/groups/join', methods=['POST'])
def join_group():
    data = request.json
    group_id = data['groupId']
    invitation_code = data['invitationCode']
    
    if group_id == invitation_code and verify_group_exists(group_id):
        group = Group.get_group_by_id(group_id)
        user = User(data['name'], data['email'])
        group.add_member(user)
        return jsonify({"message": "Joined group successfully."}), 200
    else:
        return jsonify({"error": "Invalid group ID or invitation code."}), 400


@app.route('/api/groups/<group_id>/add-member', methods=['POST'])
def add_member_to_group(group_id):
    data = request.json
    group = Group.get_group_by_id(group_id)  # Assume this method exists
    user = User(data['name'], data['email'])
    group.add_member(user)
    return jsonify({"message": f"User {user.name} added to the group."}), 200

@app.route('/api/groups/<group_id>/remove-member', methods=['POST'])
def remove_member_from_group(group_id):
    data = request.json
    group = Group.get_group_by_id(group_id)  # Assume this method exists
    user = User(data['name'], data['email'])
    group.remove_member(user)
    return jsonify({"message": f"User {user.name} removed from the group."}), 200

@app.route('/api/groups/<group_id>/info', methods=['GET'])
def get_group_info(group_id):
    try:
        group = Group.get_group_by_id(group_id)
        return jsonify(group.get_group_info()), 200
    except ValueError:
        return jsonify({"error": "Group not found"}), 404


@app.route('/api/groups/<group_id>/free-slots', methods=['GET'])
def get_free_slots(group_id):
    group = Group.get_group_by_id(group_id)  # Assume this method exists
    min_duration = int(request.args.get('min_duration', 30))
    free_slots = group.find_free_slots(min_duration)
    return jsonify({"free_slots": [{"start": slot[0].isoformat(), "end": slot[1].isoformat()} for slot in free_slots]}), 200

@app.route('/api/groups/<group_id>/add-activity', methods=['POST'])
def add_group_activity(group_id):
    data = request.json
    group = Group.get_group_by_id(group_id)  # Assume this method exists
    start_time = datetime.fromisoformat(data['start_time'])
    end_time = datetime.fromisoformat(data['end_time'])
    group.add_group_activity(data['activity_name'], start_time, end_time)
    return jsonify({"message": "Group activity added successfully."}), 200

@app.route('/api/calendar/events', methods=['GET'])
def get_events():
    group_id = request.args.get('groupId')
    group = Group.get_group_by_id(group_id)
    if group:
        events = get_calendar_events(group.service, group.id)
        return jsonify({"events": events}), 200
    else:
        return jsonify({"error": "Group not found"}), 404
    
from datetime import datetime, timezone

@app.route('/api/calendar/availability', methods=['GET'])
def get_calendar_availability():
    group_id = request.args.get('groupId')
    date_range = request.args.get('dateRange')
    
    group = Group.get_group_by_id(group_id)
    start_date, end_date = date_range.split('/')
    
    free_slots = group.find_free_slots()
    suggested_time = (
        datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc),
        datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
    )
    
    is_available = any(start <= suggested_time[0] and suggested_time[1] <= end for start, end in free_slots)
    
    return jsonify({
        "isAvailable": is_available,
        "suggestedTime": {
            "start": suggested_time[0].isoformat(),
            "end": suggested_time[1].isoformat()
        }
    }), 200



if __name__ == '__main__':
    app.run(debug=True)
