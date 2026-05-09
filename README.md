# Alpha Town — Intelligence Operating Environment

A zero-budget, fully operational OSINT platform. 14 autonomous AI agents scrape real public data, analyze it via Groq LLM, detect cross-agent convergence, and surface intelligence briefs.

## Quick Start

```bash
pip install -r requirements.txt
cp .env.example .env
# Add your GROQ_API_KEY to .env
python app.py
# Open http://localhost:5000
```

## Files

| File | Purpose |
|------|---------|
| `app.py` | Flask backend + scheduler |
| `database.py` | SQLite/Supabase dual-mode |
| `requirements.txt` | Dependencies |
| `.env.example` | Environment template |
| `index.html` | Dashboard shell |
| `city.css` | Professional dark theme |
| `app.js` | Dashboard logic |
| `agents/*.py` | 14 agent implementations |

## Setup Guide

See **[SETUP.md](SETUP.md)** for complete step-by-step:
- Groq API key (free)
- Supabase setup (free, optional)
- Render deployment (free)
- GitHub Pages deployment (free)
- cron-job.org keepalive (free)

## Architecture

```
GitHub Pages (Frontend) → Render (Flask Backend) → Groq LLM + Public APIs
                                    ↓
                              SQLite / Supabase
```

**Total cost: $0**

## License

MIT
