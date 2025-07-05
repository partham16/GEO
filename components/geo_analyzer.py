import json
from groq import Groq
import config  # Import the global config


def analyze_geo_content(content: str, groq_client: Groq, debug_mode: bool = False) -> dict:
    """Uses an LLM to perform a GEO Check, using settings from the global config."""
    if debug_mode:
        print("[GEO Analyzer] DEBUG MODE: Returning mock GEO scores.")
        return {
            "brand_sentiment": {"score": 8, "justification": "DEBUG: The content is positive."},
            "citation_propensity": {"score": 7, "justification": "DEBUG: Includes a citable statistic."},
        }

    prompt = f"""You are a world-class expert in Generative Engine Optimization (GEO). Analyze the following text and score it from 1 to 10 on the criteria below. Provide your analysis in a strict JSON format.
    TEXT TO ANALYZE:\n---\n{content}\n---\n
    JSON Response Format: {{"brand_sentiment": {{"score": <number>, "justification": "<string>"}}, "citation_propensity": {{"score": <number>, "justification": "<string>"}}}}
    """
    try:
        model_config = {
            "model": config.DEFAULT_FAST_MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}], **model_config
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        print(f"Error during GEO analysis: {e}")
        return {"error": "Failed to generate GEO analysis.", "details": str(e)}
