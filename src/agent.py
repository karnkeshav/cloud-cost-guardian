import os
from google import genai
import json
from dotenv import load_dotenv

load_dotenv()

# New Client Initialization
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def classify_resource(resource_json):
    prompt = f"""
    Analyze the following cloud resource usage data and classify it into one of these 4 buckets:
    'Idle Resource', 'Oversized/Rightsizing', 'Orphaned Resource', or 'Misconfigured/Non-compliant'.
    
    Data: {resource_json}
    
    Return the response as a strict JSON object with two keys: "bucket" and "reasoning".
    """
    
    # Use the new client.models.generate_content method
    response = client.models.generate_content(
        model="gemini-2.0-flash", 
        contents=prompt
    )
    
    try:
        clean_json = response.text.replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        return {"bucket": "Unknown", "reasoning": "Failed to classify: " + str(e)}
