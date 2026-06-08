import os
from dotenv import load_dotenv
from pathlib import Path
import sys

# Load env from backend/.env
backend_env = Path(__file__).resolve().parent.parent / 'backend' / '.env'
load_dotenv(backend_env)

sys.path.append(str(Path(__file__).resolve().parent.parent / 'backend'))
from app.agents.quote_agent import extract_quote_data

test_text = """
DELL TECHNOLOGIES QUOTE
Date: 2024-05-20
Item: PowerEdge R650
Total Price: $12,500.00
Delivery Time: 14 business days
Warranty: 5 Years On-Site
Payment Terms: Net 45
"""

print("Testing AI Extraction...")
result = extract_quote_data(test_text)
print("Result:")
print(result)
