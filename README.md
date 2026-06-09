# AI Procurement Agent

Monorepo scaffold with a separate React frontend and FastAPI backend.

## Structure

- `frontend/` - Vite + React + TypeScript app
- `backend/` - FastAPI app with Uvicorn entrypoint

## Frontend

```bash
cd frontend
npm install
npm run dev
```

## Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

## API

- Health check: `GET http://localhost:8000/health`
- Root: `GET http://localhost:8000/`

## Risk Intelligence

- Existing Supabase table: `vendor_risk_analysis`
- API routes:
	- `GET /risk/vendor/{vendor_id}`
	- `GET /risk/history/{vendor_id}`
	- `GET /risk/dashboard`
	- `POST /risk/analyze`
