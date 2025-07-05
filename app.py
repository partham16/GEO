import streamlit as st
import autogen
import json
import config  # Import our new config file

from groq import Groq
from tavily import TavilyClient
from pyvis.network import Network
from components.semantic_firewall import SemanticFirewall
from components.geo_analyzer import analyze_geo_content

# --- 1. CONFIGURATION & INITIALIZATION ---
st.set_page_config(layout="wide", page_title="Agentic Marketer's Suite")

# --- UI: Sidebar for configuration ---
with st.sidebar:
    st.title("Configuration")
    use_tavily_api = st.toggle("Use Live Tavily API", value=config.USE_TAVILY_API,
                               help="Turn on to use real Tavily search credits. When off, uses a pre-canned mock cache.")

    selected_model = st.selectbox(
        "Select Groq Model for Agents:",
        options=config.AVAILABLE_GROQ_MODELS,
        index=config.AVAILABLE_GROQ_MODELS.index(config.DEFAULT_CREATIVE_MODEL),
        help="Choose the primary LLM for content generation."
    )

    with st.expander("Agent System Prompts"):
        st.session_state.cmo_prompt = st.text_area(
            "CMO Prompt", value=config.AGENT_CONFIG["cmo"]["system_message"], height=150)
        st.session_state.strategist_prompt = st.text_area(
            "Strategist Prompt", value=config.AGENT_CONFIG["strategist"]["system_message"], height=150)
        st.session_state.copywriter_prompt = st.text_area(
            "Copywriter Prompt", value=config.AGENT_CONFIG["copywriter"]["system_message"], height=150)
        st.session_state.art_director_prompt = st.text_area(
            "Art Director Prompt", value=config.AGENT_CONFIG["art_director"]["system_message"], height=150)

    if config.GROQ_API_KEY and config.TAVILY_API_KEY:
        st.success("API keys loaded.")
    else:
        st.error("Missing API Keys in .env file!")
        st.stop()

# Initialize clients and components
try:
    groq_client = Groq(api_key=config.GROQ_API_KEY)
    tavily_client = TavilyClient(api_key=config.TAVILY_API_KEY)
    firewall = SemanticFirewall(groq_client, tavily_client)
except Exception as e:
    st.error(f"Failed to initialize clients: {e}")
    st.stop()

# Initialize Streamlit session state
if "results" not in st.session_state:
    st.session_state.results = []
if "agent_chat" not in st.session_state:
    st.session_state.agent_chat = []

# --- 2. AGENT & TOOL DEFINITION ---


def firewalled_tavily_search(query: str) -> str:
    firewall.use_live_api = use_tavily_api
    firewall_result = firewall.query(query)
    st.session_state.agent_chat.append(
        {"sender": "Firewall", "message": f"Status: {firewall_result['status']} for query: '{query}'"})
    if "error" in firewall_result["result"]:
        return f"Search failed: {firewall_result['result']['error']}"
    content = "\n".join([obj.get("content", "") for obj in firewall_result["result"].get('results', [])])
    return content if content else "No relevant content found."


creative_llm_config = {
    "config_list": [{"model": selected_model, "api_key": config.GROQ_API_KEY, "api_type": "groq"}],
    "temperature": 0.7
}

# Define Agents with updated prompts and configs
cmo_agent = autogen.AssistantAgent(name="ChiefMarketingOfficer", system_message=st.session_state.get(
    "cmo_prompt"), llm_config=creative_llm_config)
content_strategist_agent = autogen.AssistantAgent(
    name="ContentStrategist", system_message=st.session_state.get("strategist_prompt"), llm_config=creative_llm_config)
copywriter_agent = autogen.AssistantAgent(name="Copywriter", system_message=st.session_state.get(
    "copywriter_prompt"), llm_config=creative_llm_config)
art_director_agent = autogen.AssistantAgent(name="ArtDirector", system_message=st.session_state.get(
    "art_director_prompt"), llm_config=creative_llm_config)

# --- 3. SEQUENTIAL EXECUTION APPROACH ---


