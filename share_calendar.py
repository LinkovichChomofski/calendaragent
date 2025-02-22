from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Calendar and service account configuration
CALENDAR_ID = 'a3caeb237bc1daa251da479d61071aad8f99c636a8b232b1501c940ec774f7ca@group.calendar.google.com'
SERVICE_ACCOUNT_FILE = '/Users/jordanwoods/Desktop/2024 Projects/CalendarAgent/calendaragent-451205-5134e64efa59.json'
CLIENT_SECRETS_FILE = 'client_secrets.json'  # You'll need to download this from Google Cloud Console
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_service_account_email():
    """Get the service account email from the credentials file"""
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        creds = json.load(f)
    return creds['client_email']

def main():
    try:
        if not os.path.exists(CLIENT_SECRETS_FILE):
            print(f"Error: {CLIENT_SECRETS_FILE} not found.")
            print("Please download the OAuth client configuration file from Google Cloud Console:")
            print("1. Go to https://console.cloud.google.com/apis/credentials")
            print("2. Select your project")
            print("3. Click 'Create Credentials' > 'OAuth client ID'")
            print("4. Choose 'Desktop app'")
            print("5. Download the client configuration file")
            print("6. Save it as 'client_secrets.json' in the project directory")
            return

        # Start OAuth2 flow
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        
        # Build the service with OAuth2 credentials
        service = build('calendar', 'v3', credentials=creds)
        
        # Get service account email
        service_account_email = get_service_account_email()
        print(f"Service account email: {service_account_email}")
        
        # Share calendar with service account
        rule = {
            'scope': {
                'type': 'user',
                'value': service_account_email,
            },
            'role': 'writer'
        }
        
        # Insert the calendar permission
        result = service.acl().insert(calendarId=CALENDAR_ID, body=rule).execute()
        print(f"Successfully shared calendar with service account")
        print(f"Rule details: {json.dumps(result, indent=2)}")
        
        # Verify calendar exists
        calendar = service.calendars().get(calendarId=CALENDAR_ID).execute()
        print(f"Successfully verified calendar: {calendar['summary']}")
        
        # List all calendar permissions
        acl = service.acl().list(calendarId=CALENDAR_ID).execute()
        print("\nCurrent calendar permissions:")
        for rule in acl.get('items', []):
            print(f"- {rule['scope']['value']}: {rule['role']}")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    main()