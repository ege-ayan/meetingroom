from flask import Flask, render_template, redirect, url_for, session, jsonify
import msal
import requests
import json
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

@app.route('/dashboard')
def dashboard():
    access_token = session.get('access_token')
    if not access_token:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(ENDPOINT, headers=headers)
    if response.status_code == 200:
        events = response.json()
        return render_template('dashboard.html', events=events)
    else:
        return f"Error: {response.status_code} {response.json()}"

if __name__ == '__main__':
    app.run(debug=True)
