# 📸 G2Commons

> Upload images from **Google Drive** or **Google Photos** directly to **Wikimedia Commons** — free, open-source, and built for the Wikimedia community.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey)](https://flask.palletsprojects.com)
[![Wikimedia Cloud Services](https://img.shields.io/badge/Hosted%20on-Wikimedia%20Cloud-green)](https://wikitech.wikimedia.org)

---

## 🌟 Features

| Feature | Details |
|--------|---------|
| 🔐 **Google OAuth 2.0** | Secure sign-in — passwords never stored |
| 🌐 **Wikimedia OAuth 2.0** | Authorise uploads via official Authlib flow |
| �️ **Google Photos** | Browse and select from your personal photo library |
| � **Google Drive** | Pick image files directly from your Drive |
| � **Batch Uploads** | Select multiple images and upload them all at once |
| 🏷️ **Rich Metadata** | Set title, description, and Wikimedia categories per image |
| 🌙 **Dark / Light Mode** | Persistent theme toggle with no flash on reload |
| 📋 **Privacy & ToS** | Built-in Privacy Policy and Terms of Use pages |
| 📱 **Responsive UI** | Works on desktop, tablet, and mobile |

---

## 🛠️ Tech Stack

**Backend**
- Python 3.14 · Flask 3
- [Authlib](https://docs.authlib.org) — OAuth 2.0 for both Google and Wikimedia
- Flask-Session — server-side session management
- Google APIs: Drive API, Photos Library API
- MediaWiki REST API — Wikimedia Commons uploads

**Frontend**
- Vanilla HTML + CSS (glassmorphism dark/light theme)
- Jinja2 templating with reusable macros
- No JavaScript frameworks — fast and lightweight

---

## 📋 Prerequisites

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) (recommended) **or** `pip`
- A **Google Cloud Project** with OAuth 2.0 credentials
- A **Wikimedia consumer** registered at [Special:OAuthConsumerRegistration](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration) (select **OAuth 2.0**)

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/Wiki-For-All-Technical/codecatalyst.git
cd codecatalyst
```

### 2. Create a virtual environment

```bash
# Using uv (recommended — this project uses uv)
uv venv
uv pip install -r requirements.txt

# Or using standard pip
python3 -m venv .venv
source .venv/bin/activate   # Linux / macOS
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your credentials:

```env
FLASK_SECRET_KEY="your-long-random-secret-key"

# Google OAuth 2.0
# From: https://console.cloud.google.com → APIs & Services → Credentials
GOOGLE_CLIENT_ID="your-google-client-id"
GOOGLE_CLIENT_SECRET="your-google-client-secret"
GOOGLE_REDIRECT_URI="http://localhost:5000/oauth2callback"

# Wikimedia OAuth 2.0
# Register at: https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration
# Select "OAuth 2.0" — set redirect URI to http://localhost:5000/wiki_callback
WIKI_CLIENT_ID="your-wikimedia-client-id"
WIKI_CLIENT_SECRET="your-wikimedia-client-secret"
WIKI_REDIRECT_URI="http://localhost:5000/wiki_callback"
```

### 4. Enable Google APIs

In [Google Cloud Console](https://console.cloud.google.com):
1. Enable **Google Drive API**
2. Enable **Google Photos Library API**
3. Add your email as a **test user** under the OAuth consent screen

---

## ▶️ Running the Application

### Quick start (recommended)

```bash
./run.sh
```

This automatically activates the virtual environment, syncs dependencies, and starts the Flask dev server.

### Manual start

```bash
source .venv/bin/activate   # or: .venv\Scripts\activate on Windows
flask run --debug
```

Then open your browser at **http://localhost:5000**

---

## 📂 Project Structure

```
codecatalyst/
│
├── app.py                    # Application factory + Authlib OAuth registry
├── config.py                 # All configuration (OAuth endpoints, scopes, etc.)
├── run.sh                    # One-click venv-aware dev server launcher
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
│
├── auth/                     # Authentication modules
│   ├── google.py             # Google OAuth 2.0 flow
│   └── wiki.py               # Wikimedia OAuth 2.0 flow (Authlib)
│
├── routes/                   # Flask blueprints (thin controllers)
│   ├── main.py               # /, /google_login, /wiki_callback, /about, /privacy, /terms
│   ├── gallery.py            # /gallery/* — image fetching and proxy
│   └── upload.py             # /upload/* — metadata, Wikimedia auth, upload pipeline
│
├── services/                 # Business logic layer
│   ├── google_service.py     # Google Photos & Drive image fetching
│   └── wikimedia_service.py  # Bearer token CSRF fetch + Commons upload
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Base layout (header, footer, theme toggle)
│   ├── index.html            # Home page
│   ├── about.html            # About page
│   ├── gallery.html          # Image selection gallery
│   ├── metadata.html         # Per-image metadata form
│   ├── select_domain.html    # Google Photos vs Drive picker
│   ├── upload_result.html    # Upload results summary
│   ├── wiki_login.html       # Wikimedia connect page
│   ├── wiki_success.html     # Post-OAuth success page
│   ├── privacy.html          # Privacy Policy
│   ├── terms.html            # Terms of Use
│   └── partials/
│       └── macros.html       # Reusable Jinja2 macros (steps_bar, flash_messages, etc.)
│
└── static/
    └── style.css             # Premium dark/light theme CSS
```

---

## 🧠 How It Works

```
1. Login with Google  →  Grant access to Photos / Drive
2. Login with Wikimedia  →  OAuth 2.0 consent via Authlib
3. Pick source  →  Google Photos or Google Drive
4. Select images  →  Multi-select gallery with AJAX pagination
5. Add metadata  →  Title, description, categories per image
6. Upload  →  Bearer token auth → CSRF token → MediaWiki upload API
7. Results  →  Success/failure summary with Commons links
```

---

## 🔒 Security & Privacy

- **No password storage** — OAuth 2.0 tokens are stored in server-side sessions only
- **No permanent file storage** — images pass through in-memory during upload, never written to disk
- **Session expiry** — sessions expire after 1 hour
- **Wikimedia Cloud Services compliant** — follows all ToU requirements
- See [Privacy Policy](/privacy) and [Terms of Use](/terms) in the running app

---

## 📌 Use Cases

- 📷 Contributors uploading their own photos to Wikimedia Commons
- 🏛️ GLAMs (Galleries, Libraries, Archives, Museums) batch-uploading collections
- 🎓 Educational content creators sharing freely licensed media
- 📰 Journalists and researchers contributing to the free knowledge movement

---

## 🤝 Contributing

Contributions, bug reports, and feature requests are welcome!

1. **Fork** the repository
2. **Create** a feature branch: `git checkout -b feature/my-feature`
3. **Commit** your changes: `git commit -m 'feat: add my feature'`
4. **Push** to the branch: `git push origin feature/my-feature`
5. **Open** a Pull Request

Please follow the existing code style and add tests where applicable.

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👩‍💻 Authors

Developed and maintained by the **[Wiki For All Technical](https://github.com/Wiki-For-All-Technical)** team as part of an initiative to simplify media contribution to Wikimedia Commons.

---

> Built with ❤️ for the free knowledge movement · Hosted on [Wikimedia Cloud Services](https://wikitech.wikimedia.org)
