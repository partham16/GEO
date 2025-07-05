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
    config.USE_TAVILY_API = st.toggle("Use Live Tavily API", value=config.USE_TAVILY_API,
                                      help="Turn on to use real Tavily search credits. When off, uses a pre-canned mock cache.")

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
    creative_llm_config, _ = config.get_llm_config(groq_client)
except Exception as e:
    st.error(f"Failed to initialize clients: {e}")
    st.stop()

# Initialize Streamlit session state
if "results" not in st.session_state:
    st.session_state.results = None
if "agent_chat" not in st.session_state:
    st.session_state.agent_chat = []

# --- 2. AGENT & TOOL DEFINITION ---


def firewalled_tavily_search(query: str) -> str:
    firewall_result = firewall.query(query)
    st.session_state.agent_chat.append(
        {"sender": "Firewall", "message": f"Status: {firewall_result['status']} for query: {query}"})

    # Handle the new data structure for both mock and real results
    if "error" in firewall_result["result"]:
        return f"Search failed: {firewall_result['result']['error']}"

    # Extract and concatenate content from the 'results' list
    content = "\n".join([obj.get("content", "") for obj in firewall_result["result"].get('results', [])])
    return content


# Define AutoGen Agents using settings from UI or config
cmo_agent = autogen.AssistantAgent(name="ChiefMarketingOfficer", system_message=st.session_state.get(
    "cmo_prompt", config.AGENT_CONFIG["cmo"]["system_message"]), llm_config=creative_llm_config)
content_strategist_agent = autogen.AssistantAgent(name="ContentStrategist", system_message=st.session_state.get(
    "strategist_prompt", config.AGENT_CONFIG["strategist"]["system_message"]), llm_config=creative_llm_config)
copywriter_agent = autogen.AssistantAgent(name="Copywriter", system_message=st.session_state.get(
    "copywriter_prompt", config.AGENT_CONFIG["copywriter"]["system_message"]), llm_config=creative_llm_config)
art_director_agent = autogen.AssistantAgent(name="ArtDirector", system_message=st.session_state.get(
    "art_director_prompt", config.AGENT_CONFIG["art_director"]["system_message"]), llm_config=creative_llm_config)
user_proxy = autogen.UserProxyAgent(name="MarketingManager", human_input_mode="NEVER",
                                    max_consecutive_auto_reply=10, code_execution_config=False)
user_proxy.register_function(function_map={"search": firewalled_tavily_search})

# --- 3. STREAMLIT UI & MAIN LOGIC ---
st.title("Agentic Marketer's Suite")
user_input = st.text_input("Enter a simple topic (e.g., 'best car to buy'):", "best photographer in berlin")

if st.button("Generate Content Strategy", type="primary"):
    st.session_state.results = None
    st.session_state.agent_chat = []

    with st.spinner("CMO Agent is generating strategies..."):
        user_proxy.initiate_chat(cmo_agent, message=f"Generate content strategies for the topic: {user_input}")
        cmo_response = user_proxy.last_message()["content"]

    try:
        st.session_state.strategies = json.loads(cmo_response)
    except (json.JSONDecodeError, TypeError):
        st.error("The CMO agent did not return a valid JSON list. Please try again.")
        st.code(cmo_response)
        st.stop()

if "strategies" in st.session_state:
    strategy_titles = [s.get("title", f"Strategy {i + 1}") for i, s in enumerate(st.session_state.strategies)]
    selected_strategy_title = st.radio("Select a strategy to execute:", strategy_titles, horizontal=True)

    if st.button("Execute Selected Strategy"):
        selected_strategy = next(s for s in st.session_state.strategies if s.get("title") == selected_strategy_title)

        with st.spinner("Agent team at work... This may take a moment."):
            groupchat = autogen.GroupChat(agents=[user_proxy, content_strategist_agent,
                                          copywriter_agent, art_director_agent], messages=[], max_round=15)
            manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=creative_llm_config)
            strategist_prompt = f"Execute the following strategic brief:\n{json.dumps(selected_strategy, indent=2)}\n\nYour task: 1. Research using the 'search' tool. 2. Create a detailed outline. 3. Pass the outline to the copywriter."
            user_proxy.initiate_chat(manager, message=strategist_prompt)

            chat_history = groupchat.messages
            st.session_state.agent_chat.extend(chat_history)

            final_content = next((msg["content"] for msg in reversed(chat_history) if msg.get(
                "name") == "Copywriter" and msg.get("content")), "Content not found.")
            art_direction = next((msg["content"] for msg in reversed(chat_history) if msg.get(
                "name") == "ArtDirector" and msg.get("content")), "Art direction not found.")

            with st.spinner("Analyzing final content for GEO score..."):
                geo_scores = analyze_geo_content(final_content, groq_client)

            st.session_state.results = {"content": final_content, "art": art_direction,
                                        "geo": geo_scores, "firewall_cache": firewall.cache}
            st.rerun()

# --- 4. DISPLAY RESULTS ---
if st.session_state.results:
    st.success("Content generation and analysis complete!")
    results = st.session_state.results

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Final Content")
        st.text_area("Generated Blog Post", results["content"], height=400)
        st.subheader("Art Direction")
        st.code(results["art"], language="json")

    with col2:
        st.subheader("Pre-flight GEO Analysis")
        if "error" not in results["geo"]:
            for key, value in results["geo"].items():
                st.metric(label=key.replace('_', ' ').title(), value=f"{value['score']}/10")
                st.caption(value['justification'])
        else:
            st.error(f"GEO Analysis Failed: {results['geo']['details']}")

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
        st.json(results["firewall_cache"])
