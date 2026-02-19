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
| 🔗 **No Photos API needed** | Share a public album link — photos fetched without API approval |
| 📁 **Google Drive** | Browse and select image files directly from your Drive |
| 📤 **Batch Uploads** | Select multiple images and upload them all at once |
| 🏷️ **Rich Metadata** | Set title, description, and Wikimedia categories per image |
| 🌙 **Dark / Light Mode** | Persistent theme toggle with no flash on reload |
| 📋 **Privacy & ToS** | Built-in Privacy Policy and Terms of Use pages |
| 📱 **Responsive UI** | Works on desktop, tablet, and mobile |

---

## �️ Google Photos — Shared Album Approach

> **No Google Photos API approval required.**

Instead of using the restricted Google Photos Library API (which requires OAuth scope approval that many cloud-hosted apps cannot obtain), G2Commons uses a **shared public album** approach:

1. Open [photos.google.com](https://photos.google.com) and go to **Albums**
2. Open the album you want to upload
3. Click the **share icon** → enable **"Anyone with the link can view"**
4. Copy the link and paste it into G2Commons
5. G2Commons fetches all photos directly from the public album URL

### Why this is better
- ✅ **No API key needed** — just a public link
- ✅ **More privacy-friendly** — you share only a specific album, not your entire library
- ✅ **No OAuth scope approval** — works on all hosting environments including Wikimedia Cloud
- ✅ **Full-resolution images** — fetched at original quality for Commons upload

---

## �🛠️ Tech Stack

**Backend**
- Python 3.14 · Flask 3
- [Authlib](https://docs.authlib.org) — OAuth 2.0 for both Google and Wikimedia
- Flask-Session — server-side session management
- Google Drive API — Drive image browsing (OAuth)
- Google Photos — public shared album HTML scraping (no API key)
- MediaWiki REST API — Wikimedia Commons uploads

**Frontend**
- Vanilla HTML + CSS (glassmorphism dark/light theme)
- Jinja2 templating with reusable macros
- No JavaScript frameworks — fast and lightweight

---

## 📋 Prerequisites

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) (recommended) **or** `pip`
- A **Google Cloud Project** with OAuth 2.0 credentials (for Google Drive only)
- A **Wikimedia consumer** registered at [Special:OAuthConsumerRegistration](https://meta.wikimedia.org/wiki/Special:OAuthConsumerRegistration) (select **OAuth 2.0**)

> **Note:** You do **not** need to enable the Google Photos Library API. The shared album approach works without it.

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

# Google OAuth 2.0  (needed for Google Drive; NOT needed for Google Photos)
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
1. Enable **Google Drive API** ← required for Drive source
2. ~~Google Photos Library API~~ ← **NOT required** (we use shared album links instead)
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
source .venv/bin/activate
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
│   ├── google_service.py     # Shared album scraper + Google Drive fetching
│   └── wikimedia_service.py  # Bearer token CSRF fetch + Commons upload
│
├── templates/                # Jinja2 HTML templates
│   ├── base.html             # Base layout (header, footer, theme toggle)
│   ├── index.html            # Home page
│   ├── about.html            # About page
│   ├── gallery.html          # Image selection gallery
│   ├── metadata.html         # Per-image metadata form
│   ├── select_domain.html    # Source picker (album URL input or Drive)
│   ├── upload_result.html    # Upload results summary
│   ├── wiki_login.html       # Wikimedia connect page
│   ├── wiki_success.html     # Post-OAuth success page
│   ├── privacy.html          # Privacy Policy
│   ├── terms.html            # Terms of Use
│   └── partials/
│       └── macros.html       # Reusable Jinja2 macros
│
└── static/
    └── style.css             # Premium dark/light theme CSS
```

---

## 🧠 How It Works

```
Google Photos flow:
──────────────────
1. User creates a public Google Photos shared album
2. User pastes the shared link into G2Commons
3. G2Commons fetches the album's public HTML page (no API key needed)
4. Photo URLs are extracted from lh3.googleusercontent.com CDN links
5. Thumbnails are displayed; full-res originals uploaded to Commons

Google Drive flow:
──────────────────
1. Login with Google → OAuth grants Drive read access
2. Browse image files from your Drive
3. Select images → add metadata → upload to Commons

Common steps:
─────────────
4. Login with Wikimedia → OAuth 2.0 (Authlib)
5. Add title, description, and categories per image
6. Upload via MediaWiki API with Bearer token
7. Results page with success/failure + direct Commons links
```

---

## 🔒 Security & Privacy

- **No password storage** — OAuth 2.0 tokens stored in server-side sessions only
- **No permanent file storage** — images pass through in-memory, never written to disk
- **Minimal Google permissions** — only Drive access (no Photos library access)
- **Shared album privacy** — user controls exactly which album is shared
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

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## 👩‍💻 Authors

Developed and maintained by the **[Wiki For All Technical](https://github.com/Wiki-For-All-Technical)** team as part of an initiative to simplify media contribution to Wikimedia Commons.

---

> Built with ❤️ for the free knowledge movement · Hosted on [Wikimedia Cloud Services](https://wikitech.wikimedia.org)
