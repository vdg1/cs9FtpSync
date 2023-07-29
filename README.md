# CS9FTPSync - SRS-Stäubli Robot Controller Synchronization

![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Overview

CS9FTPSync is a Python-based daemon-like program designed to simplify the synchronization of the `usrapp` folder between Stäubli Robotics Studio (SRS) projects and Stäubli robot controllers. The synchronization process is achieved using the `pyftpsync` library, ensuring secure file transfers between the two systems.

The primary aim of this project is to automate the process of keeping the `usrapp` folder up-to-date, facilitating the seamless integration between SRS projects and Stäubli robot controllers.

## Features

- Automatic synchronization of the `usrapp` folder between Stäubli Robotics Studio (SRS) and Stäubli robot controllers.
- Utilizes the `pyftpsync` library for secure FTP transfers, ensuring data integrity.
- Configuration file (`ftpsync.ini`) for easy setup and management.
- Customizable settings for synchronization intervals and connection parameters.
- Detailed logging system for monitoring synchronization activities.

## Requirements

- Python 3.8 or higher
- `pyftpsync` library (will be automatically installed via setup script)

## Installation

1. Clone this GitHub repository:
```bash
git clone https://github.com/vdg1/cs9ftpsync.git
```

2. Change into the project directory:
```bash
cd cs9ftpsync
```

3. (Optional) Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate # On Windows: venv\Scripts\activate
```

4. Install the required dependencies:
```bash
pip install -r requirements.txt
```
## Configuration

Before running the synchronization program, ensure that you have the necessary configuration set up:

1. Open the `ftpsync.ini` file and modify the following settings as needed:

```ini
[ftpsync]
enabled=true
username=maintenance
password=spec_cal
include=io*, a*
```

enabled: Set to true to enable synchronization.
username: The username for FTP authentication.
password: The password for FTP authentication.
include: A comma-separated list of file patterns to include in the synchronization.

Save the changes.

## Usage
Once the configuration is set, you can run the synchronization daemon using the following command:

```bash
python sync_daemon.py
```
The program will start synchronizing the usrapp folder between the Stäubli Robotics Studio (SRS) project and the Stäubli robot controller at the specified interval. You can keep the program running in the background, and it will handle the synchronization automatically.

## License
This project is licensed under the MIT License.

## Acknowledgments
The CS9FTPSync project was inspired by the need for seamless integration between Stäubli Robotics Studio (SRS) projects and Stäubli robot controllers. Special thanks to the developers of pyftpsync for providing a robust FTP synchronization library.

Happy syncing! If you have any questions or need assistance, feel free to contact us or create an issue in this repository. We appreciate your interest in CS9FTPSync.
