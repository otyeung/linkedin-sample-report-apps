import requests
from flask import Flask, redirect, request, session, url_for, render_template, jsonify, send_file
import io
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_wtf.csrf import CSRFProtect
import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import secrets
from dotenv import dotenv_values
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
#logging.basicConfig(level=logging.DEBUG)

# Determine the correct .env file path
env_path = Path('.env.local') if Path('.env.local').exists() else Path('.env')
print(f"Loading {env_path} file")

# Load environment variables into a dictionary
env_vars = dotenv_values(dotenv_path=env_path)

# Debug function to print environment variables
def print_env_vars():
    logging.debug("Environment variables after loading:")
    for key, value in env_vars.items():
        logging.debug(f"{key}: {value}")

print_env_vars()  # Print environment variables after loading

# Flask app setup
app = Flask(__name__)
app.secret_key = env_vars.get('FLASK_SECRET_KEY', '73cacfc5')  # Use a secure, randomly generated secret key

# LinkedIn OAuth credentials
CLIENT_ID = env_vars.get('CLIENT_ID')
CLIENT_SECRET = env_vars.get('CLIENT_SECRET')
REDIRECT_URI = 'http://127.0.0.1:5000/login/authorized'
API_VERSION = env_vars.get('API_VERSION')
AUTHORIZATION_URL = 'https://www.linkedin.com/oauth/v2/authorization'
TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'

# Report parameters
CMT_ACCOUNT_ID = env_vars.get('CMT_ACCOUNT_ID')
CMT_CAMPAIGN_ID = env_vars.get('CMT_CAMPAIGN_ID')

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

# Generate a secure secret key
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Initialize CSRF protection
csrf = CSRFProtect(app)

login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

@login_manager.unauthorized_handler
def unauthorized():
    return "Unauthorized!", 403

@app.route('/login')
def login():
    state = secrets.token_urlsafe(16)
    session['oauth_state'] = state
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'state': state,
        'scope': 'r_liteprofile,r_basicprofile,rw_ads,r_ads,r_emailaddress,r_ads_reporting'
    }
    url = requests.Request('GET', AUTHORIZATION_URL, params=params).prepare().url
    return redirect(url)

@app.route('/logout')
def logout():
    session.pop('linkedin_token', None)
    logout_user()
    return redirect(url_for('index'))

@app.route('/login/authorized')
def authorized():
    error = request.args.get('error', '')
    if error:
        logging.error(f"Error received: {error}")
        return f"Error received: {error}", 400

    state = request.args.get('state')
    if state != session.get('oauth_state'):
        logging.error("State mismatch error")
        return "State mismatch error", 400

    code = request.args.get('code')
    access_token = get_linkedin_access_token(code, REDIRECT_URI, CLIENT_ID, CLIENT_SECRET)
    if not access_token:
        return "Failed to obtain access token.", 400

    session['linkedin_token'] = access_token

    # Print the access token to the console
    logging.debug(f"Access Token: {session['linkedin_token']}")

    profile_data, email = fetch_linkedin_profile(access_token, API_VERSION)
    if not profile_data or not email:
        return "Failed to fetch profile information.", 400

    user_id = profile_data['id']
    first_name = profile_data['localizedFirstName']
    last_name = profile_data['localizedLastName']

    logging.debug(f"{user_id}, {first_name} {last_name}, Logged in with email: {email}")

    user = User(user_id)
    login_user(user)

    try:
        report_data = fetch_ads_report(access_token, CMT_ACCOUNT_ID, CMT_CAMPAIGN_ID)
        logging.debug(f"Report Data: {report_data}")

        if not report_data:
            raise ValueError("No report data available.")  # Raise custom exception

        session['report_data_list'] = report_data  # Store the data in session
        return render_template('report.html', report_data=report_data)

    except ValueError as ve:
        logging.error(f"ValueError: {str(ve)}")
        return str(ve), 400  # Return the error message to the user interface

    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error: {req_err}")
        return jsonify({"error": "Request error", "message": str(req_err)}), 500


@app.route('/')
def index():
    return render_template("index.html")

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    # Protected route
    return "Protected route, restricted to logged-in users only!"

def get_linkedin_access_token(code, redirect_uri, client_id, client_secret):
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri,
        'client_id': client_id,
        'client_secret': client_secret
    }
    response = requests.post(TOKEN_URL, data=data)
    response_data = response.json()
    return response_data.get('access_token')

