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

    st.session_state.selected_model = st.selectbox(
        "Select Groq Model for Agents:",
        options=config.AVAILABLE_GROQ_MODELS,
        index=config.AVAILABLE_GROQ_MODELS.index(config.DEFAULT_CREATIVE_MODEL),
        help="Choose the primary LLM for content generation."
    )

    human_input_mode = st.selectbox(
        "Human Intervention Mode:",
        options=["NEVER", "TERMINATE"],
        index=0,  # Default to NEVER for autonomous operation
        help="NEVER: Fully autonomous. TERMINATE: If agents get stuck, you can provide input in the terminal."
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
    firewall_result = firewall.query(query)
    st.session_state.agent_chat.append(
        {"sender": "Firewall", "message": f"Status: {firewall_result['status']} for query: '{query}'"})
    if "error" in firewall_result["result"]:
        return f"Search failed: {firewall_result['result']['error']}"
    content = "\n".join([obj.get("content", "") for obj in firewall_result["result"].get('results', [])])
    return content


creative_llm_config = {
    "config_list": [{"model": st.session_state.selected_model, "api_key": config.GROQ_API_KEY, "api_type": "groq"}],
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
group_chat_user_proxy = autogen.UserProxyAgent(
    name="MarketingManager",
    human_input_mode=human_input_mode,
    max_consecutive_auto_reply=10,
    code_execution_config=False,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE")
)
group_chat_user_proxy.register_function(function_map={"search": firewalled_tavily_search})

# --- 3. HELPER FUNCTION FOR RUNNING A STRATEGY ---


def execute_strategy(strategy: dict):
    with st.status(f"Executing Strategy: {strategy.get('title')}", expanded=True) as status:
        status.write("Orchestrating agent workflow...")
        groupchat = autogen.GroupChat(agents=[group_chat_user_proxy, content_strategist_agent,
                                      copywriter_agent, art_director_agent], messages=[], max_round=15)
        manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=creative_llm_config)

        project_plan_prompt = f"""
        Team, execute the following strategy: {json.dumps(strategy, indent=2)}
        Plan:
        1.  ContentStrategist: Research using 'search' tool and create a detailed outline. Your final message MUST be ONLY the outline, prefixed with "FINAL OUTLINE:".
        2.  Copywriter: Take the outline and write the blog post. Your final message MUST be ONLY the text, prefixed with "FINAL CONTENT:".
        3.  ArtDirector: Read the final content and provide image prompts. Your final message MUST be ONLY JSON, prefixed with "FINAL ART DIRECTION:". Then, you must write the word TERMINATE on a new line.
        ContentStrategist, begin.
        """
        group_chat_user_proxy.initiate_chat(manager, message=project_plan_prompt)

        chat_history = groupchat.messages
        st.session_state.agent_chat.extend(chat_history)

        status.update(label="Parsing final results...", state="running")
        final_content = next((msg["content"].replace("FINAL CONTENT:", "").strip() for msg in reversed(chat_history) if msg.get(
            "name") == "Copywriter" and msg.get("content", "").strip().startswith("FINAL CONTENT:")), None)
        art_direction = next((msg["content"].replace("FINAL ART DIRECTION:", "").strip().replace("TERMINATE", "") for msg in reversed(
            chat_history) if msg.get("name") == "ArtDirector" and msg.get("content", "").strip().startswith("FINAL ART DIRECTION:")), None)

        if not final_content or not art_direction:
            return {"error": "Workflow failed to generate all required outputs."}

        status.update(label="Analyzing GEO score...", state="running")
        geo_scores = analyze_geo_content(final_content, groq_client)

        status.update(label="Complete!", state="complete", expanded=False)
        return {"title": strategy.get("title"), "content": final_content, "art": art_direction, "geo": geo_scores}


# --- 4. STREAMLIT UI & MAIN LOGIC ---
st.title("Agentic Marketer's Suite")
user_input = st.text_input("Enter a simple topic (e.g., 'best car to buy'):", "best photographer in berlin")

if st.button("Generate Content Strategy", type="primary"):
    st.session_state.results = []
    st.session_state.agent_chat = []

    with st.spinner("CMO Agent is generating strategies..."):
        cmo_user_proxy = autogen.UserProxyAgent(name="CMO_User_Proxy", human_input_mode="NEVER", is_termination_msg=lambda x: x.get(
            "content", "").strip().endswith("]"), max_consecutive_auto_reply=2)
        cmo_user_proxy.initiate_chat(cmo_agent, message=f"Generate content strategies for the topic: {user_input}")
        cmo_response = cmo_user_proxy.last_message()["content"]
        st.session_state.agent_chat.extend(cmo_user_proxy.chat_messages[cmo_agent])

    try:
        json_response_str = cmo_response[cmo_response.find("["): cmo_response.rfind("]") + 1]
        st.session_state.strategies = json.loads(json_response_str)
    except (json.JSONDecodeError, TypeError):
        st.error("The CMO agent did not return a valid JSON list. Please try again.")
        st.code(cmo_response)
        st.stop()

if "strategies" in st.session_state:
    st.subheader("Step 2: Choose a Strategy to Execute")
    col1, col2 = st.columns([3, 1])
    with col1:
        strategy_titles = [s.get("title", f"Strategy {i + 1}") for i, s in enumerate(st.session_state.strategies)]
        selected_strategy_title = st.radio("Select a single strategy:", strategy_titles,
                                           horizontal=True, label_visibility="collapsed")
    with col2:
        if st.button("Execute Selected Strategy"):
            selected_strategy = next(s for s in st.session_state.strategies if s.get("title")
                                     == selected_strategy_title)
            result = execute_strategy(selected_strategy)
            st.session_state.results = [result]  # Store as a list
            st.rerun()

        if st.button("Execute All Strategies", type="primary"):
            all_results = []
            for strategy in st.session_state.strategies:
                result = execute_strategy(strategy)
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
