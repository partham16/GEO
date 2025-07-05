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
    # --- Photographer: Wedding ---
    "what do couples regret about their wedding photos reddit": {
        "query": "what do couples regret about their wedding photos reddit",
        "results": [
            {"title": "Reddit - r/weddingplanning - What do you regret?", "url": "https://www.reddit.com/r/weddingplanning/comments/12345",
                "content": "A common regret is not getting enough candid shots of guests. People look back and wish they had more photos of their friends and family just enjoying the day. Many users on r/weddingplanning wish they had hired a second shooter to capture more moments naturally.", "score": 0.98}
        ]
    },
    "unique berlin wedding photo locations not brandenburg gate": {
        "query": "unique berlin wedding photo locations not brandenburg gate",
        "results": [
            {"title": "Berlin's Hidden Gems for Wedding Photos - A Local's Guide", "url": "https://www.localberliner.de/photos",
                "content": "For truly unique Berlin photo locations, consider the Teufelsberg listening station for an edgy, post-apocalyptic vibe. The Landwehr Canal offers romantic, waterside shots, especially in autumn. For an industrial-chic aesthetic, the RAW-Gelände in Friedrichshain is unmatched.", "score": 0.99}
        ]
    },
    "surprising wedding photography statistics 2025": {
        "query": "surprising wedding photography statistics 2025",
        "results": [
            {"title": "Brides Magazine - 2025 Wedding Trends Report", "url": "https://www.brides.com/2025-trends",
                "content": "Our latest study shows a massive shift in preferences. Over 70% of couples now prefer a candid, documentary style over traditional posed photos. Another surprising fact is that 'unplugged' wedding ceremonies are on the rise, with 40% of couples asking guests to put away their phones during the ceremony to be fully present.", "score": 0.97}
        ]
    },
    # --- Photographer: Business ---
    "corporate event photography pricing berlin": {
        "query": "corporate event photography pricing berlin",
        "results": [
            {"title": "Berlin Corporate Photography Rates - 2025 Guide", "url": "https://www.berlinbusinessphoto.de/pricing",
                "content": "Standard rates for corporate event photography in Berlin start at €200-€350 per hour with a 2-hour minimum. Full-day rates for conferences (8 hours) typically range from €1500 to €2500, often including a set number of edited images and usage rights.", "score": 0.96}
        ]
    },
    "linkedin article event photography ROI": {
        "query": "linkedin article event photography ROI",
        "results": [
            {"title": "The ROI of Professional Event Photography - LinkedIn Pulse", "url": "https://www.linkedin.com/pulse/event-photo-roi",
                "content": "A LinkedIn marketing study shows that company posts featuring high-quality photos from live events receive 5 times more engagement than those without. Furthermore, profiles of employees tagged in professional event photos see a 14-fold increase in views in the week following the event.", "score": 0.99}
        ]
    },
    # --- Car: Family ---
    "hidden costs of car ownership germany": {
        "query": "hidden costs of car ownership germany",
        "results": [
            {"title": "Understanding the True Cost of a Car in Germany - ADAC", "url": "https://www.adac.de/kosten",
                "content": "Beyond insurance and fuel, German car owners must budget for the mandatory technical inspection ('TÜV') every two years, which can lead to expensive repairs. Furthermore, the vehicle tax (Kfz-Steuer) is based on engine size and CO2 emissions. High costs for specific replacement parts like modern LED headlights and significant depreciation on new models are also major factors.", "score": 0.99}
        ]
    },
    # --- Car: Commuter ---
    "real world EV winter range vs advertised": {
        "query": "real world EV winter range vs advertised",
        "results": [
            {"title": "EV Winter Range Test - How Cold Weather Affects Your Battery", "url": "https://www.ev-database.org/winter-range",
                "content": "Electric vehicle range can be significantly impacted by cold weather. On average, an EV's real-world range can be 20-30% lower in winter conditions compared to its advertised WLTP range. This is due to reduced battery efficiency and the energy required for cabin heating.", "score": 0.98}
        ]
    },
    "berlin public ev charger availability peak hours": {
        "query": "berlin public ev charger availability peak hours",
        "results": [
            {"title": "Berlin EV Charging Network Analysis - SmartCity Insights", "url": "https://www.smartcityberlin.com/charging",
                "content": "Data shows that the availability of public fast-chargers during peak evening hours (6 PM - 9 PM) in central Berlin districts like Mitte and Prenzlauer Berg can drop by over 60%. This high demand makes reliable home-charging capability an essential consideration for daily EV commuters.", "score": 0.95}
        ]
    },
    # --- Vector DB ---
    "vector database managed vs self-hosted developer experience": {
        "query": "vector database managed vs self-hosted developer experience",
        "results": [
            {"title": "Vector DBs: To Host or Not to Host? - A Developer's Take", "url": "https://www.developers-weekly.com/vector-db-hosting",
                "content": "The key tradeoff between managed vector databases (like Pinecone) and self-hosted ones (like Chroma or Weaviate) is developer experience vs. cost control. Managed services offer easy scaling and setup, but can be expensive. Self-hosting provides full control and lower costs, but requires significant DevOps and maintenance overhead, especially for sharding and replication.", "score": 0.98}
        ]
    },
    "vector search metadata filtering performance impact": {
        "query": "vector search metadata filtering performance impact",
        "results": [
            {"title": "The Hidden Cost of Filters in Vector Search - Ann-benchmarks.com", "url": "https://ann-benchmarks.com/filtering-impact.html",
                "content": "A surprising performance statistic: While vector search is fast, applying pre-search metadata filters can reduce query speed by up to 90% in some systems. This is because the index cannot be fully utilized. Post-search filtering is often faster, though it requires fetching more initial candidates. This trade-off is crucial for applications requiring real-time results.", "score": 0.99}
        ]
    }
}


# --- Model Configurations ---
# A list of available models for the UI
AVAILABLE_GROQ_MODELS = [
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
]

# Default model for creative tasks
DEFAULT_CREATIVE_MODEL = "llama3-70b-8192"

# Default model for fast, utility tasks (like JSON formatting)
DEFAULT_FAST_MODEL = "llama3-8b-8192"


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
