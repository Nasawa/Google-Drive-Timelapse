from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta
from PIL import Image
import os
import sys
import shutil
import json
import cv2
import glob
import argparse
import time
from moviepy.editor import ImageSequenceClip
import logging

# Configure logging
script_dir = os.path.dirname(os.path.realpath(__file__))
logging.basicConfig(filename=os.path.join(script_dir, 'timelapse.log'), level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

# Create a StreamHandler for console output
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)  # Set this to your preferred level
console_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s:%(message)s'))

# Add the console handler to the root logger
logging.getLogger().addHandler(console_handler)

# Construct paths relative to the script's directory
config_path = os.path.join(script_dir, 'config.json')
credentials_path = os.path.join(script_dir, 'credentials.json')
token_path = os.path.join(script_dir, 'token.json')

parser = argparse.ArgumentParser(description='Copy files from a mapped drive for timelapse creation.')
parser.add_argument('--ago', type=int, default=1, help='Number of days ago to retrieve images for.')

# Parse arguments
args = parser.parse_args()

def authenticate_google_drive(token_path, credentials_path, scopes):
    """
    Authenticates the user with Google Drive and returns a service object.

    :param token_path: Path to the token file.
    :param credentials_path: Path to the credentials file.
    :param scopes: Scopes required for the Google Drive service.
    :return: Authenticated Google Drive service object.
    """
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token_file:
            token_file.write(creds.to_json())
    
    service = build('drive', 'v3', credentials=creds)
    return service

def upload_to_google_drive(service, file_path, destination_folder_id):
    """
    Uploads a file to Google Drive.

    :param service: Authenticated Google Drive service object.
    :param file_path: Path to the file to upload.
    :param destination_folder_id: ID of the Google Drive folder to upload the file to.
    """
    if not os.path.exists(file_path):
        logging.error(f"File not found: {file_path}, skipping upload.")
        return

    file_metadata = {'name': os.path.basename(file_path), 'parents': [destination_folder_id]}
    media = MediaFileUpload(file_path, mimetype='video/mp4')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    logging.info(f'File ID: {file.get("id")}')

def is_gray_image(image_path, gray_threshold=0.05):
    image = cv2.imread(image_path)
    height, width = image.shape[:2]
    roi_start_width = width // 2
    roi_end_width = width
    roi_start_height = 0
    roi_end_height = height // 2
    roi = image[roi_start_height:roi_end_height, roi_start_width:roi_end_width]
    gray_roi = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    stddev = cv2.meanStdDev(gray_roi)[1][0][0]
    if stddev < gray_threshold:
        logging.warning(f"Deviation {stddev} below threshold {gray_threshold} for image {image_path}. Image skipped.")
    return stddev < gray_threshold

def create_timelapse_with_opencv(image_folder, output_path, fps=30):
    logging.info(f"Looking in {image_folder} for images...")
    images = sorted(glob.glob(os.path.join(image_folder, '*.jpg')), key=os.path.getmtime)
    if not images:
        logging.warning("No images found in the directory.")
        return

    valid_images = [img for img in images if not is_gray_image(img)]

    if not valid_images:
        logging.warning("No valid (non-gray) images found in the directory.")
        return
    
    logging.info(f"{len(valid_images)} of {len(images)} are valid.")

    frame = cv2.imread(valid_images[len(valid_images) - 1])
    height, width, layers = frame.shape
    size = (width, height)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, size)

    for image_path in valid_images:
        # logging.info(f"Using image: {image_path}")
        frame = cv2.imread(image_path)
        out.write(frame)

    out.release()
    logging.info(f"Timelapse video created at {output_path}")

def delete_files_and_directory(image_folder_path, video_folder_path, max_attempts=5, wait_seconds=3):
    """
    Deletes all files in the specified image and video folders, then deletes the folders themselves.

    :param image_folder_path: Path to the directory containing the image files.
    :param video_folder_path: Path to the directory containing the video files.
    :param max_attempts: Maximum number of attempts to delete the files and folders.
    :param wait_seconds: Number of seconds to wait between deletion attempts.
    """
    # Function to delete all files in a folder with retry logic
    def delete_files_in_folder(folder_path, file_type):
        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)
            for attempt in range(max_attempts):
                try:
                    os.remove(file_path)
                    # logging.info(f"Deleted {file_type} file: {file_path}")
                    break  # Exit the loop if deletion is successful
                except PermissionError as e:
                    logging.warning(f"Attempt {attempt + 1} to delete {file_path} failed: {e}")
                    if attempt < max_attempts - 1:  # Wait before retrying unless it's the last attempt
                        time.sleep(wait_seconds)
            else:
                logging.error(f"Failed to delete {file_path} after {max_attempts} attempts.")
    
    # Delete all files in the image folder with retry logic
    if os.path.exists(image_folder_path):
        delete_files_in_folder(image_folder_path, 'image')
    
    # Delete all files in the video folder with retry logic
    if os.path.exists(video_folder_path):
        delete_files_in_folder(video_folder_path, 'video')
    
    # Function to delete a folder
    def delete_folder(folder_path):
        try:
            os.rmdir(folder_path)
            logging.info(f"Deleted folder: {folder_path}")
        except Exception as e:
            logging.error(f"Failed to delete folder {folder_path}: {e}")
    
    # Delete the image folder
    delete_folder(image_folder_path)
    
    # Delete the video folder
    delete_folder(video_folder_path)


