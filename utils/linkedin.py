import requests
import logging
from datetime import datetime, timedelta
import pandas as pd

TOKEN_URL = 'https://www.linkedin.com/oauth/v2/accessToken'

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
    if 'access_token' in response_data:
        return response_data['access_token']
    else:
        logging.error("Failed to obtain access token")
        return None

def fetch_linkedin_profile(token, api_version):
    headers = {
        'Authorization': f"Bearer {token}",
        'cache-control': 'no-cache',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': api_version
    }
    profile_response = requests.get('https://api.linkedin.com/v2/me', headers=headers)
    email_response = requests.get('https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))', headers=headers)

    if profile_response.status_code == 200 and email_response.status_code == 200:
        profile_data = profile_response.json()
        email_data = email_response.json()
        return profile_data, email_data['elements'][0]['handle~']['emailAddress']
    else:
        logging.error("Failed to fetch LinkedIn profile")
        return None, None

def fetch_ads_report(token, cmt_account_id):
    headers = {
        'Authorization': f"Bearer {token}",
        'cache-control': 'no-cache',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    end_date = datetime.now()
    start_date = end_date - timedelta(days=60)
    report_api_url = (
        f'https://api.linkedin.com/rest/adAnalytics?q=analytics'
        f'&dateRange=(start:(year:{start_date.year},month:{start_date.month},day:{start_date.day}),'
        f'end:(year:{end_date.year},month:{end_date.month},day:{end_date.day}))'
        f'&timeGranularity=(value:ALL)'
        f'&accounts=List(urn%3Ali%3AsponsoredAccount%3A{cmt_account_id})'
        f'&pivot=MEMBER_COMPANY'
        f'&fields=pivotValues,costInUsd,impressions,clicks,totalEngagements,externalWebsiteConversions,'
        f'externalWebsitePostViewConversions,externalWebsitePostClickConversions,oneClickLeads'
    )
    response = requests.get(report_api_url, headers=headers)
    response.raise_for_status()  # Raise an exception for HTTP errors
    report_data = response.json().get('elements', [])
    df = pd.DataFrame(report_data)
    df['pivotValues'] = df['pivotValues'].apply(lambda x: x[0] if x else None)
    df.rename(columns={'pivotValues': 'organizationUrn'}, inplace=True)
    organization_ids = df['organizationUrn'].str.split(':').str[-1]
    organization_lookup_url = f'https://api.linkedin.com/rest/organizationsLookup?ids=List({",".join(organization_ids)})'
    org_response = requests.get(organization_lookup_url, headers=headers)
    company_names = {}
    if org_response.status_code == 200:
        org_data = org_response.json()
        for org_id, org_info in org_data['results'].items():
            company_names[org_id] = org_info['localizedName']
    df['companyName'] = df['organizationUrn'].str.split(':').str[-1].map(company_names.get)
    return df[df['companyName'].notna()].to_dict(orient='records')
