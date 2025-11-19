# app.py
from flask import Flask
from flask_session import Session
from dotenv import load_dotenv
import os
# Register blueprints
from routes.main import main_bp
from routes.gallery import gallery_bp
from routes.upload import upload_bp
from config import Config

load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.config.from_object("config.Config")

# Initialize server-side session
Session(app)


app.register_blueprint(main_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(upload_bp)

if __name__ == "__main__":
    app.run(debug=True)
