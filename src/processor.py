import pandas as pd
from agent import classify_resource
from db_manager import insert_report_data

def process_csv(file_path):
    """Reads the CSV, processes each row via Gemini, and saves to Supabase."""
    df = pd.read_csv(file_path)
    
    # Filter for pending rows only
    pending_rows = df[df['status'] == 'pending']
    
    if pending_rows.empty:
        print("No pending rows to process.")
        return
    
    for index, row in pending_rows.iterrows():
        # Convert row to a clean JSON string for the AI
        resource_json = row.to_json()
        
        # 1. Decide: Get classification from Gemini
        ai_result = classify_resource(resource_json)
        
        # Prepare data for Supabase
        db_payload = {
            "resource_id": row.get('lineItem/ResourceId'),
            "product_code": row.get('lineItem/ProductCode'),
            "unblended_cost": float(row.get('lineItem/UnblendedCost', 0)) if pd.notna(row.get('lineItem/UnblendedCost')) else 0.0,
            "billing_start_date": row.get('bill/BillingPeriodStartDate') if pd.notna(row.get('bill/BillingPeriodStartDate')) else None,
            "billing_end_date": row.get('bill/BillingPeriodEndDate') if pd.notna(row.get('bill/BillingPeriodEndDate')) else None,
            "usage_account_id": str(row.get('lineItem/UsageAccountId')) if pd.notna(row.get('lineItem/UsageAccountId')) else None,
            "usage_type": row.get('lineItem/UsageType') if pd.notna(row.get('lineItem/UsageType')) else None,
            "usage_amount": float(row.get('lineItem/UsageAmount', 0)) if pd.notna(row.get('lineItem/UsageAmount')) else 0.0,
            "line_item_description": row.get('lineItem/LineItemDescription') if pd.notna(row.get('lineItem/LineItemDescription')) else None,
            "region": row.get('product/region') if pd.notna(row.get('product/region')) else None,
            "bucket_category": ai_result.get('bucket'),
            "ai_reasoning": ai_result.get('reasoning'),
            "resolver_group": ai_result.get('resolver_group'),
            "ticket_title": ai_result.get('ticket_title'),
            "ticket_description": ai_result.get('ticket_description'),
            "severity": ai_result.get('severity'),
            "status": "processed"
        }


        
        # 2. Act: Insert into Supabase
        result = insert_report_data([db_payload])
        
        if result and result.get("success"):
            df.at[index, 'status'] = 'processed'
            df.at[index, 'decision'] = ai_result.get('bucket')
            df.to_csv(file_path, index=False)
            print(f"Successfully processed resource: {db_payload['resource_id']}")
        else:
            print(f"Failed to process: {db_payload['resource_id']}. Error: {result.get('error') if result else 'Unknown'}")

if __name__ == "__main__":
    # Point this to your data path
    process_csv('data/raw/cur_report_updated.csv')

