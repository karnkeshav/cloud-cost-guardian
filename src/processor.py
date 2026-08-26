import glob
import pandas as pd
from agent import classify_resource
from db_manager import insert_report_data, insert_ticket_data, get_processed_resource_periods

def process_csv(file_path, processed_periods=None):
    """Reads the CSV, processes each row via Gemini, and saves to Supabase."""
    df = pd.read_csv(file_path)

    # Filter for pending rows only
    pending_rows = df[df['status'] == 'pending']

    if pending_rows.empty:
        print(f"No pending rows to process in {file_path}.")
        return

    # GitHub Actions runners are ephemeral, so the local CSV's 'status' column
    # doesn't survive between runs. Cross-check against Supabase (the durable
    # store) so re-running against the same CSV doesn't reclassify or
    # double-insert resources already processed for their billing period.
    if processed_periods is None:
        processed_periods = get_processed_resource_periods()

    for index, row in pending_rows.iterrows():
        billing_start = str(row.get('bill/BillingPeriodStartDate') or '')[:10]
        resource_key = (row.get('lineItem/ResourceId'), billing_start)

        if resource_key in processed_periods:
            df.at[index, 'status'] = 'processed'
            df.to_csv(file_path, index=False)
            print(f"Skipping already-processed resource: {resource_key[0]} (billing period {billing_start})")
            continue

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
            # High-stakes classifications wait for a human to confirm before
            # counting as an actionable, 'open' ticket.
            "status": "pending_review" if ai_result.get('needs_review') else "open"
        }

        # 2. Act: Insert into Supabase tables
        bill_res = insert_report_data([billing_payload])
        if not (bill_res and bill_res.get("success")):
            print(f"Failed to insert billing report: {billing_payload['resource_id']}. Error: {bill_res.get('error') if bill_res else 'Unknown'}")
            continue

        processed_periods.add(resource_key)

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
    # Process every CUR CSV dropped into data/raw/, not just one fixed filename,
    # so new monthly reports don't need to overwrite/rename a specific file.
    processed_periods = get_processed_resource_periods()
    for csv_path in sorted(glob.glob('data/raw/*.csv')):
        process_csv(csv_path, processed_periods)


