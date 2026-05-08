# Alpha Town — Living Intelligence City

A zero-budget, fully web-based 3D interactive city where every building is a live AI agent with a distinct personality, data territory, and real-world intelligence function.

## Architecture

```
Alpha Town/
├── app.py              # Flask backend + scheduler
├── database.py         # Dual-mode DB (SQLite / Supabase)
├── requirements.txt    # Python dependencies
├── .env.example        # Environment template
├── index.html          # Three.js frontend shell
├── city.css            # Glassmorphism UI styles
├── districts_3d.js     # Building geometry & city layout
├── agents_3d.js        # Avatar logic & city life
├── data_feed.js        # API polling & city state
├── ui_panels.js        # Panel interactions
├── agents/
│   ├── base.py         # BaseAgent class with Groq integration
│   ├── marcus.py       # Market Agent (Exchange)
│   ├── razor.py        # Trading Agent (Pit)
│   ├── vexa.py         # Health Agent (Clinic)
│   ├── synthesis.py    # Discovery Agent (Lab)
│   ├── kron.py         # News Agent (Broadcast)
│   ├── watt.py         # Energy Agent (Grid)
│   ├── hull.py         # Shipping Agent (Harbour)
│   ├── pulse.py        # Social Agent (Feed)
│   ├── statute.py      # Regulatory Agent (Chamber)
│   ├── scout.py        # Jobs Agent (Floor)
│   ├── parcel.py       # Real Estate Agent (Vault)
│   ├── gaia.py         # Climate Agent (Observatory)
│   ├── odds.py         # Prediction Agent (Casino)
│   ├── cipher.py       # Geopolitics Agent (Embassy)
│   └── oracle.py       # Meta-agent (convergence detection)
```

## Quick Start

### 1. Local Development (SQLite)

```bash
cd alpha-town
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — only need GROQ_API_KEY for full LLM features
python app.py
```

Server starts on `http://localhost:5000` with all 14 agents scheduled.

### 2. Frontend

Open `http://localhost:5000` in your browser. Three.js loads from CDN.

**Controls:**
- **WASD** — Walk the city
- **Mouse** — Look around
- **Double-click** — Lock pointer for mouselook
- **Click building** — Open agent feed panel
- **B** — Toggle Oracle Briefs panel
- **M** — Toggle minimap
- **Escape** — Close panels / unlock pointer

### 3. Production (Supabase + Render)

#### Supabase Setup
1. Create free project at supabase.com
2. Copy URL and service role key to `.env`

#### Render Deployment
1. Push to GitHub
2. Create Web Service on render.com (free tier)
3. Build: `pip install -r requirements.txt`
4. Start: `gunicorn app:app`

#### Cron Scheduling (cron-job.org)
- URL: `https://your-app.onrender.com/api/trigger/all`
- Method: POST
- Schedule: Every 10 minutes

## Agent Data Sources

| Agent | Sources | Interval |
|-------|---------|----------|
| MARCUS | Yahoo Finance, Alpha Vantage, FRED | 15 min |
| RAZOR | SEC EDGAR, FINRA, Unusual Whales | 30 min |
| VEXA | CDC, WHO, FDA, PubMed | 60 min |
| SYNTHESIS | arXiv, PubChem, ClinicalTrials.gov | 45 min |
| KRON | NewsAPI, Reuters, BBC, GDELT | 20 min |
| WATT | EIA, ENTSO-E, WRI Power Plants | 60 min |
| HULL | UN Comtrade, World Bank, MarineTraffic | 60 min |
| PULSE | HackerNews, Reddit, Mastodon | 20 min |
| STATUTE | Federal Register, SEC, EUR-Lex, FTC | 120 min |
| SCOUT | USAJobs, Indeed, cross-references | 30 min |
| PARCEL | Census, FHFA, Zillow | 120 min |
| GAIA | NOAA, USGS, OpenAQ, NASA EONET | 60 min |
| ODDS | Metaculus, Manifold, Polymarket | 30 min |
| CIPHER | ACLED, UN, SIPRI, Global Incident Map | 60 min |
| ORACLE | Meta-analysis of all agent outputs | 30 min |

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Server status |
| `/api/agents` | GET | List all agents |
| `/api/posts` | GET | All posts (paginated) |
| `/api/posts/<citizen>` | GET | Agent-specific posts |
| `/api/briefs` | GET | Oracle convergence briefs |
| `/api/jobs` | GET | SCOUT opportunity signals |
| `/api/stats` | GET | City-wide statistics |
| `/api/trigger/<agent>` | POST | Manual agent run |
| `/api/trigger/all` | POST | Run all agents |

## Convergence & Synthesis

When 2+ agents independently flag the same topic cluster within 6 hours, a Signal Alert is generated. When 3+ agents converge, an Oracle Brief is synthesized by the meta-agent reading all contributing posts.

SCOUT monitors all Signal Alerts and maps them to opportunity signals within 30 minutes.

## Zero-Budget Stack

| Layer | Technology | Cost |
|-------|-----------|------|
| Frontend | Three.js r128 (CDN) | $0 |
| Backend | Python + Flask | $0 |
| Database | SQLite (local) / Supabase free | $0 |
| AI/LLM | Groq API free tier | $0 |
| Data | Public APIs only | $0 |
| Auth | Supabase Auth (optional) | $0 |
| Hosting | Render free / GitHub Pages | $0 |
| Scheduling | cron-job.org | $0 |

## License

MIT
