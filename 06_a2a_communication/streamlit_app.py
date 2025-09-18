import asyncio
import httpx
from uuid import uuid4
import streamlit as st

from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import Message, Part, Role, TextPart, TransportProtocol, Task

# Agent URLs
LANGGRAPH_AGENT_URL = "http://localhost:10006"
OPENAI_AGENT_URL = "http://localhost:10007"

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        color: white;
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        margin: 0;
        font-size: 2.5rem;
    }
    
    .main-header p {
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin: 0.5rem 0 0 0;
    }
    

</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
async def get_a2a_client(http_client: httpx.AsyncClient, agent_url: str) -> Client:
    config = ClientConfig(streaming=False, supported_transports=[TransportProtocol.jsonrpc])
    factory = ClientFactory(config)
    card_resolver = A2ACardResolver(http_client, agent_url)
    agent_card = await card_resolver.get_agent_card()
    return factory.create(agent_card)


async def send_message_and_get_response(client: Client, message_text: str, context_id: str) -> str:
    user_message = Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=message_text))],
        message_id=str(uuid4()),
        context_id=context_id,
    )

    final_task_object = None
    async for event in client.send_message(request=user_message):
        if isinstance(event, tuple):
            final_task_object = event[0]
        else:
            final_task_object = event

    if isinstance(final_task_object, Task) and final_task_object.artifacts:
        return final_task_object.artifacts[0].parts[0].root.text
    
    return "Error: Agent did not provide a valid response."


def render_agent_card(card, gradient_colors: tuple[str, str]):
    """Render a styled agent card with gradient background."""
    gradient_css = f"linear-gradient(135deg, {gradient_colors[0]}, {gradient_colors[1]})"
    skills_html = "".join([f"<li>{s.name}</li>" for s in card.skills])

    st.markdown(
        f"""
        <div style="padding:18px; border-radius:14px; 
                    background: {gradient_css};
                    color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
            <h3 style="margin:0;">{card.name}</h3>
            <p style="margin:4px 0;"><b>Description:</b> {card.description}</p>
            <p style="margin:4px 0;"><b>URL:</b> {card.url}</p>
            <p style="margin:4px 0;"><b>Version:</b> {card.version}</p>
            <p style="margin:4px 0;"><b>Input Modes:</b> {", ".join(card.default_input_modes)}</p>
            <p style="margin:4px 0;"><b>Output Modes:</b> {", ".join(card.default_output_modes)}</p>
            <p style="margin:4px 0;"><b>Skills:</b></p>
            <ul style="margin-top:0; margin-bottom:0;">
                {skills_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


# --- Streamlit UI ---
st.set_page_config(page_title="AI Agents Debate", layout="wide")

st.sidebar.header("Debate Settings")
debate_topic = st.sidebar.text_input(
    "Debate Topic",
    placeholder="e.g. Is time travel possible?"
)
debate_turns = st.sidebar.number_input("Number of Turns", min_value=1, max_value=10, value=5, help="The number of times each agent will speak")

tabs = st.tabs(["Agent Cards", "Debate Chat"])

# Session state for storing agents
for key in ["langgraph_client", "openai_client", "langgraph_card", "openai_card"]:
    if key not in st.session_state:
        st.session_state[key] = None


# --- Tab 1: Agent Cards ---
with tabs[0]:
    # Page Header
    st.markdown("""
    <div class="main-header">
        <h1>🤖 AI Agents Debate Arena</h1>
        <p>Watch intelligent agents engage in debates on diverse topics</p>
    </div>
    """, unsafe_allow_html=True)
    
    fetch_button = st.button("Fetch Agent Cards", use_container_width=True)

    if fetch_button:
        async def fetch_cards():
            async with httpx.AsyncClient(timeout=240.0) as async_client:
                lg_client, oa_client = await asyncio.gather(
                    get_a2a_client(async_client, LANGGRAPH_AGENT_URL),
                    get_a2a_client(async_client, OPENAI_AGENT_URL),
                )
                st.session_state.langgraph_client = lg_client
                st.session_state.openai_client = oa_client
                st.session_state.langgraph_card = await lg_client.get_card()
                st.session_state.openai_card = await oa_client.get_card()

        asyncio.run(fetch_cards())

    if st.session_state.langgraph_card and st.session_state.openai_card:
        cols = st.columns(2)
        with cols[0]:
            render_agent_card(st.session_state.langgraph_card, ("#1674f0", "#388dfc"))  # Blue gradient
        with cols[1]:
            render_agent_card(st.session_state.openai_card, ("#8a0030", "#bd1a53"))  # Red gradient


# --- Tab 2: Debate Chat ---
with tabs[1]:
    st.subheader("Debate")
    start_button = st.button("Start Debate", use_container_width=True)

    async def run_debate():
        langgraph_client = st.session_state.langgraph_client
        openai_client = st.session_state.openai_client
        langgraph_agent_card = st.session_state.langgraph_card
        openai_agent_card = st.session_state.openai_card

        if not (langgraph_client and openai_client):
            st.warning("Please fetch agent cards first in the Agent Cards tab.")
            return

        debate_id = f"debate-{uuid4()}"
        current_speaker_name = langgraph_agent_card.name
        current_speaker_client = langgraph_client
        current_message = f"Let's debate the topic: {debate_topic}."

        for i in range(debate_turns * 2):
            response = await send_message_and_get_response(
                current_speaker_client, current_message, debate_id
            )

            with st.chat_message(current_speaker_name):
                st.markdown(f"**{current_speaker_name} (Turn {i+1}):** {response}")

            current_message = response
            if current_speaker_name == langgraph_agent_card.name:
                current_speaker_name = openai_agent_card.name
                current_speaker_client = openai_client
            else:
                current_speaker_name = langgraph_agent_card.name
                current_speaker_client = langgraph_client

    if start_button:
        asyncio.run(run_debate())