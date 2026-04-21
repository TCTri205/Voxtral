import os
import secrets
import requests
from dotenv import load_dotenv

# Load explicitly to allow running this script standalone for testing
load_dotenv()

# Default URLs
DEFAULT_LOGIN_URL = "https://ai.javis-dev.vi-jp-te.info/api/v1/login/access-token"
LOGIN_URL = os.getenv("JAVIS_LOGIN_URL", DEFAULT_LOGIN_URL)

def get_javis_credentials(debug=False):
    """
    Retrieves Javis session ID and token.
    Priority:
    1. JAVIS_SESSION_ID and JAVIS_TOKEN from environment variables
    2. Dynamically fetch using JAVIS_EMAIL and JAVIS_PASSWORD
    """
    session_id = os.getenv("JAVIS_SESSION_ID")
    token = os.getenv("JAVIS_TOKEN")
    
    if session_id and token:
        if debug:
            print(f"[AUTH] Using existing session_id and token from environment.")
        return session_id, token
    
    email = os.getenv("JAVIS_EMAIL")
    password = os.getenv("JAVIS_PASSWORD")
    
    if not email or not password:
        raise ValueError(
            "Missing Javis authentication credentials. "
            "Please provide JAVIS_SESSION_ID/JAVIS_TOKEN or JAVIS_EMAIL/JAVIS_PASSWORD in .env"
        )
    
    if debug:
        print(f"[AUTH] Fetching new token for {email}...")
        
    try:
        # Note: Using json={...} automatically sets Content-Type to application/json
        response = requests.post(
            LOGIN_URL,
            json={"email": email, "password": password},
            headers={"Accept": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        # Structure as seen in config_visualizer_log_server.py
        new_token = data.get("data", {}).get("access_token")
        
        # Robustness: some APIs might return it at top level
        if not new_token:
            new_token = data.get("access_token")
            
        if not new_token:
            raise KeyError(f"Response did not contain 'access_token'. Metadata: {list(data.keys())}")
            
        new_session_id = f"voxtral-session-{secrets.token_hex(6)}"
        
        if debug:
            print(f"[AUTH] Successfully retrieved new token. Generated session_id: {new_session_id}")
            
        return new_session_id, new_token
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to authenticate with Javis API: {e}")

if __name__ == "__main__":
    # Test script
    try:
        sid, tk = get_javis_credentials(debug=True)
        print(f"Session ID: {sid}")
        print(f"Token: {tk[:20]}...")
    except Exception as e:
        print(f"Error: {e}")
