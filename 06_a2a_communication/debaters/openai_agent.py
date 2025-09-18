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
    print(f"\nSearching for: {query}\n")
    return await tavily_client.search(query, search_depth="basic", max_results=3)

# Agent Wrapper
class OpenAIAgent:
    """A wrapper for the OpenAI Agent."""
    def __init__(self, name: str, prompt: str):
        self.session_store = {}
        self.agent = Agent(
            name=name,
            instructions=prompt,
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
