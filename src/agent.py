import os
import google.generativeai as genai
import json
from dotenv import load_dotenv

load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

def classify_resource(resource_json):
    """Sends JSON to Gemini to get a classification."""
    prompt = f"""
    Analyze the following cloud resource usage data and classify it into one of these 4 buckets:
    'Idle Resource', 'Oversized/Rightsizing', 'Orphaned Resource', or 'Misconfigured/Non-compliant'.
    
    Data: {resource_json}
    
    Return the response as a strict JSON object with two keys: "bucket" and "reasoning".
    """
    
    response = model.generate_content(prompt)
    try:
        # Extract and parse the JSON string from the response
        clean_json = response.text.replace('```json', '').replace('```', '')
        return json.loads(clean_json)
    except Exception as e:
        return {"bucket": "Unknown", "reasoning": "Failed to classify: " + str(e)}
