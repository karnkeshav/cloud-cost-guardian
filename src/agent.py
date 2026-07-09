import os
from google import genai
from google.genai import types
from pydantic import BaseModel
import json
from dotenv import load_dotenv

load_dotenv()

_client = None

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
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ClassificationResult,
            ),
        )
        return json.loads(response.text)
    except Exception as e:
        return {"bucket": "Unknown", "reasoning": "Failed to classify: " + str(e)}

