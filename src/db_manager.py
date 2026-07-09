import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables (GitHub Secrets or .env)
load_dotenv()

_supabase_client = None

def get_supabase_client() -> Client:
    """Returns the initialized Supabase client, lazily creating it if needed."""
    global _supabase_client
    if _supabase_client is None:
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY environment variables must be configured.")
        _supabase_client = create_client(supabase_url, supabase_key)
    return _supabase_client

def insert_report_data(data_list):
    """Inserts a list of dictionaries into the Supabase table with success tracking."""
    try:
        client = get_supabase_client()
        response = client.table("cloud_billing_reports").insert(data_list).execute()
        return {"success": True, "data": response}
    except Exception as e:
        print(f"Error inserting into Supabase: {e}")
        # Returning a dictionary allows your main script to handle errors gracefully
        return {"success": False, "error": str(e)}

def insert_ticket_data(data_list):
    """Inserts a list of dictionaries into the Supabase remediation_tickets table."""
    try:
        client = get_supabase_client()
        response = client.table("remediation_tickets").insert(data_list).execute()
        return {"success": True, "data": response}
    except Exception as e:
        print(f"Error inserting ticket into Supabase: {e}")
        return {"success": False, "error": str(e)}


