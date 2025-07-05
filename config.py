import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- Global Settings ---
# This toggle specifically controls the use of the limited Tavily API.
# When False, the SemanticFirewall will use the MOCK_TAVILY_CACHE below.
USE_TAVILY_API = False 

# --- Mock Data Cache ---
# Pre-canned search results for offline development to save Tavily credits.
# This format now mirrors the real Tavily API response structure.
MOCK_TAVILY_CACHE = {
    "what do couples regret about their wedding photos reddit": {
        "query": "what do couples regret about their wedding photos reddit",
        "results": [
            {"title": "Reddit - r/weddingplanning - What do you regret?", "url": "https://www.reddit.com/r/weddingplanning/comments/12345", "content": "A common regret is not getting enough candid shots of guests. People look back and wish they had more photos of their friends and family just enjoying the day. Many users on r/weddingplanning wish they had hired a second shooter to capture more moments naturally.", "score": 0.98},
            {"title": "Reddit - Top Wedding Photo Regrets", "url": "https://www.reddit.com/r/photography/comments/67890", "content": "The biggest regret mentioned is not doing a 'first look' session. The day goes by so fast, and that quiet moment is often missed. Also, not getting detailed shots of the decor and rings.", "score": 0.95}
        ]
    },
    "unique berlin wedding photo locations not brandenburg gate": {
        "query": "unique berlin wedding photo locations not brandenburg gate",
        "results": [
            {"title": "Berlin's Hidden Gems for Wedding Photos - A Local's Guide", "url": "https://www.localberliner.de/photos", "content": "For truly unique Berlin photo locations, consider the Teufelsberg listening station for an edgy, post-apocalyptic vibe. The Landwehr Canal offers romantic, waterside shots, especially in autumn. For an industrial-chic aesthetic, the RAW-Gelände in Friedrichshain is unmatched.", "score": 0.99}
        ]
    },
    "surprising wedding photography statistics 2025": {
        "query": "surprising wedding photography statistics 2025",
        "results": [
            {"title": "Brides Magazine - 2025 Wedding Trends Report", "url": "https://www.brides.com/2025-trends", "content": "Our latest study shows a massive shift in preferences. Over 70% of couples now prefer a candid, documentary style over traditional posed photos. Another surprising fact is that 'unplugged' wedding ceremonies are on the rise, with 40% of couples asking guests to put away their phones during the ceremony to be fully present.", "score": 0.97}
        ]
    },
    "hidden costs of car ownership germany": {
        "query": "hidden costs of car ownership germany",
        "results": [
            {"title": "Understanding the True Cost of a Car in Germany - ADAC", "url": "https://www.adac.de/kosten", "content": "Beyond insurance and fuel, German car owners must budget for the mandatory technical inspection ('TÜV') every two years, which can lead to expensive repairs. Furthermore, the vehicle tax (Kfz-Steuer) is based on engine size and CO2 emissions. High costs for specific replacement parts like modern LED headlights and significant depreciation on new models are also major factors.", "score": 0.99}
        ]
    }
}


# --- Model Configurations ---
LLM_CONFIG_FAST = {
    "model": "llama3-8b-8192",
    "temperature": 0,
    "response_format": {"type": "json_object"},
}

LLM_CONFIG_CREATIVE = {
    "model": "llama3-70b-8192",
    "temperature": 0.7,
}

# --- Agent Configurations ---
# Default system messages that can be overridden in the Streamlit UI
AGENT_CONFIG = {
    "cmo": {
        "system_message": "You are a Chief Marketing Officer. Your job is to take a simple user query and transform it into 2-3 distinct, actionable content strategies. For each strategy, define a clear title, target audience, and a unique angle. Respond with a JSON list of these strategies.",
    },
    "strategist": {
        "system_message": "You are a Content Strategist. Your job is to take a strategic brief, perform detailed research using the search tool, find a unique angle and a surprising statistic, and create a final, detailed outline for the copywriter.",
    },
    "copywriter": {
        "system_message": "You are a Copywriter. Your job is to take a detailed outline and write a compelling, well-structured blog post.",
    },
    "art_director": {
        "system_message": "You are an Art Director. Your job is to read the final blog post and suggest 1-2 impactful images. For each, provide a detailed image generation prompt.",
    }
}

# --- Component Configurations ---
FIREWALL_CONFIG = {
    "similarity_model": LLM_CONFIG_FAST
}

GEO_ANALYZER_CONFIG = {
    "analysis_model": LLM_CONFIG_FAST
}

def get_llm_config(client: any):
    """Helper function to inject the Groq client into model configs."""
    from copy import deepcopy
    
    creative_config = deepcopy(LLM_CONFIG_CREATIVE)
    creative_config["client"] = client

    fast_config = deepcopy(LLM_CONFIG_FAST)
    fast_config["client"] = client

    return creative_config, fast_config
