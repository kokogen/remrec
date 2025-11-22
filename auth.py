from http.server import BaseHTTPRequestHandler, HTTPServer
import webbrowser
import requests
import threading
import urllib

class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if '/oauth_callback' in self.path:
            # Simplified parsing of the 'code' parameter from the URL
            import urllib.parse as urlparse
            query = urlparse.urlparse(self.path).query
            params = urlparse.parse_qs(query)
            code = params.get('code', [None])[0]
            self.server.auth_code = code  # Store it in the server instance
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorization code received. You can close this window.")
        else:
            self.send_response(404)
            self.end_headers()

def run_server_in_thread(port=8080):
    server = HTTPServer(('localhost', port), OAuthHandler)
    server.auth_code = None

    def server_thread():
        server.handle_request()  # Handle one request and exit

    t = threading.Thread(target=server_thread)
    t.start()
    return server, t

def exchange_code_for_token(client_id, client_secret, code, redirect_uri):
    url = "https://api.dropbox.com/oauth2/token"
    data = {
        'code': code,
        'grant_type': 'authorization_code',
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri,
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token_data = response.json()
        print("Access Token:", token_data.get('access_token'))
        print("Refresh Token:", token_data.get('refresh_token'))
        print("Expires in (seconds):", token_data.get('expires_in'))
        return token_data
    else:
        print("Error getting tokens:", response.status_code, response.text)
        return None

import os
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    client_id = os.getenv('DROPBOX_APP_KEY')
    client_secret = os.getenv('DROPBOX_APP_SECRET')
    redirect_uri = 'http://localhost:8080/oauth_callback'

    if not client_id or not client_secret:
        raise ValueError("DROPBOX_APP_KEY and DROPBOX_APP_SECRET must be set in .env file")

    params = {
        "client_id": client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "token_access_type": "offline",
    }

    auth_url = "https://www.dropbox.com/oauth2/authorize?" + urllib.parse.urlencode(params)
    print(auth_url)

    server, thread = run_server_in_thread()
    print("Server started, waiting for request...")

    webbrowser.open(auth_url)

    thread.join(timeout=160)
    if server.auth_code:
        code = server.auth_code
        print("Code received:", server.auth_code)
    else:
        print("Code was not received.")

    if code: 
        token_data = exchange_code_for_token(client_id, client_secret, code, redirect_uri)

        if token_data:
            print("\nSave the following data for use in your scripts:")
            print("Access Token:", token_data['access_token'])
            print("Refresh Token:", token_data['refresh_token'])
