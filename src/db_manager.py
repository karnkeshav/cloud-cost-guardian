import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables (GitHub Secrets or .env)
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def insert_report_data(data_list):
    """Inserts a list of dictionaries into the Supabase table with success tracking."""
    try:
        response = supabase.table("cloud_billing_reports").insert(data_list).execute()
        return {"success": True, "data": response}
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        # Returning a dictionary allows your main script to handle errors gracefully
        return {"success": False, "error": str(e)}
