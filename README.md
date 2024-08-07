# LinkedIn Sample Report Apps (MVP)

## Introduction

This project sets up a basic Python Flask web application that allows users to log in using their LinkedIn member account through [OAuth 2.0 3-legged code flow](https://learn.microsoft.com/en-gb/linkedin/shared/authentication/authorization-code-flow?context=linkedin%2Fcontext&tabs=HTTPS1), retrieves authenticated user data and download ABM campaign performance report from Ads account.

MVP is meant to be a Minimum Viable Product (MVP) to validate a business idea with minimal resources and effort by releasing a basic version of the product that includes only the essential features (OAuth 2.0 and generate report workflow).

While MVP apps is not a full-blown production apps, developer is welcome to build on top of it to add more functionality and polish the user experience, or integrating into existing workflow.

## Pre-requistie

1. Create an app from [LinkedIn developer portal](https://developer.linkedin.com)
2. Make sure the app have added the "Advertising API" product. If it doesn't please request access. ![advertising api](screenshots/advertising_api.png)
3. Create [LinkedIn Ads account](https://www.linkedin.com/help/linkedin/answer/a426102/create-an-ad-account-in-campaign-manager-as-a-new-advertiser). Ads account should include historic / current campaign performance data
4. Assume all the above requirements are met, developer should be able to spin up a MVP apps in 5 minutes.

## How to run

1. Clone repository locally to your machine

   `git clone https://github.com/otyeung/linkedin-sample-report-apps`

2. Create virtual environment

   `python -m venv venv`

3. Activate virtual environment
   `source venv/bin/activate`

4. Install required Python library in virtual environment
   `pip install -r requirements.txt`

5. Copy your client id, client secret from developer portal to .env file. You should set the API_VERSION to the latest one according to [LinkedIn API documentation](https://learn.microsoft.com/en-us/linkedin/marketing/versioning?view=li-lms-2024-06) in the format "YYYYMM", it should NOT be older than 12 months from current date, for example :

```
CLIENT_ID=abcdefg
CLIENT_SECRET=abcdefg
API_VERSION=202406
```

6. Add your LinkedIn Ads account id in .env file <CMT_ACCOUNT_ID>. If you have multiple Ads accounts simply separate them by commas without space, e.g. "12345678,23456789,34567890" and the report metrics will be **aggregrated** across all Ads accounts. You must provide at least 1 Ads account id, authenticated user must have at least viewer access to the account, for example :

```
CMT_ACCOUNT_ID=12345678
```

```
CMT_ACCOUNT_ID=12345678,23456789,34567890
```

7. Add your LinkedIn Ads campaign id in .env file <CMT_CAMPAIGN_ID>. This is a campaign filter. If you have multiple campaign ids to be filter simply separate them by commas without space, e.g. "12345678,23456789,34567890" and the report metrics will be **filtered** across your selected campaigns, for example :

```
CMT_CAMPAIGN_ID=12345678
```

```

CMT_CAMPAIGN_ID=12345678,23456789,34567890

```

- If you don't want to filter by campaign, simply leave <CMT_CAMPAIGN_ID> line blank :

```

CMT_CAMPAIGN_ID=

```

8. You may change REPORT_PERIOD in .env file too, default value is 60 days.

```

REPORT_PERIOD=60

```

9. Provision redirect_url (http://127.0.0.1:5000/login/authorized) in the apps under LinkedIn developer portal. This is NECESSARY to complete the OAuth 3-legged redirect flow.
   ![redirect_url](screenshots/redirect_url.png)

10. Run flask app by
    `flask --app app run`

11. Open Chrome web browser in incognito window (or clear all caches and cookies \*.linkedin.com, 127.0.0.1)
    `http://127.0.0.1:5000/`

12. This app will retreive following ABM engagement metrics using [analytics finder API, MEMBER_COMPANY demographic pivot](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting?view=li-lms-2024-05&tabs=http#statistics-finder) in the past 60 days.

- costInUsd
- impressions
- clicks
- comments
- commetLikes
- follows
- likes
- opens
- reactions
- sends
- shares
- companyPageClicks
- totalEngagements
- otherEngagements
- viralOtherEngagements
- viralTotalEngagements
- externalWebsitePostViewConversions
- externalWebsitePostClickConversions
- oneClickLeads

Analytics finder API can use only 1 pivot (MEMBER_COMPANY), if developer wants to see the ABM report for individual campaigns, please use campaign filter in the API, make multiple API calls and combine all results. Pay attention to [data restrictions](https://learn.microsoft.com/en-us/linkedin/marketing/integrations/ads-reporting/ads-reporting?view=li-lms-2024-06&tabs=http#restrictions) of minimum threshold 3 events to be reported, and there is a limit of max 20 metrics to be included in one API call.

## Limitations and Further Enhancements

1. To further enhance the apps, developer may persist the access token in the apps and implement [token refresh](https://learn.microsoft.com/en-gb/linkedin/shared/authentication/authorization-code-flow?context=linkedin%2Fcontext&tabs=HTTPS1#step-5-refresh-access-token) routine before existing access token expires
2. Developer may implement the UI logic to export the results to database, CSV/Excel files, or email the report data
3. Developer may implement the UI logic to specifiy time period of report and implement a scheduler to run the apps

## Troubleshooting

1. If you get "No report data available.", ensure your Ads account has valid campaign data and relax campaign filter.
2. If developer run into api error, please clear all caches/cookies in current window or launch a new incognito window.
3. If developer find a bug, please submit new issue in github.

## MVP Screenshots

![app_login](screenshots/app_login.png)

![linkedin_oauth](screenshots/linkedin_oauth.png)

![allow_access](screenshots/allow_access.png)

![report](screenshots/report.png)

## License

Open Apache License 2.0