def get_date_ago(ago=1):
    """
    Returns a string representing the date a specified number of days ago.

    :param ago: Number of days ago to calculate the date for.
    :return: String representing the date in 'YYYY-MM-DD' format.
    """
    target_date = datetime.now() - timedelta(days=ago)
    return target_date.strftime('%Y-%m-%d')

def copy_files_from_mapped_drive(mapped_drive_letter, mapped_drive_path, camera_name, destination_folder_path, formatted_date):
    """
    Copies files from a mapped network drive to a local directory.

    :param mapped_drive_letter: The letter assigned to the mapped network drive (e.g., 'Z').
    :param camera_name: The name of the camera directory to find the images.
    :param destination_folder_path: The path to the local directory where files will be copied.
    """
    # Ensure the destination folder exists
    if not os.path.exists(destination_folder_path):
        os.makedirs(destination_folder_path)
        logging.info(f"Created destination folder: {destination_folder_path}")

    source_path = os.path.join(f"{mapped_drive_letter}", mapped_drive_path, camera_name, formatted_date)

    # Log the operation
    logging.info(f"Copying files from mapped drive {source_path} to {destination_folder_path}")

    # Check if the source directory exists to avoid errors
    if os.path.exists(source_path):
        for filename in os.listdir(source_path):
            # Adjust the condition below as needed (e.g., file type filter)
            if filename.endswith(".jpg"):  # Example: Copy only JPEG images
                source_file = os.path.join(source_path, filename)
                destination_file = os.path.join(destination_folder_path, filename)
                shutil.copy2(source_file, destination_file)  # copy2 preserves metadata like timestamps
        logging.info(f"Successfully copied images for timelapse creation.")
    else:
        logging.error(f"Source directory does not exist: {source_path}")

def main_workflow(token_path, credentials_path, config, args):
    """
    The main workflow of the script.

    :param token_path: Path to the token file.
    :param credentials_path: Path to the credentials file.
    :param skip_upload: Boolean indicating whether to skip uploading to Google Drive.
    :param delete_on_success: Boolean indicating whether to delete files after successful upload.
    :param destination_folder_id: ID of the Google Drive folder to upload the file to.
    :param mapped_drive_letter: The letter assigned to the mapped network drive (e.g., 'Z').
    :param camera_name: The name of the camera directory to find the images.
    :param args: Command-line arguments.
    """
    service = authenticate_google_drive(token_path, credentials_path, SCOPES)

    formatted_date = get_date_ago(args.ago)
    local_image_folder_path = os.path.join(script_dir, f"{config['camera_name']}_temp_images")
    output_video_dir = os.path.join(script_dir, f"{config['camera_name']}_timelapse")
    output_video_path = os.path.join(output_video_dir, f"{formatted_date}_timelapse.mp4")

    # Ensure local image folder is created
    if not os.path.exists(local_image_folder_path):
        os.makedirs(local_image_folder_path)

    # Ensure local output video folder is created
    if not os.path.exists(output_video_dir):
        os.makedirs(output_video_dir)

    # Adjusted to use config dictionary
    copy_files_from_mapped_drive(
        config['mapped_drive_letter'], 
        config['mapped_drive_path'], 
        config['camera_name'], 
        local_image_folder_path, 
        formatted_date)

    create_timelapse_with_opencv(local_image_folder_path, output_video_path, fps=30)

    # More adjustments as necessary
    if not config['skip_upload']:
        upload_to_google_drive(service, output_video_path, config['destination_folder_id'])

    if config['delete_on_success']:
        delete_files_and_directory(local_image_folder_path, output_video_dir)

def main():
    #Load Configuration List
    with open(config_path) as config_file:
        configs = json.load(config_file)
    
    for config in configs:
        main_workflow(
            token_path=token_path,
            credentials_path=credentials_path,
            config=config,
            args=args
        )

if __name__ == '__main__':
    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    try:
        main()
    except Exception as e:
        logging.error("An error occurred during script execution.", exc_info=True)
