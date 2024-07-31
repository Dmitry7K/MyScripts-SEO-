import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

def authenticate_gsc():
    SCOPES = ['https://www.googleapis.com/auth/webmasters.readonly']
    SERVICE_ACCOUNT_FILE = os.path.join('credentials', 'Users/dmitrijkovalev/GSCmonitoring/credentials/gsc-data-427612-cd5d146298e8.json')

    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    
    service = build('searchconsole', 'v1', credentials=credentials)
    return service