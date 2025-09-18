import os

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver

from tavily import AsyncTavilyClient
from dotenv import load_dotenv

_ = load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

tavily_client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

# Tool for web search
@tool
async def search(query: str) -> str:
    """
    Searches the web for the given query.
    Args:
        query (str): The query to search for.
    """
    print(f"\nSearching for: {query}\n")
    return await tavily_client.search(query, search_depth="basic", max_results=3)

# Agent Wrapper
class LangGraphAgent:
    """A class that encapsulates the LangGraph agent."""

    def __init__(self, name: str, prompt: str):
        """Initializes the agent."""
        self.checkpointer = InMemorySaver()
        self.agent = create_react_agent(
            model="google_genai:gemini-2.0-flash",
            name=name,
            tools=[search],
            checkpointer=self.checkpointer,
            prompt=prompt,
        )

    async def run(self, query: str, thread_id: str):
        """
        Runs the agent's response for a given query and thread_id.
        """
        inputs = {"messages": [HumanMessage(content=query)]}

        # The config dictionary specifies the thread_id for persistence.
        config = {"configurable": {"thread_id": thread_id}}

        response = await self.agent.ainvoke(inputs, config=config)
        return response["messages"][-1].content