def fetch_linkedin_profile(access_token, api_version):
    headers = {
        'Authorization': f"Bearer {access_token}",
        'cache-control': 'no-cache',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': api_version
    }
    response = requests.get('https://api.linkedin.com/v2/me', headers=headers)
    profile_data = response.json()

    response = requests.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))', headers=headers)
    email_data = response.json()

    email = email_data['elements'][0]['handle~']['emailAddress']
    return profile_data, email

def fetch_ads_report(access_token, account_ids, campaign_ids):
    headers = {
        'Authorization': f"Bearer {access_token}",
        'cache-control': 'no-cache',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': API_VERSION
    }

    end_date = datetime.now()
    start_date = end_date - timedelta(days=REPORT_PERIOD)

    # Ensure account_ids is a list
    if isinstance(account_ids, str):
        account_ids = account_ids.split(',')
    accounts_list = ",".join([f"urn%3Ali%3AsponsoredAccount%3A{account_id.strip()}" for account_id in account_ids])
    logging.info(f"accounts_list: {accounts_list}")

    # Initialize campaigns_list as an empty string
    campaigns_list = ''

    # Ensure campaign_ids is a list and not empty
    if isinstance(campaign_ids, str) and campaign_ids != '':
        campaign_ids = campaign_ids.split(',')
        campaigns_list = ",".join([f"urn%3Ali%3AsponsoredCampaign%3A{campaign_id.strip()}" for campaign_id in campaign_ids])
        logging.info(f"campaigns_list: {campaigns_list}")

    report_api_url = (
        f'https://api.linkedin.com/rest/adAnalytics?q=analytics'
        f'&dateRange=(start:(year:{start_date.year},month:{start_date.month},day:{start_date.day}),'
        f'end:(year:{end_date.year},month:{end_date.month},day:{end_date.day}))'
        f'&timeGranularity=(value:ALL)'
        f'&accounts=List({accounts_list})'
    )

    # Add campaigns_list to report_api_url if not empty
    if campaigns_list:
        report_api_url += f'&campaigns=List({campaigns_list})'

    # Add the rest of parameters to report_api_url
    report_api_url += (
        f'&pivot=MEMBER_COMPANY'
        f'&fields=pivotValues,costInUsd,impressions,clicks,comments,commentLikes,follows,likes,opens,reactions,sends,shares,companyPageClicks,'
        f'totalEngagements,otherEngagements,viralOtherEngagements,viralTotalEngagements,externalWebsitePostViewConversions,externalWebsitePostClickConversions,oneClickLeads'
    )

    logging.info(f"Report API URL: {report_api_url}")

    # Generate curl command for debug message
    curl_command = f"curl -X GET '{report_api_url}' -H 'Authorization: Bearer {access_token}' -H 'X-Restli-Protocol-Version: 2.0.0' -H 'LinkedIn-Version: {API_VERSION}'"
    logging.debug(f"curl command for API request:\n{curl_command}")

    try:
        response = requests.get(report_api_url, headers=headers)
        response.raise_for_status()  # Raise an exception for HTTP errors

        report_data = response.json().get('elements', [])

        if not report_data:  # Handle case where report_data is empty
            raise ValueError("No report data available.")  # Raise custom exception

        df = pd.DataFrame(report_data)

        df['pivotValues'] = df['pivotValues'].apply(lambda x: x[0] if x else None)
        df.rename(columns={'pivotValues': 'organizationUrn'}, inplace=True)

        organization_ids = df['organizationUrn'].str.split(':').str[-1]
        organization_lookup_url = f'https://api.linkedin.com/rest/organizationsLookup?ids=List({",".join(organization_ids)})'
        response = requests.get(organization_lookup_url, headers=headers)

        company_names = {}
        if response.status_code == 200:
            json_data = response.json()
            for org_id, org_data in json_data['results'].items():
                company_names[org_id] = org_data['localizedName']

        df['companyName'] = df['organizationUrn'].str.split(':').str[-1].map(company_names.get)

        # Remove rows where companyName is None
        df = df[df['companyName'].notna()]

        # Format the costInUsd to two decimal places
        if 'costInUsd' in df.columns:
            df['costInUsd'] = pd.to_numeric(df['costInUsd'], errors='coerce')  # coerce errors to NaN
            df['costInUsd'] = df['costInUsd'].apply(lambda x: f"{x:.2f}" if not pd.isnull(x) else None)

        return df.to_dict(orient='records')  # Return DataFrame as dictionary

    except requests.exceptions.RequestException as req_err:
        logging.error(f"Request error: {req_err}")
        return None  # Handle the error gracefully

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
