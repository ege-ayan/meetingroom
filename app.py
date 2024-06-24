from flask import Flask, render_template, redirect, url_for, session, jsonify, request
import msal
import requests
import json
from datetime import datetime, date, time, timedelta
from dateutil import parser
from config import CLIENT_ID, CLIENT_SECRET, AUTHORITY, SCOPE, ENDPOINT

app = Flask(__name__)
app.secret_key = 'a_secure_random_key'  # Replace with a real secret key

@app.route('/')
def index():
    app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = app_msal.initiate_device_flow(scopes=SCOPE)
    if 'user_code' not in flow:
        raise ValueError("Failed to create device flow. Err: %s" % json.dumps(flow, indent=4))

    session['flow'] = flow
    return render_template('index.html', message=flow['message'])

@app.route('/token')
def token():
    app_msal = msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)
    flow = session.get('flow')
    result = app_msal.acquire_token_by_device_flow(flow)
    if 'access_token' in result:
        session['access_token'] = result['access_token']
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'waiting'})

@app.route('/main_screen')
def main_screen():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    # For debugging: set the date to 18/04/2024 and time to 9:41 AM
    debug_date = datetime(2024, 4, 18, 9, 41)
    now_date = datetime.now()

    now = debug_date
    current_time = now.isoformat()
    today_start = datetime.combine(debug_date.date(), time.min).isoformat() + 'Z'
    today_end = datetime.combine(debug_date.date(), time.max).isoformat() + 'Z'

    response = requests.get(f"{ENDPOINT}?$filter=start/dateTime ge '{today_start}' and start/dateTime le '{today_end}'", headers=headers)
    if response.status_code == 200:
        events = response.json()
        room_available = True
        for event in events['value']:
            event_start = parser.parse(event['start']['dateTime'])
            event_end = parser.parse(event['end']['dateTime'])
            if event_start <= now <= event_end:
                room_available = False
                break
        return render_template('main_screen.html', events=events['value'], room_available=room_available, current_time=current_time)
    else:
        return f"Error: {response.status_code} {response.json()}"

@app.route('/event_details/<event_id>')
def event_details(event_id):
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(f"{ENDPOINT}/{event_id}", headers=headers)
    if response.status_code == 200:
        event = response.json()
        return render_template('event_details.html', event=event)
    else:
        return f"Error: {response.status_code} {response.json()}"

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('index'))

    if request.method == 'POST':
        event_data = {
            "subject": request.form['subject'],
            "body": {
                "contentType": "HTML",
                "content": request.form['body']
            },
            "start": {
                "dateTime": request.form['start'],
                "timeZone": "UTC"
            },
            "end": {
                "dateTime": request.form['end'],
                "timeZone": "UTC"
            },
            "location": {
                "displayName": request.form['location']
            },
            "attendees": [
                {
                    "emailAddress": {
                        "address": request.form['attendee'],
                        "name": request.form['attendee_name']
                    },
                    "type": "required"
                }
            ]
        }

        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.post(ENDPOINT, headers=headers, json=event_data)
        if response.status_code == 201:
            return redirect(url_for('main_screen'))
        else:
            return f"Error: {response.status_code} {response.json()}"

    return render_template('create_event.html')

if __name__ == '__main__':
    app.run(debug=True)
