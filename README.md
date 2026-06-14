# ProcureAI - AI Procurement Agent
ProcureAI is an AI-driven Procurement Agent. The system combines multi-agent intelligence (scouting, risk modeling, and cross-deal negotiation leverage) with a modern web interface.

## System Architecture

The application is split into two primary packages:
* [frontend/](file:///d:/Projects/AI_Procurement_Agent/frontend) - Vite + React + TypeScript web application styled with premium glassmorphic dark-mode aesthetics.
* [backend/](file:///d:/Projects/AI_Procurement_Agent/backend) - FastAPI + Uvicorn server implementing agent orchestration, Supabase integrations, and LangChain LLM reasoning.

---

## Directory Structure

* [backend/app/agents/](file:///d:/Projects/AI_Procurement_Agent/backend/app/agents) - AI agents (Scout, Predictor, and Quote parsers).
* [backend/app/routes/](file:///d:/Projects/AI_Procurement_Agent/backend/app/routes) - REST API routing layers.
* [backend/app/services/](file:///d:/Projects/AI_Procurement_Agent/backend/app/services) - Orchestration service layers for risk, cross-deal, and recommendations.
* [frontend/src/pages/](file:///d:/Projects/AI_Procurement_Agent/frontend/src/pages) - React pages (Directory, Simulator, Risk, Negotiation).
* [frontend/src/components/](file:///d:/Projects/AI_Procurement_Agent/frontend/src/components) - Reusable UI widgets and layout.

---

## Getting Started

### 1. Backend Setup

Prerequisites: Python 3.10+ and virtualenv.

Navigate to backend directory and setup environment:
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory with the following variables:
```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
GROQ_API_KEY=your_groq_api_key
```

Start the FastAPI application:
```bash
uvicorn app.main:app --reload --port 8000
```

The server health-check will be available at `GET http://localhost:8000/`.

### 2. Frontend Setup

Prerequisites: Node.js 18+ and npm.

Navigate to frontend directory and start the dev server:
```bash
cd frontend
npm install
npm run dev
```

The web application will launch locally at `http://localhost:5173`.

---

## Key Modules and AI Agents

### 1. Decision Simulator & Comparison Engine
* **Code Reference**: [recommendation_service.py](file:///d:/Projects/AI_Procurement_Agent/backend/app/services/recommendation_service.py) | [VendorComparison.tsx](file:///d:/Projects/AI_Procurement_Agent/frontend/src/pages/VendorComparison.tsx)
* **Function**: An explainability engine that normalizes price, delivery speed, compliance, and risk metrics using customized weights to rank vendor quotes dynamically. Includes a slider for manually adding qualitative adjustment offsets.

### 2. Risk Intelligence Agent
* **Code Reference**: [risk_service.py](file:///d:/Projects/AI_Procurement_Agent/backend/app/services/risk_service.py) | [VendorRiskOverview.tsx](file:///d:/Projects/AI_Procurement_Agent/frontend/src/pages/VendorRiskOverview.tsx)
* **Function**: Aggregates historical service compliance, external threat indicators, and contract renewal proximity to predict vendor fulfillment delay probabilities. Stored in the `vendor_risk_analysis` database table.

### 3. Shadow Market Scout Agent
* **Code Reference**: [shadow_market_scout.py](file:///d:/Projects/AI_Procurement_Agent/backend/app/agents/shadow_market_scout.py)
* **Function**: Integrates rule-based signals with live news sentiment. Automatically queries Google News RSS search for the vendor, scans headlines case-insensitively for critical keywords (lawsuits, breaches, layoffs), and generates dynamic threat alerts.

### 4. Cross-Deal Negotiator Agent
* **Code Reference**: [crossdeal_service.py](file:///d:/Projects/AI_Procurement_Agent/backend/app/services/crossdeal_service.py)
* **Function**: Identifies procurement overlaps where a single supplier is bid across multiple departments. Automatically models consolidated volume discounts (5% to 15%) and lists actionable bundling recommendations.

### 5. Negotiation Outreach Assistant
* **Code Reference**: [negotiation_service.py](file:///d:/Projects/AI_Procurement_Agent/backend/app/services/negotiation_service.py)
* **Function**: Uses LangChain + Groq LLM to draft professional vendor emails tailored to specific procurement tactics, desired discount targets, and historical metrics.

---

## Database Utilities

To facilitate clean manual testing, several script files are available in the project root:

* **Complete Database Purge**: [clean_supabase.py](file:///d:/Projects/AI_Procurement_Agent/clean_supabase.py)
  Safely clears records from all tables in reverse foreign-key dependency order (vendor quotes, contracts, risk analysis, vendors, procurements, and audit logs) for a clean slate.
  ```powershell
  python clean_supabase.py
  ```

* **Standard Project Seeding**: [set_specific_projects.py](file:///d:/Projects/AI_Procurement_Agent/scratch/set_specific_projects.py)
  Populates the `procurements` table with a clean variety of standard projects across Software, Hardware, and Networking categories so you can test adding vendors and quotes manually in the UI.
  ```powershell
  python -c "import sys; sys.path.append('scratch'); import set_specific_projects; set_specific_projects.reset_to_specific_projects()"
  ```
