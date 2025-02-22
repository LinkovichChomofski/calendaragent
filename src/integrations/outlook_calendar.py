import os
from msal import ConfidentialClientApplication
from datetime import datetime, timedelta

class OutlookCalendarClient:
    def __init__(self):
        self.client_id = os.getenv('OUTLOOK_CLIENT_ID')
        self.client_secret = os.getenv('OUTLOOK_CLIENT_SECRET')
        self.authority = "https://login.microsoftonline.com/common"
        self.scopes = ["Calendars.ReadWrite"]
        
        self.app = ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
    def get_access_token(self):
        result = self.app.acquire_token_silent(self.scopes, account=None)
        if not result:
            result = self.app.acquire_token_for_client(scopes=self.scopes)
        return result.get('access_token')
