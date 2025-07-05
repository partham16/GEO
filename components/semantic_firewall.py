import json
from groq import Groq
from tavily import TavilyClient
from typing import Dict, Any, Tuple
import config  # Import the global config


class SemanticFirewall:
    """A smart caching layer that uses settings from the global config."""

    def __init__(self, groq_client: Groq, tavily_client: TavilyClient):
        self.cache: Dict[str, Any] = {}
        self.groq_client = groq_client
        self.tavily_client = tavily_client
        print(f"Semantic Firewall Initialized. Using Tavily API: {config.USE_TAVILY_API}")

    def _check_similarity(self, new_query: str) -> Tuple[bool, str | None]:
        if not self.cache:
            return False, None

        cached_queries = list(self.cache.keys())
        cached_queries_str = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(cached_queries))
        prompt = f"""Is the "NEW QUERY" semantically equivalent to any "PREVIOUS QUERIES"? Respond ONLY with JSON: {{"similar": "YES" or "NO", "match_index": "number" or "null"}}.
        PREVIOUS QUERIES:\n{cached_queries_str}\n\nNEW QUERY:\n"{new_query}" """

        try:
            model_config = config.FIREWALL_CONFIG["similarity_model"]
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}], **model_config
            )
            response_json = json.loads(chat_completion.choices[0].message.content)

            if response_json.get("similar") == "YES":
                match_index = int(response_json.get("match_index")) - 1
                if 0 <= match_index < len(cached_queries):
                    return True, cached_queries[match_index]
            return False, None
        except Exception as e:
            print(f"Error during similarity check: {e}")
            return False, None

    def query(self, query: str) -> Dict[str, Any]:
        is_hit, matched_query = self._check_similarity(query)

        if is_hit and matched_query:
            print(f"[Firewall] CACHE HIT! Query '{query}' is similar to '{matched_query}'.")
            return {"result": self.cache[matched_query], "status": "HIT"}
        else:
            print(f"[Firewall] CACHE MISS for query: '{query}'.")

            if not config.USE_TAVILY_API:
                if query in config.MOCK_TAVILY_CACHE:
                    print("[Firewall] Found query in MOCK_TAVILY_CACHE.")
                    result = config.MOCK_TAVILY_CACHE[query]
                else:
                    result = {"query": query, "results": [
                        {"title": "Mock Result", "content": f"This is a generic mock search result for '{query}' because it was not found in the pre-canned cache.", "url": ""}]}
            else:
                try:
                    print("[Firewall] Calling real Tavily API...")
                    result = self.tavily_client.search(query=query, search_depth="advanced")
                except Exception as e:
                    result = {"query": query, "results": [], "error": f"Tavily search failed: {e}"}

            self.cache[query] = result
            return {"result": result, "status": "MISS"}
