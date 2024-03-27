# OLD. Probably not needed anymore, but keeping just in case

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
import zipfile
import os
import json

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Load configuration
with open('config.json') as config_file:
    config = json.load(config_file)
    destination_folder_id = config['destination_folder_id']
    camera_name = config['camera_name']
    delete_on_success = config['delete_on_success']

def zip_files(source_dir, output_file):
    """Zips the contents of the source directory into the output file."""
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, os.path.join(source_dir, '..')))

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=44121)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('drive', 'v3', credentials=creds)

    # Calculate yesterday's date and format it
    yesterday = datetime.now() - timedelta(1)
    formatted_date = yesterday.strftime('%Y-%m-%d')
    source_dir = f"/share/motioneye/{camera_name}/{formatted_date}/"  # Source directory to zip
    zip_file_path = f"/share/motioneye/{camera_name}/{formatted_date}.zip"  # Output zip file

    # Ensure source directory exists before attempting to zip
    if not os.path.exists(source_dir) or not os.listdir(source_dir):
        print(f"No files to zip in {source_dir}")
        return

    print(f"Zipping files from {source_dir} into {zip_file_path}")
    zip_files(source_dir, zip_file_path)

    # Ensure zip file exists before attempting to upload
    if not os.path.exists(zip_file_path):
        print(f"Zip file not found: {zip_file_path}, skipping upload.")
        return

    # Call the Drive v3 API to upload the file
    file_metadata = {'name': os.path.basename(zip_file_path), 'parents': [destination_folder_id]}
    media = MediaFileUpload(zip_file_path, mimetype='application/zip')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print('File ID:', file.get('id'))

    # Delete the zip file if upload was successful and delete_on_success is True
    if delete_on_success:
        os.remove(zip_file_path)
        print(f"Deleted {zip_file_path} after successful upload.")

if __name__ == '__main__':
    main()
