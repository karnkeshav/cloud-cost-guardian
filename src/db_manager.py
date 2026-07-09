import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from the GitHub Secrets configuration
load_dotenv()

SUPABASE_URL = os.getenv("https://yagecbzykodypgjkaazo.supabase.co")
SUPABASE_KEY = os.getenv("sb_publishable_JkfpUKTHBirzTLILyZOlGg_iGfucFgm")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_report_data(data_list):
    """Inserts a list of dictionaries into the Supabase table."""
    try:
        response = supabase.table("cloud_billing_reports").insert(data_list).execute()
        return response
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        return None
