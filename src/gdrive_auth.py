# gdrive_auth.py
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# The scope for Google Drive API
SCOPES = ["https://www.googleapis.com/auth/drive"]

def gdrive_authenticate():
    """
    Handles the OAuth 2.0 flow for Google Drive API.
    It prompts the user for the path to their credentials.json file,
    and generates a gdrive_token.json file.
    """
    creds = None
    token_path = "gdrive_token.json"

    # Check if a token file already exists
    if os.path.exists(token_path):
        with open(token_path, "r") as token_file:
            creds_data = json.load(token_file)
            creds = Credentials.from_authorized_user_info(creds_data, SCOPES)

            # If there are no (valid) credentials available, let the user log in.
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    # Prompt the user for the path to their credentials.json file
                    creds_path = input("Please enter the path to your credentials.json file: ")                if not os.path.exists(creds_path):
                    print("Error: The provided path to credentials.json is invalid.")
                    return
                with open(creds_path, "r") as token_file:
                    creds_data = json.load(token_file) # Initialize creds_data here
            
                flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, "w") as token_file:
                token_file.write(creds.to_json())
            print(f"Token saved to {token_path}")
    
    if __name__ == "__main__":
        gdrive_authenticate()
