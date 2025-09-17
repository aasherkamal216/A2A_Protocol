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
    print(f"\n[EINSTEIN] Searching for: {query}\n")
    return await tavily_client.search(query, search_depth="basic", max_results=3)

# Agent prompt
EINSTEIN_PROMPT = """
You are Albert Einstein, the 20th-century physicist. Today you have to debate with Isaac Newton on a topic.

## INSTRUCTIONS
- Present yourself with wit, calmness, and intellectual depth. 
- Challenge Newton's worldview by pointing out limits and exceptions in his framework. 
- Use thought experiments, analogies, and imaginative reasoning to make your points convincing. 
- Respond to Newton's authority with sharp counterarguments and irony, exposing where his ideas fail. 
- Keep your tone confident, sarcastic and witty, showing that your vision is broader and more revolutionary. 
- Never accept Newton's absolute certainty; always reveal the deeper complexity of reality. 

## TONE & STYLE
- Use short and concise sentences
- Avoid complex vocabulary, use simple words

## WEB SEARCH
- Use the `search` tool if you need to strengthen your arguments with references.
"""

# Agent Wrapper
class EinsteinAgent:
    """A class that encapsulates the Einstein agent."""

    def __init__(self):
        """Initializes the Einstein agent."""
        self.checkpointer = InMemorySaver()
        self.agent = create_react_agent(
            model="google_genai:gemini-2.0-flash",
            name="Albert Einstein Agent",
            tools=[search],
            checkpointer=self.checkpointer,
            prompt=EINSTEIN_PROMPT,
        )

    async def run(self, query: str, thread_id: str):
        """
        Runs the agent's response for a given query and thread_id.

        Args:
            query (str): The user's input message.
            thread_id (str): A unique identifier for the conversation thread.

        Returns:
            The agent's response.
        """
        inputs = {"messages": [HumanMessage(content=query)]}

        # The config dictionary specifies the thread_id for persistence.
        config = {"configurable": {"thread_id": thread_id}}

        response = await self.agent.ainvoke(inputs, config=config)
        return response["messages"][-1].content