import json
import os
import sys
from datetime import datetime, timedelta
from upstash_redis import Redis

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Fetch credentials from environment variables
UPSTASH_REDIS_REST_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
SUBSCRIPTION_KEY = os.getenv("SUBSCRIPTION_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize Redis client
redis_client = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)



# Dynamically check and install dependencies
try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
except ImportError:
    print("Installing required libraries...")
    os.system(f"{sys.executable} -m pip install google-auth google-auth-oauthlib google-api-python-client")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials

# --- Constants ---
SCOPES = ['https://www.googleapis.com/auth/calendar']
DEFAULT_DURATION_MINUTES = 60  # Default meeting duration is set to 1 hour

# Get credentials file from environment
CREDENTIALS_FILE = os.getenv("GCP_CREDENTIALS_JSON")

if not CREDENTIALS_FILE:
    print("⚠️ Environment variable 'GCP_CREDENTIALS_JSON' not found.")
    sys.exit()

def authenticate_user():
    """
    Authenticate the user via OAuth2 and return a Google Calendar API service object.
    Saves token for future runs.
    """
    creds = None
    # Check for existing token
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    # If no token is available, prompt for login
    if not creds or not creds.valid:
        if not os.path.exists(CREDENTIALS_FILE):
            print(f"Error: '{CREDENTIALS_FILE}' file not found. Please provide OAuth credentials.")
            sys.exit()

        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token for future runs
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())

    # Build the Calendar API service correctly
    service = build("calendar", "v3", credentials=creds)
    return service

def create_meeting(service, summary, description, start_time, time_zone):
    print(f"Start Time Received: {start_time}")
    if not start_time:
        print("No valid start_time provided. Skipping meeting creation.")
        return

    if isinstance(start_time, str):
        try:
            start_time = datetime.fromisoformat(start_time)
        except ValueError:
            print("Invalid start_time format. Unable to parse.")
            return

    end_time = start_time + timedelta(minutes=DEFAULT_DURATION_MINUTES)
    print(f"End Time Calculated: {end_time}")
    # Prepare the event details
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': time_zone,
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': time_zone,
        },
        'reminders': {
            'useDefault': True,
        },
    }

    try:
        # Create the event using the Google Calendar API
        event_result = service.events().insert(
            calendarId='primary', body=event).execute()
        redis_client.set("meeting_link", event_result['htmlLink'])
        print(f"✅ Meeting has been successfully scheduled!\nEvent details: {event_result['htmlLink']}")
    except Exception as e:
        print(f"Error creating event: {e}")

def get_valid_datetime_input(prompt):
    """Prompt user for a valid date-time input and return a datetime object."""
    while True:
        try:
            date_input = input(prompt)
            return datetime.strptime(date_input, "%Y-%m-%d %H:%M")
        except ValueError:
            print("\u26A0\uFE0F Invalid format. Please use 'YYYY-MM-DD HH:MM'.")

def main():
    print("\n🔹 Welcome to the Automated Meeting Scheduler 🔹\n")
    print("Note: You will be asked to log in with your Google account.\n")
    service = authenticate_user()

if __name__ == "__main__":
    main()


