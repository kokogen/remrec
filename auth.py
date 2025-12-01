# auth.py
import secrets
import hashlib
import base64
import webbrowser
import urllib.parse
import requests
from config import settings

TOKEN_STORAGE_FILE = ".dropbox.token"

def generate_pkce_challange():
    """Generates a code verifier and a code challenge for PKCE."""
    code_verifier = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(hashed).decode('utf-8').replace('=', '')
    return code_verifier, code_challenge

def get_refresh_token(app_key: str):
    """
    Guides the user through the Dropbox OAuth2 PKCE flow to get a refresh token.
    The token is saved to a file.
    """
    code_verifier, code_challenge = generate_pkce_challange()

    auth_params = {
        'client_id': app_key,
        'response_type': 'code',
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
        'token_access_type': 'offline',
    }
    auth_url = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode(auth_params)

    print("--- Dropbox Authorization ---")
    print("\n1. A browser window will open. Please authorize the application.")
    print("\n2. After authorization, you will be redirected to a blank page.")
    print("   Copy the FULL URL from your browser's address bar.\n")
    
    webbrowser.open(auth_url)

    redirect_url_str = input("3. Paste the full redirect URL here and press Enter:\n")

    try:
        # Instead of running a server, we parse the code from the URL the user pastes.
        parsed_url = urllib.parse.urlparse(redirect_url_str)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        auth_code = query_params.get('code', [None])[0]

        if not auth_code:
            print("\nError: Could not find 'code' in the provided URL.")
            return

        # --- Exchange authorization code for a refresh token ---
        token_params = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'client_id': app_key,
            'code_verifier': code_verifier,
        }
        
        response = requests.post("https://api.dropboxapi.com/oauth2/token", data=token_params)
        response.raise_for_status() # Raise an exception for bad status codes

        token_data = response.json()
        refresh_token = token_data.get('refresh_token')

        if refresh_token:
            # Save the token to the file
            with open(TOKEN_STORAGE_FILE, "w") as f:
                f.write(refresh_token)
            print(f"\n✅ Success! Refresh token has been saved to '{TOKEN_STORAGE_FILE}'.")
            print("You can now run the main application.")
        else:
            print("\n❌ Error: Did not receive a refresh token from Dropbox.")
            print("Response:", token_data)

    except requests.exceptions.RequestException as e:
        print(f"\n❌ An error occurred during the token exchange: {e}")
        print("Response body:", e.response.text if e.response else "N/A")
    except (KeyError, IndexError):
        print("\n❌ Error: The pasted URL does not seem to be a valid Dropbox redirect.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == '__main__':
    # We can run this script directly to perform authorization
    app_key = settings.DROPBOX_APP_KEY
    if not app_key or "YOUR_APP_KEY" in app_key:
        print("Error: `DROPBOX_APP_KEY` is not configured in your .env file.")
        print("Please copy .env.example to .env and fill in your Dropbox App Key.")
    else:
        get_refresh_token(app_key)