def execute_strategy_sequential(strategy: dict):
    """Executes a marketing strategy using sequential 1-on-1 agent chats."""
    with st.status(f"Executing Strategy: {strategy.get('title')}", expanded=True) as status:

        # Step 1: Content Strategist
        status.write("Step 1: Content Strategist researching...")
        strategist_proxy = autogen.UserProxyAgent(name="StrategistProxy", human_input_mode="NEVER", max_consecutive_auto_reply=5,
                                                  code_execution_config=False, is_termination_msg=lambda x: "FINAL OUTLINE:" in x.get("content", ""))
        strategist_proxy.register_function(function_map={"search": firewalled_tavily_search})
        strategist_prompt = f"Research and create a detailed outline for this strategy: {json.dumps(strategy, indent=2)}. Use the search tool. When done, respond with ONLY your outline prefixed with 'FINAL OUTLINE:'."

        try:
            strategist_proxy.initiate_chat(content_strategist_agent, message=strategist_prompt)
            strategist_messages = strategist_proxy.chat_messages.get(content_strategist_agent, [])
            st.session_state.agent_chat.extend(strategist_messages)
            outline = next((msg["content"].replace("FINAL OUTLINE:", "").strip() for msg in reversed(
                strategist_messages) if "FINAL OUTLINE:" in msg.get("content", "")), None)
            if not outline:
                return {"error": "Content Strategist failed to provide an outline."}
        except Exception as e:
            return {"error": f"Content Strategist failed: {str(e)}"}

        # Step 2: Copywriter
        status.write("Step 2: Copywriter creating content...")
        copywriter_proxy = autogen.UserProxyAgent(name="CopywriterProxy", human_input_mode="NEVER", max_consecutive_auto_reply=3,
                                                  code_execution_config=False, is_termination_msg=lambda x: "FINAL CONTENT:" in x.get("content", ""))
        copywriter_prompt = f"Based on this outline, write a compelling blog post:\n\n{outline}\n\nRespond with ONLY the blog post text prefixed with 'FINAL CONTENT:'."

        try:
            copywriter_proxy.initiate_chat(copywriter_agent, message=copywriter_prompt)
            copywriter_messages = copywriter_proxy.chat_messages.get(copywriter_agent, [])
            st.session_state.agent_chat.extend(copywriter_messages)
            final_content = next((msg["content"].replace("FINAL CONTENT:", "").strip() for msg in reversed(
                copywriter_messages) if "FINAL CONTENT:" in msg.get("content", "")), None)
            if not final_content:
                return {"error": "Copywriter failed to provide content."}
        except Exception as e:
            return {"error": f"Copywriter failed: {str(e)}"}

        # Step 3: Art Director
        status.write("Step 3: Art Director creating image prompts...")
        art_director_proxy = autogen.UserProxyAgent(name="ArtDirectorProxy", human_input_mode="NEVER", max_consecutive_auto_reply=3,
                                                    code_execution_config=False, is_termination_msg=lambda x: "FINAL ART DIRECTION:" in x.get("content", ""))
        art_director_prompt = f"Based on this blog post, create image prompts:\n\n{final_content[:1000]}...\n\nProvide 1-2 detailed image generation prompts in JSON format. Respond with ONLY the JSON prefixed with 'FINAL ART DIRECTION:'."

        try:
            art_director_proxy.initiate_chat(art_director_agent, message=art_director_prompt)
            art_director_messages = art_director_proxy.chat_messages.get(art_director_agent, [])
            st.session_state.agent_chat.extend(art_director_messages)
            art_direction = next((msg["content"].replace("FINAL ART DIRECTION:", "").strip() for msg in reversed(
                art_director_messages) if "FINAL ART DIRECTION:" in msg.get("content", "")), '{"error": "Could not generate art direction."}')
        except Exception as e:
            st.warning(f"Art Director failed: {e}")
            art_direction = '{"error": "Art Director agent failed."}'

        # Step 4: GEO Analysis
        status.write("Step 4: Analyzing GEO score...")
        geo_scores = analyze_geo_content(final_content, groq_client, debug_mode=not use_tavily_api)

        status.update(label="Complete!", state="complete", expanded=False)
        return {"title": strategy.get("title"), "content": final_content, "art": art_direction, "geo": geo_scores}

# --- 4. STREAMLIT UI & MAIN LOGIC ---


