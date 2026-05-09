# Alpha Town — Complete Setup Guide

## What You're Building

Alpha Town is a **zero-budget, fully operational OSINT platform** — not a toy. It runs 14 autonomous AI agents that scrape real public data sources, analyze them through a Groq LLM, detect cross-agent signal convergence, and surface intelligence briefs and job opportunities.

**Stack:** Python/Flask backend + Vanilla JS frontend + SQLite (local) or Supabase (cloud) + Groq (free LLM) + Render (free hosting)

---

## Step 1: Get Your API Keys (All Free)

### 1A. Groq API Key (REQUIRED for AI intelligence)

Groq provides free inference on Llama-3.3-70B. This is what makes your agents "smart."

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up with email or GitHub
3. Click **"API Keys"** in the left sidebar
4. Click **"Create API Key"**
5. Name it `alphatown`
6. Copy the key (starts with `gsk_`)
7. Paste it into your `.env` file:
   ```bash
   GROQ_API_KEY=gsk_your_actual_key_here
   ```

**Free tier limits:** 20 requests/minute, 1,440 requests/day, 6,000 tokens/minute. More than enough.

### 1B. Supabase (Optional — for cloud database)

If you want data to persist between Render restarts, use Supabase. Otherwise SQLite works fine locally.

1. Go to [supabase.com](https://supabase.com)
2. Click **"New Project"**
3. Name: `alphatown`
4. Database password: generate a strong one, save it
5. Region: pick closest to your users (e.g., `us-east-1`)
6. Click **"Create new project"**
7. Wait ~2 minutes for provisioning
8. Go to **Project Settings → API**
9. Copy:
   - `URL` (e.g., `https://abcdefgh12345678.supabase.co`)
   - `anon public` key (for frontend auth, if you add it later)
   - `service_role` key (for backend — keep secret!)
10. Paste into `.env`:
    ```bash
    SUPABASE_URL=https://your-project.supabase.co
    SUPABASE_KEY=your-anon-key
    SUPABASE_SERVICE_KEY=your-service-role-key
    ```

**You don't need to create tables manually.** The backend auto-creates SQLite tables. For Supabase, create these tables in the SQL Editor:

```sql
CREATE TABLE posts (
    id TEXT PRIMARY KEY,
    citizen TEXT NOT NULL,
    type TEXT NOT NULL,
    body TEXT NOT NULL,
    tags JSONB DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    tier TEXT DEFAULT 'free',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    reactions INTEGER DEFAULT 0,
    source_urls JSONB DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE seen_items (
    id TEXT PRIMARY KEY,
    agent TEXT NOT NULL,
    hash TEXT NOT NULL UNIQUE,
    seen_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_runs (
    id SERIAL PRIMARY KEY,
    agent TEXT NOT NULL,
    status TEXT,
    items_found INTEGER DEFAULT 0,
    items_posted INTEGER DEFAULT 0,
    error TEXT,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE briefs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    agents_involved JSONB DEFAULT '[]',
    confidence REAL DEFAULT 0.5,
    tier TEXT DEFAULT 'premium',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    source_agent TEXT,
    trigger_post_id TEXT,
    url TEXT,
    posted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_posts_citizen ON posts(citizen);
CREATE INDEX idx_posts_timestamp ON posts(timestamp DESC);
CREATE INDEX idx_seen_items_agent ON seen_items(agent);
```

### 1C. Other Data APIs (Optional — agents work without them)

| Service | What For | Get Key At | Free Tier |
|---------|----------|-----------|-----------|
| Alpha Vantage | Stock data | alphavantage.co/support/#api-key | 25 calls/day |
| FRED | Economic data | research.stlouisfed.org/useraccount/apikey | 120 calls/min |
| NewsAPI | News headlines | newsapi.org/register | 100 calls/day |
| EIA | Energy data | eia.gov/opendata/register.php | 100,000 calls |
| NOAA | Weather data | weather.gov/documentation/services-web-api | No key needed |

**Agents work without these.** They fall back to synthetic/demo data or RSS feeds that need no key.

---

## Step 2: Local Development (Test Everything First)

```bash
# 1. Clone/download the project files into a folder
cd alpha-town

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create environment file
cp .env.example .env

# 6. Edit .env with your keys
# Use any text editor — nano, vim, VS Code, Notepad

# 7. Run the backend
python app.py
```

The server starts on `http://localhost:5000`

**Test it:**
- Open `http://localhost:5000/api/health` → should show `{"status": "alive"}`
- Open `http://localhost:5000/api/agents` → should list all 14 agents

**Trigger a test run:**
```bash
curl -X POST http://localhost:5000/api/trigger/MARCUS
```

Wait 10-30 seconds, then check `http://localhost:5000/api/posts` — you should see signals.

---

## Step 3: Deploy Backend to Render (Free)

### 3A. Push to GitHub

```bash
# In your alpha-town folder
git init
git add .
git commit -m "Alpha Town v1.0"

# Create a new repo on GitHub (don't add README/license)
# Then:
git remote add origin https://github.com/YOURNAME/alpha-town.git
git branch -M main
git push -u origin main
```

### 3B. Deploy on Render

1. Go to [render.com](https://render.com) → Sign up with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your `alpha-town` GitHub repo
4. Configure:
   - **Name:** `alpha-town`
   - **Region:** US East (or closest)
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
5. Click **"Advanced"** and add Environment Variables:
   - `GROQ_API_KEY` = your key
   - `SUPABASE_URL` = (if using)
   - `SUPABASE_SERVICE_KEY` = (if using)
   - `SECRET_KEY` = any random string (generate at random.org)
   - `FLASK_ENV` = `production`
6. Click **"Create Web Service"**
7. Wait 2-3 minutes for build
8. Your URL will be: `https://alpha-town.onrender.com`

**Test:** Visit `https://alpha-town.onrender.com/api/health`

---

## Step 4: Deploy Frontend to GitHub Pages (Free)

The frontend is just static HTML/CSS/JS. It talks to your Render backend.

### 4A. Update API URL

In `app.js`, change this line:
```javascript
const API_BASE = window.location.origin.includes('github.io') 
    ? 'https://alpha-town.onrender.com'  // <-- YOUR RENDER URL
    : window.location.origin;
```

### 4B. Create GitHub Pages Repo

You have two options:

**Option A: Same repo as backend (simplest)**

Your `index.html`, `city.css`, and `app.js` are already in the repo root. GitHub Pages can serve them.

1. On GitHub, go to your `alpha-town` repo → **Settings**
2. Scroll to **Pages** (left sidebar)
3. **Source:** Deploy from a branch
4. **Branch:** `main` → `/ (root)`
5. Click **Save**
6. Wait 1-2 minutes
7. Your site: `https://yourname.github.io/alpha-town/`

**Option B: Separate frontend repo (cleaner)**

```bash
mkdir alpha-town-frontend
cd alpha-town-frontend
cp ../alpha-town/index.html .
cp ../alpha-town/city.css .
cp ../alpha-town/app.js .
git init
git add .
git commit -m "Frontend v1"
git remote add origin https://github.com/YOURNAME/alpha-town-frontend.git
git push -u origin main
```

Then enable GitHub Pages on that repo.

---

## Step 5: Keep Render Alive (Free Tier Fix)

Render free tier sleeps after 15 minutes of inactivity. Use cron-job.org to ping it.

1. Go to [cron-job.org](https://cron-job.org)
2. Sign up (free, no credit card)
3. Click **"Create cronjob"**
4. Configure:
   - **Title:** Alpha Town Keepalive
   - **URL:** `https://alpha-town.onrender.com/api/trigger/all`
   - **Method:** POST
   - **Schedule:** Every 10 minutes
5. Click **Create**

This does TWO things:
- Keeps Render awake
- Triggers all agents to run every 10 minutes

---

## Step 6: Verify Everything Works

### Checklist:

- [ ] `https://yourname.github.io/alpha-town/` loads the dashboard
- [ ] Boot sequence plays
- [ ] Agent grid shows 14 agents
- [ ] `https://alpha-town.onrender.com/api/health` returns `alive`
- [ ] Trigger an agent manually via frontend or curl
- [ ] Wait 30 seconds, refresh — signals appear in feed
- [ ] Briefs panel shows "No convergence detected" (normal until 3+ agents agree)

### If Frontend Can't Connect to Backend:

**CORS error?** In `app.py`, update the CORS line:
```python
CORS(app, origins=["https://yourname.github.io", "http://localhost:5000"])
```

Then redeploy to Render.

---

## Architecture Recap

```
┌─────────────────────────────────────────────────────────────┐
│  GITHUB PAGES (Frontend)                                    │
│  index.html + city.css + app.js                             │
│  ↓ HTTPS                                                    │
├─────────────────────────────────────────────────────────────┤
│  RENDER (Backend)                                           │
│  Flask + 14 Agents + Scheduler                              │
│  ↓                                                          │
│  ├─→ Groq API (LLM analysis)                                │
│  ├─→ Yahoo Finance, SEC, CDC, arXiv, etc. (data)           │
│  └─→ Supabase/SQLite (persistence)                          │
├─────────────────────────────────────────────────────────────┤
│  CRON-JOB.ORG                                               │
│  POST /api/trigger/all every 10 min                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### "No signals today" / 0 signals

1. Check Render logs: Dashboard → Logs
2. Trigger manually: `curl -X POST https://your-app.onrender.com/api/trigger/all`
3. Wait 60 seconds, check `/api/posts`
4. If Groq key is missing, agents still run but output raw data (less useful)

### CORS errors in browser console

Update `app.py`:
```python
from flask_cors import CORS
CORS(app, origins=["https://yourname.github.io"])
```

### Agents timeout / Render kills them

Render free tier has 512MB RAM and 30-second request timeout. Agents run in background threads via APScheduler, so they survive. But if an agent takes >30s to respond to a trigger endpoint, increase gunicorn timeout or use a background worker.

### SQLite data lost on Render restart

This is expected with SQLite on ephemeral disks. **Use Supabase** for persistence, or accept that data resets (agents will re-scan on next trigger).

---

## Next Steps (After It's Running)

1. **Add more API keys** — Alpha Vantage, NewsAPI, etc. for richer data
2. **Tune agent intervals** — Edit `interval_minutes` in each agent file
3. **Add auth** — Supabase Auth for user accounts
4. **Custom agents** — Copy any agent file, change `fetch_data()`, deploy
5. **Alerts** — Add webhook/Discord/Telegram notifications for high-confidence signals

---

**Total cost: $0.00/month**
