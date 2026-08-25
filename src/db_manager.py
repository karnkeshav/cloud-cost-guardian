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

def get_processed_resource_periods():
    """Returns the set of (resource_id, billing_period_date) pairs already recorded
    in cloud_billing_reports.

    GitHub Actions runners are ephemeral, so the 'processed' status the pipeline
    writes back to the local CSV never survives past a single run - the next run
    checks out a fresh copy of the CSV with every row back to 'pending'. This
    queries the durable store (Supabase) instead, so re-running the workflow
    against the same CSV can't reclassify or double-insert a resource that was
    already processed for that billing period.
    """
    try:
        client = get_supabase_client()
        response = client.table("cloud_billing_reports").select("resource_id, billing_start_date").execute()
        rows = response.data or []
        processed = set()
        for r in rows:
            resource_id = r.get("resource_id")
            billing_date = (r.get("billing_start_date") or "")[:10]
            if resource_id:
                processed.add((resource_id, billing_date))
        return processed
    except Exception as e:
        print(f"Error fetching processed resource periods from Supabase: {e}")
        return set()


