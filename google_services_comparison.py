import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow # Changed from InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

CLIENT_SECRET_FILE = 'c:/Users/KEERTHANA/OneDrive/Desktop/wikimedia-uploader/client_secret.json'

def authenticate(scopes, token_pickle_file):
    """
    Handles the OAuth 2.0 flow for a given set of scopes and token file.
    Returns an authenticated service credential.
    """
    creds = None
    if os.path.exists(token_pickle_file):
        with open(token_pickle_file, 'rb') as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Use the web application flow, which matches your client_secret.json
            # The redirect_uri must match one of the URIs in your client_secret.json
            flow = Flow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                scopes=scopes,
                redirect_uri='http://localhost:5000/oauth2callback'
            )
            creds = flow.run_local_server(port=5000) # Use the port from the redirect URI
        
        with open(token_pickle_file, 'wb') as token:
            pickle.dump(creds, token)
    return creds

def get_images_from_drive():
    """Connects to Google Drive and lists the first 5 image files."""
    print("\n--- Attempting to get images from Google Drive ---")
    
    # 1. Define Drive-specific scopes and token file
    scopes = ['https://www.googleapis.com/auth/drive.readonly']
    token_file = 'token_drive.pickle'
    
    try:
        creds = authenticate(scopes, token_file)
        
        # 2. Build the Google Drive service object
        service = build('drive', 'v3', credentials=creds)

        # 3. Call the Drive API to search for files with an image mimeType
        print("Searching for image files in Google Drive...")
        results = service.files().list(
            q="mimeType contains 'image/'",
            pageSize=5,
            fields="nextPageToken, files(id, name, webViewLink)"
        ).execute()
        
        items = results.get('files', [])

        if not items:
            print("No image files found in Google Drive.")
        else:
            print("Found images in Google Drive:")
            for item in items:
                print(f"- {item['name']} (ID: {item['id']})")
                print(f"  Link: {item['webViewLink']}")

    except HttpError as error:
        print(f"An error occurred with Google Drive API: {error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def get_photos_from_google_photos():
    """Connects to Google Photos and lists the first 5 media items."""
    print("\n--- Attempting to get photos from Google Photos ---")
    
    # 1. Define Photos-specific scopes and token file
    scopes = ['https://www.googleapis.com/auth/photoslibrary.readonly']
    token_file = 'token_photos.pickle'

    try:
        creds = authenticate(scopes, token_file)
        
        # 2. Build the Google Photos Library service object (note the different service name)
        service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

        # 3. Call the Photos API to list media items
        print("Fetching media items from Google Photos library...")
        results = service.mediaItems().list(pageSize=5).execute()
        
        items = results.get('mediaItems', [])

        if not items:
            print("No media items found in Google Photos.")
        else:
            print("Found media in Google Photos:")
            for item in items:
                print(f"- {item['filename']} (ID: {item['id']})")
                # baseUrl is the direct link to the media bytes, valid for 60 mins
                print(f"  Base URL: {item['baseUrl']}")

    except HttpError as error:
        print(f"An error occurred with Google Photos API: {error}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == '__main__':
    # Run both functions to see the difference
    get_images_from_drive()
    get_photos_from_google_photos()