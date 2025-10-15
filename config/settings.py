import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = "gemini-1.5-flash"

# Sample data paths
SAMPLE_DEALS_PATH = "data/sample_deals.json"
CRM_DATA_PATH = "data/crm_data.json"