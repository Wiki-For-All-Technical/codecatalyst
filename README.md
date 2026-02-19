G2COMMONS

Upload Images from Google Drive / Google Photos to Wikimedia Commons

G2COMMONS is a web-based tool that allows users to easily transfer images from their Google Drive or Google Photos directly to Wikimedia Commons. The application simplifies the upload workflow by integrating Google OAuth authentication and providing a user-friendly interface for selecting and submitting images.

🚀 FEATURES

🔐 Secure Google OAuth authentication
📂 Access images from Google Drive
🖼️ Access images from Google Photos
⬆️ Direct upload to Wikimedia Commons
🖥️ Simple and clean web interface
⚡ Fast and efficient transfer process
🌐 Built using lightweight web technologies

🛠️ TECH STACK

FRONTEND:
1. HTML
2. CSS

BACKEND:
1. Python
2. Flask

APIs & SERVICES

1. Google Drive API
2. Google Photos API
3. Wikimedia Commons API
4. Google OAuth 2.0

📋 PREREQUISITES

1. Before running the project, ensure you have:

2. Python 3.x installed

3. Google Cloud Project with OAuth credentials

4. Enabled Google Drive API and Google Photos API

5. Wikimedia Commons account

6. Internet connection

⚙️ INSTALLATION

1. Clone the repository

git clone https://github.com/your-username/G2COMMONS.git
cd G2COMMONS


2. Create a virtual environment (recommended)

python -m venv venv


3. Activate it:

Windows:

venv\Scripts\activate


Linux / Mac:

source venv/bin/activate


4. Install dependencies

pip install -r requirements.txt

🔑 GOOGLE OAUTH SETUP

1. Go to Google Cloud Console

2. Create a new project

3. Enable:

Google Drive API

Google Photos Library API

4. Create OAuth 2.0 credentials

5. Download the credentials file

6. Place it in the project directory

▶️ RUNNING THE APPLICATION
python app.py


Then open your browser and go to:

http://localhost:5000

📂 PROJECT STRUCTURE
G2COMMONS/
│
├── static/            # CSS and assets
├── templates/         # HTML files
├── app.py             # Main Flask application
├── requirements.txt   # Python dependencies
├── credentials.json   # Google OAuth credentials
└── README.md

🧠 HOW IT WORKS

User logs in using Google account

Application retrieves images from Drive or Photos

User selects images to upload

Images are transferred to Wikimedia Commons

Upload status is displayed

🔒 SECURITY NOTES

OAuth authentication ensures secure access

No passwords are stored

User data is processed only for upload functionality

📌 USECASES

Contributors uploading media to Wikimedia Commons

Researchers sharing datasets

Educational content creators

Digital archivists

🤝 CONTRIBUTING

Contributions are welcome!

Fork the repository

Create a new branch

Commit your changes

Open a Pull Request

📄 LICENSE

This project is intended for educational and research purposes.
Add an appropriate open-source license if distributing publicly.

👩‍💻 AUTHOR

Developed as part of a project to simplify media transfer to Wikimedia Commons.
