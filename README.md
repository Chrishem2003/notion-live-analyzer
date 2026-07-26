# 📊 Live Notion Data Analyzer & Visualizer

A real-time Streamlit dashboard that syncs with your Notion database, visualizes metrics, and monitors upload status.

---

## ✨ Features

- 🔗 **Live Notion Sync** — Queries your Notion database in real-time
- 📈 **Interactive Charts** — Bar charts, pie charts, and data tables
- 🔑 **Per-Workspace Credential Setup** — Each user enters their own Notion API token
- ⏰ **Keep-Alive System** — Prevents app from sleeping on free hosting tiers
- 🖼️ **Custom Background** — Branded background image support
- 🔄 **Auto-Refresh** — Configurable refresh cadence (30s, 60s, 5min, or off)

---

## 🚀 Deployment (Render / Fly.io / Railway)

### Option 1: Deploy on Render (Free Tier)

1. Fork or push this repo to GitHub
2. In Render Dashboard → **New +** → **Web Service**
3. Connect your GitHub repo
4. Render will auto-detect the `render.yaml`
5. Set environment variables:
   - `NOTION_TOKEN` — Your Notion Internal Integration Secret
   - `DATABASE_ID` — *(optional)* Your Notion database ID (leave blank for auto-discover)
6. Deploy!

### Option 2: Deploy with Docker

```bash
docker build -t notion-live-analyzer .
docker run -p 8501:8501 -e NOTION_TOKEN="ntn_xxxx" notion-live-analyzer
```

### Option 3: Deploy manually

```bash
pip install -r requirements.txt
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

---

## 🔐 Credential Setup (Per-User / Workspace Duplication)

This app is designed to be **duplicated by many users** into their own Notion workspaces.

### When you first open the app:
1. You'll see a **"Connect Your Notion Workspace"** screen
2. Go to [https://www.notion.so/my-integrations](https://www.notion.so/my-integrations)
3. Click **"New Integration"** → Give it a name → Submit
4. Copy the **"Internal Integration Secret"** (starts with `ntn_`)
5. Paste it into the token field and click **"Test & Save Connection"**
6. *(Optional)* Enter your Database ID, or leave blank for auto-discovery

> ⚠️ **Security:** Your token is stored only in your browser session. It is never written to disk or shared.

### If your token becomes invalid:
The app auto-detects 401/403 errors and shows the setup wizard again — simply re-enter your credentials.

### Resetting:
Click **"Reset Configuration"** in the setup wizard to clear stored credentials.

---

## ⏰ Preventing App Sleep (Keep-Alive)

Free hosting plans (Render, Fly.io, etc.) spin down apps after **15 minutes of inactivity**.

### 1️⃣ Client-Side Keep-Alive (Built-in)
In the sidebar, enable **"Keep-Alive"** and choose a ping interval. While your browser tab is open, the app will ping itself periodically.

### 2️⃣ Render Cron Job (24/7 Uptime)
This repo includes a `render.yaml` with a cron job that pings your app every 10 minutes:

```yaml
schedule: "*/10 * * * *"
```

**To activate it:**
1. Deploy via `render.yaml` (Blueprints)
2. Set the `RENDER_EXTERNAL_URL` environment variable to your app URL
3. The cron job will automatically keep your app awake

### 3️⃣ External Uptime Monitors (Free)
Set up a free monitor to ping your app URL every 10-15 minutes:

| Service | URL | Free Tier |
|---------|-----|-----------|
| **UptimeRobot** | https://uptimerobot.com | 50 monitors, 5-min interval |
| **cron-job.org** | https://cron-job.org | Unlimited, 10-min interval |
| **Kaffeine** | https://kaffeine.herokuapp.com | Free, for Heroku-like platforms |

Paste your app URL (e.g., `https://your-app.onrender.com`) into the monitor.

---

## 📁 Project Structure

```
notion-live-analyzer/
├── app.py                 # Main Streamlit dashboard
├── images/
│   └── background.jpg     # Optional background image
├── .streamlit/
│   └── config.toml        # Streamlit server configuration
├── render.yaml            # Render deployment config (web + cron)
├── Dockerfile             # Docker build
├── runtime.txt            # Python version pin
├── requirements.txt       # Python dependencies
├── Procfile               # Heroku-style start command
└── README.md              # This file
```

---

## 🔧 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NOTION_TOKEN` | ✅ | Notion Internal Integration Secret |
| `AUDIT_MASTER_PASSWORD` | ❌ | Unlocks the Forensic Audit view (view stays locked if unset) |
| `PROJECT_COLLAB_SIGNING_KEY` | ❌ | JWT signing key for Project Collaboration (random per-process if unset) |
| `DATABASE_ID` | ❌ | Notion database ID (auto-discovers if blank) |
| `RENDER_EXTERNAL_URL` | ❌ | Your app URL (used by cron keep-alive) |
| `PYTHON_VERSION` | ❌ | Python version (default: 3.11.9) |

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## 📄 License

MIT — Free for personal and commercial use.

---

*Built with ❤️ using Streamlit & Notion API*

