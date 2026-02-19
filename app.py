# app.py
from dotenv import load_dotenv
import os

load_dotenv()

from flask import Flask
from flask_session import Session
from config import Config
# Register blueprints
from routes.main import main_bp
from routes.gallery import gallery_bp
from routes.upload import upload_bp
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.config.from_object("config.Config")

# Ensure session directory exists
if not os.path.exists(".flask_sessions"):
    os.makedirs(".flask_sessions")

# Initialize server-side session
Session(app)


app.register_blueprint(main_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(upload_bp)

if __name__ == "__main__":
    app.run(debug=True)
