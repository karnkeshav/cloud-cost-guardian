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

def classify_resource(resource_json):
    prompt = f"""
    Analyze the following cloud resource usage data and classify it into one of these 4 buckets:
    'Idle Resource', 'Oversized/Rightsizing', 'Orphaned Resource', or 'Misconfigured/Non-compliant'.
    
    Data: {resource_json}
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

