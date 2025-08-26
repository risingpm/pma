# PM Agent

Modern PM onboarding agent with:
- FastAPI backend (pmagent_api.py) wrapping pmagent.py
- Next.js + Tailwind frontend in /web with a 6-step onboarding wizard

Quick Start

Backend:
python -m uvicorn pmagent_api:app --host 0.0.0.0 --port 8000 --reload

Frontend:
cd web
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm i
npm run dev

Common Issues
- Port busy: npx kill-port 3000  (or 8000)
- CORS: API allows http://localhost:3000 by default (see pmagent_api.py)
- Network Error in UI: frontend uses fetch in web/lib/api.ts

Repo Structure
pmagent.py
pmagent_api.py
web/
pmagent_data/
