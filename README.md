# Timelapse Video Generator and Uploader

This Python script automates the process of creating timelapse videos from a collection of images stored on a mapped network drive, with the optional feature of uploading the resulting video to Google Drive. It is ideal for projects like construction monitoring, nature observation, or any other scenario where you want to convert a series of images into a timelapse video.

## Features

- **Automated Timelapse Creation:** Generates a video from a series of images.
- **Google Drive Integration:** Optionally uploads the generated timelapse video to Google Drive.
- **Flexible Configuration:** Utilizes a JSON configuration file for managing settings such as image source, Google Drive upload details, and more.
- **Logging:** Provides detailed logging to both a file and the console for troubleshooting.

## Prerequisites

Before you begin, ensure you have:

- Python 3.6 or higher.
- Google Drive API credentials saved in a file named `credentials.json` within the project directory (for uploading to Google Drive).
- Required Python libraries as listed in `requirements.txt`. Install them using the command below:

## Installation

1. Clone this repository or download the source code to your local machine.
2. Install the necessary Python packages:

    ```
    pip install -r requirements.txt
    ```

3. Obtain Google Drive API credentials and save them as `credentials.json` in the project directory. Follow the [Google Drive API documentation](https://developers.google.com/drive/api/v3/quickstart/python) for guidance on generating these credentials.

## Configuration

Customize `config.json` with your specific parameters, like the camera name, mapped drive details, and the Google Drive folder ID for uploads. Example configuration:

```
[
    {
        "camera_name": "Camera1",
        "mapped_drive_letter": "Z",
        "mapped_drive_path": "/path/to/images",
        "destination_folder_id": "your_google_drive_folder_id_here",
        "skip_upload": false,
        "delete_on_success": true
    }
]
```

## Usage

To run the script from the command line:

```
python timelapse.py
```

By default, the script retrieves images from the previous day to create the timelapse. You can specify a different number of days ago by using the `--ago` parameter. For example, `--ago 2` retrieves images from two days ago.

## Google Drive Upload

To activate uploading to Google Drive, set `skip_upload` to `false` in `config.json`. Ensure you have `credentials.json` for your Google API credentials and `token.json` for an active token in your project directory.

## Contributing

We welcome contributions! Feel free to submit pull requests, report bugs, or suggest new features.

## License

This project is licensed under the MIT License. See the LICENSE file for more details.
