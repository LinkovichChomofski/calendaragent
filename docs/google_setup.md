## Google Cloud Configuration Guide

1. **Project Creation**  
   [Create new project](https://console.cloud.google.com/projectcreate)  
   Name: `CalendarAgent-Prod`

2. **Calendar API Enablement**  
   Navigation Menu → APIs & Services → Library → Search "Calendar API" → Enable

3. **Service Account Setup**  
   - APIs & Services → Credentials → Create Credentials → Service Account  
   - Name: `calendar-agent-integration`  
   - Role: `Calendar API User`  
   - Keys → JSON → Download

4. **Environment Configuration**  
   Paste downloaded JSON into `.env`:  
   ```env
   GOOGLE_SERVICE_ACCOUNT='{...}'  # Full service account JSON
   ```

5. **Domain Verification**  
   APIs & Services → OAuth consent screen → Configure domain

# Google Calendar Integration Setup

## Prerequisites
- Google Cloud Account
- Python 3.10+
- Virtual Environment

## 1. Google Cloud Project Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google Calendar API
   - Navigate to APIs & Services > Library
   - Search for "Google Calendar API"
   - Click Enable

## 2. Authentication Setup
You can use either OAuth 2.0 (for user accounts) or Service Account (for automated access).

### OAuth 2.0 Setup (User Authentication)
1. Configure OAuth Consent Screen
   - Go to APIs & Services > OAuth consent screen
   - Choose "External" user type
   - Fill in application name, support email, and developer contact
   - Add scope: `https://www.googleapis.com/auth/calendar`
   - Add your email as a test user

2. Create OAuth Client ID
   - Go to APIs & Services > Credentials
   - Create Credentials > OAuth Client ID
   - Choose "Desktop Application"
   - Add authorized redirect URIs:
     ```
     http://localhost:8080
     http://localhost:8080/
     http://127.0.0.1:8080
     http://127.0.0.1:8080/
     ```
   - Download client credentials

3. Configure Environment Variables
   ```bash
   # Add to .env file
   GOOGLE_CLIENT_ID=your_client_id_here
   GOOGLE_CLIENT_SECRET=your_client_secret_here
   ```

### Service Account Setup (Server-to-Server)
1. Create Service Account
   - Go to APIs & Services > Credentials
   - Create Credentials > Service Account
   - Fill in service account details
   - Create and download private key (JSON)

2. Configure Environment Variables
   ```bash
   # Add to .env file
   GOOGLE_SERVICE_ACCOUNT='{"type": "service_account", ...}'  # Entire JSON content
   ```

3. Share Calendar Access
   - Go to calendar.google.com
   - Share calendar with service account email
   - Grant appropriate permissions

## 3. Testing the Integration
```bash
# Activate virtual environment
source venv/bin/activate

# Test authentication
python -c "
from src.integrations.google_calendar import GoogleCalendarClient
from dotenv import load_dotenv
load_dotenv()

client = GoogleCalendarClient()
calendars = client.get_calendar_list()
print('Available Calendars:')
for cal in calendars.get('items', []):
    print(f\"- {cal.get('summary')}\")
"
```

## Note for Development
- The application is in testing mode
- Only approved test users can access the application
- Up to 100 test users are supported
- Production deployment will require Google verification
