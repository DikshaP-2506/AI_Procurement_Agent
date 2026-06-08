#!/bin/bash
cd /Users/riddhij08/Project/Capgemini/AI_Procurement_Agent/backend
python -m uvicorn app.main:app --reload --port 8000
