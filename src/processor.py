import pandas as pd
from agent import classify_resource
from db_manager import insert_report_data, insert_ticket_data

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
        
        # Prepare billing payload for cloud_billing_reports (matches standard AWS bill columns)
        billing_payload = {
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
            "status": "processed"
        }

        # Prepare ticket payload for remediation_tickets (remediation tasks registry)
        ticket_payload = {
            "resource_id": row.get('lineItem/ResourceId'),
            "product_code": row.get('lineItem/ProductCode'),
            "unblended_cost": float(row.get('lineItem/UnblendedCost', 0)) if pd.notna(row.get('lineItem/UnblendedCost')) else 0.0,
            "bucket_category": ai_result.get('bucket'),
            "ai_reasoning": ai_result.get('reasoning'),
            "resolver_group": ai_result.get('resolver_group'),
            "ticket_title": ai_result.get('ticket_title'),
            "ticket_description": ai_result.get('ticket_description'),
            "severity": ai_result.get('severity'),
            "status": "open"
        }
        
        # 2. Act: Insert into Supabase tables
        bill_res = insert_report_data([billing_payload])
        if not (bill_res and bill_res.get("success")):
            print(f"Failed to insert billing report: {billing_payload['resource_id']}. Error: {bill_res.get('error') if bill_res else 'Unknown'}")
            continue

        ticket_res = insert_ticket_data([ticket_payload])
        if not (ticket_res and ticket_res.get("success")):
            print(f"Failed to insert remediation ticket: {ticket_payload['resource_id']}. Error: {ticket_res.get('error') if ticket_res else 'Unknown'}")
            # We still mark CSV as processed since billing was saved, but notify the issue
        
        # Update local CSV status
        df.at[index, 'status'] = 'processed'
        df.at[index, 'decision'] = ai_result.get('bucket')
        df.to_csv(file_path, index=False)
        print(f"Successfully processed resource & created ticket for: {billing_payload['resource_id']}")

if __name__ == "__main__":
    # Point this to your data path
    process_csv('data/raw/cur_report_updated.csv')