def generate_strategies():
    st.session_state.results = []
    st.session_state.agent_chat = []

    with st.spinner("CMO Agent is generating strategies..."):
        cmo_user_proxy = autogen.UserProxyAgent(
            name="CMO_User_Proxy",
            human_input_mode="NEVER",
            is_termination_msg=lambda x: "]" in x.get("content", ""),
            max_consecutive_auto_reply=2,
            code_execution_config=False
        )
        cmo_user_proxy.initiate_chat(
            cmo_agent, message=f"Generate content strategies for the topic: {st.session_state.user_input}")
        cmo_response = cmo_user_proxy.last_message()["content"]
        st.session_state.agent_chat.extend(cmo_user_proxy.chat_messages.get(cmo_agent, []))

    try:
        json_response_str = cmo_response[cmo_response.find("["): cmo_response.rfind("]") + 1]
        st.session_state.strategies = json.loads(json_response_str)
    except (json.JSONDecodeError, TypeError):
        st.error("The CMO agent did not return a valid JSON list. Please try again.")
        st.code(cmo_response)
        st.session_state.strategies = None


st.title("Agentic Marketer's Suite")
st.text_input("Enter a simple topic (e.g., 'best car to buy'):", "best photographer in berlin", key="user_input")

if st.button("Generate Content Strategy", type="primary"):
    generate_strategies()

if "strategies" in st.session_state and st.session_state.strategies:
    st.subheader("Step 2: Choose a Strategy to Execute")

    if st.button("🔄 Regenerate Strategies"):
        generate_strategies()
        st.rerun()

    strategy_titles = [s.get("title", f"Strategy {i + 1}") for i, s in enumerate(st.session_state.strategies)]
    selected_strategy_title = st.radio("Select a single strategy:", strategy_titles,
                                       horizontal=True, label_visibility="collapsed")

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("Execute Selected Strategy"):
            selected_strategy = next(s for s in st.session_state.strategies if s.get("title")
                                     == selected_strategy_title)
            result = execute_strategy_sequential(selected_strategy)
            st.session_state.results = [result]
            st.rerun()
    with col2:
        if st.button("Execute All Strategies", type="secondary"):
            all_results = []
            for strategy in st.session_state.strategies:
                result = execute_strategy_sequential(strategy)
                all_results.append(result)
            st.session_state.results = all_results
            st.rerun()

# --- 5. DISPLAY RESULTS ---
if st.session_state.results:
    st.success("Content generation and analysis complete!")

    for result in st.session_state.results:
        with st.expander(f"Results for: {result.get('title', 'Untitled Strategy')}", expanded=True):
            if "error" in result:
                st.error(result["error"])
                continue

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Final Content")
                st.text_area("Generated Blog Post", result["content"], height=300, key=f"content_{result['title']}")
                st.subheader("Art Direction")
                st.code(result["art"], language="json")
            with col2:
                st.subheader("Pre-flight GEO Analysis")
                if "error" not in result["geo"]:
                    for key, value in result["geo"].items():
                        st.metric(label=key.replace('_', ' ').title(),
                                  value=f"{value['score']}/10", key=f"geo_{key}_{result['title']}")
                        st.caption(value['justification'])
                else:
                    st.error(f"GEO Analysis Failed: {result['geo']['details']}")

    st.subheader("Performance & Logs")
    tab1, tab2 = st.tabs(["Logic Path", "Firewall Cache"])
    with tab1:
        try:
            net = Network(height="500px", width="100%", bgcolor="#222222",
                          font_color="white", notebook=True, cdn_resources='in_line')
            senders = set()
            for msg in st.session_state.agent_chat:
                sender = msg.get("name", msg.get("sender", "System"))
                if sender not in senders:
                    net.add_node(sender, label=sender, title=sender)
                    senders.add(sender)
            for i in range(len(st.session_state.agent_chat) - 1):
                source = st.session_state.agent_chat[i].get("name", "System")
                target = st.session_state.agent_chat[i + 1].get("name", "System")
                if source != target:
                    net.add_edge(source, target)
            net.save_graph("logic_path.html")
            st.components.v1.html(open("logic_path.html", "r").read(), height=510)
        except Exception as e:
            st.error(f"Could not generate logic path: {e}")
    with tab2:
        st.json(firewall.cache)

    with st.expander("View Full Agent Conversation Log"):
        st.json(st.session_state.agent_chat)
