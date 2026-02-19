# app.py — Application factory entry point
import os
import logging
from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from flask_session import Session
from authlib.integrations.flask_client import OAuth
from config import Config

os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Global OAuth registry (Authlib)
oauth = OAuth()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ── Server-side sessions ──────────────────────────────────────────────
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    Session(app)

    # ── Authlib OAuth registry ────────────────────────────────────────────
    oauth.init_app(app)

    # Register Wikimedia as an OAuth 2.0 client
    oauth.register(
        name="wikimedia",
        client_id=app.config["WIKI_CLIENT_ID"],
        client_secret=app.config["WIKI_CLIENT_SECRET"],
        authorize_url=app.config["WIKI_AUTHORIZE_URL"],
        access_token_url=app.config["WIKI_TOKEN_URL"],
        client_kwargs={"scope": app.config["WIKI_SCOPES"]},
        # Wikimedia uses a non-standard token endpoint auth method
        token_endpoint_auth_method="client_secret_post",
    )

    # ── Blueprints ────────────────────────────────────────────────────────
    from routes.main import main_bp
    from routes.gallery import gallery_bp
    from routes.upload import upload_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(upload_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
