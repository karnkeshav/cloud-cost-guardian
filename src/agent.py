import os
import time
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
from dotenv import load_dotenv

load_dotenv()

_client = None

MAX_RETRIES = 3
RETRY_BASE_DELAY_SECONDS = 2

# Buckets whose severity is a function of wasted spend. 'Misconfigured/Non-compliant'
# is excluded because its severity reflects security/compliance risk, not cost.
COST_DRIVEN_BUCKETS = {"Idle Resource", "Oversized/Rightsizing", "Orphaned Resource"}

def get_gemini_client():
    """Returns the initialized Gemini client, lazily creating it if needed."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable must be configured.")
        _client = genai.Client(api_key=api_key)
    return _client

class ClassificationResult(BaseModel):
    bucket: str
    reasoning: str
    resolver_group: str
    ticket_title: str
    ticket_description: str
    severity: str

def classify_resource(resource_json):
    prompt = f"""
    Analyze the following cloud resource usage data and classify it into one of these 4 buckets:
    'Idle Resource', 'Oversized/Rightsizing', 'Orphaned Resource', or 'Misconfigured/Non-compliant'.
    
    Determine the following details for cost optimization:
    1. **bucket**: The category from the 4 buckets above.
    2. **reasoning**: Brief analysis explaining why this classification was chosen.
    3. **resolver_group**: Assign to the most appropriate team:
       - 'DevOps/Compute Team' for Compute, EC2, Lambda, Autoscaling, etc.
       - 'Storage & Database Team' for RDS, S3, EBS, DynamoDB, backups, etc.
       - 'Security & Compliance Team' for IAM, misconfigured Security Groups, or non-compliant policies.
       - 'Finance Team' for Tax, fees, or general cost allocations.
    4. **ticket_title**: A concise, action-oriented ticket title (e.g., 'Decommission Idle EBS Volume: vol-012b').
    5. **ticket_description**: Clear, step-by-step remediation instructions for the resolver group to optimize this resource.
    6. **severity**: Choose from 'Low', 'Medium', 'High', or 'Critical' based on the potential cost wastage or security impact.
    
    Data to analyze:
    {resource_json}
    """


    try:
        client = get_gemini_client()
    except ValueError as e:
        # Missing/invalid config won't fix itself on retry - fail fast.
        return {"bucket": "Unknown", "reasoning": "Failed to classify: " + str(e), "needs_review": True}

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ClassificationResult,
                ),
            )
            result = json.loads(response.text)
            return _verify_classification(result, resource_json)
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BASE_DELAY_SECONDS * (2 ** (attempt - 1)))

    return {
        "bucket": "Unknown",
        "reasoning": f"Failed to classify after {MAX_RETRIES} attempts: {last_error}",
        "resolver_group": "Unassigned",
        "ticket_title": "Manual Classification Required",
        "ticket_description": "The AI classifier failed after multiple retries. Please review this resource manually.",
        "severity": "Medium",
        "needs_review": True,
    }


def _verify_classification(result, resource_json):
    """Deterministic sanity check on the model's output before it becomes a ticket.

    This is the 'verify' step of a reason -> verify -> act loop: it doesn't trust
    the model's severity blindly, and it flags anything high-stakes for a human
    to confirm rather than auto-acting on it.
    """
    try:
        resource = json.loads(resource_json)
    except (TypeError, ValueError):
        resource = {}

    cost = float(resource.get("lineItem/UnblendedCost") or 0)
    bucket = result.get("bucket")
    severity = result.get("severity")

    if bucket in COST_DRIVEN_BUCKETS and severity in ("Critical", "High") and cost < 1.0:
        result["reasoning"] = (
            (result.get("reasoning") or "")
            + f" [Auto-adjusted severity from {severity} to Low: unblended cost "
            + f"${cost:.4f} does not justify that priority.]"
        ).strip()
        result["severity"] = "Low"
        severity = "Low"

    # Gate anything high-stakes behind human review instead of auto-opening it.
    result["needs_review"] = severity in ("Critical", "High")
    return result

