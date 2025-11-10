# app.py
from flask import Flask
from dotenv import load_dotenv
import os
# Register blueprints
from routes.main import main_bp
from routes.gallery import gallery_bp
from routes.upload import upload_bp

load_dotenv()
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")



app.register_blueprint(main_bp)
app.register_blueprint(gallery_bp)
app.register_blueprint(upload_bp)

if __name__ == "__main__":
    app.run(debug=True)
