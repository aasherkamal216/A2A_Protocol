import os
from dotenv import load_dotenv

# OpenAI Agents SDK imports
from agents import Agent, Runner, SQLiteSession, function_tool, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel

from tavily import AsyncTavilyClient

_ = load_dotenv()

# Disable OpenAI tracing
set_tracing_disabled(True)

tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Tool for web search
@function_tool
async def search(query: str) -> str:
    """
    Searches the web for the given query.
    Args:
        query (str): The query to search for.
    """
    print(f"\n[NEWTON] Searching for: {query}\n")
    return await tavily_client.search(query, search_depth="basic", max_results=3)

# Agent prompt
NEWTON_PROMPT = """
You are Isaac Newton, the 17th-century natural philosopher. Today you have to debate with Albert Einstein on a topic.

## INSTRUCTIONS
- Present yourself with confidence, authority, and intellectual pride. 
- Defend your worldview using logical reasoning, mathematical rigor, and references to natural philosophy. 
- Use rhetorical strategies such as questioning Einstein's assumptions, pointing out contradictions, and demanding clarity. 
- Taunt sharply, exposing weaknesses in his reasoning while maintaining a sense of superiority. 
- Structure your arguments step by step, leading your opponent into logical traps. 
- Never concede easily; insist that your system is consistent and complete. 

## TONE & STYLE
- Use short and concise sentences
- Avoid complex vocabulary, use simple words

## WEB SEARCH
- Use the `search` tool if you need to strengthen your arguments with references.
"""

# Agent Wrapper
class NewtonAgent:
    """A wrapper for the OpenAI Agent."""
    def __init__(self):
        self.session_store = {}
        self.agent = Agent(
            name="Isaac Newton Agent",
            instructions=NEWTON_PROMPT,
            model=LitellmModel(model="gemini/gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY")),
            tools=[search],
        )

    def _get_session(self, session_id: str) -> SQLiteSession:
        """Gets or creates a session for a given ID."""
        if session_id not in self.session_store:
            # Using a unique in-memory database for each session
            self.session_store[session_id] = SQLiteSession(session_id=session_id)
        return self.session_store[session_id]

    async def run(self, query: str, session_id: str):
        """Runs the agent and returns the final output."""
        session = self._get_session(session_id)
        result = await Runner.run(self.agent, query, session=session)
        return result.final_output
