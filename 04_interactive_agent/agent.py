import os
from typing import Any

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage

from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt, Command
from dotenv import load_dotenv

load_dotenv()

os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")

# --- 1. Define Tool with Human-in-the-loop ---

@tool
def send_diet_plan(
    email: str,
    diet_plan: str,
) -> str:
    """
    Sends the diet plan to the user's email.

    Args:
        diet_plan (str): The diet plan to send to the user.
        email (str): The user's email address to send the plan to.
    """

    # Step 1: Interrupt for human approval
    approval_response = interrupt(
        {
            "question": f"Do you approve this diet plan before sending to {email}?",
            "plan": diet_plan,
        }
    )

    # Step 2: Handle the user's approval response
    if approval_response and str(approval_response).lower() in ['yes', 'true', 'approve']:
        return f"Diet plan successfully sent to {email}."
    else:
        return "User cancelled the action. The diet plan was not sent."


# --- 2. Create the Agent Class ---

class DietPlannerAgent:
    """A class that encapsulates the diet planner agent."""

    def __init__(self):
        """Initializes the Diet Planner agent."""

        # 3. Create the agent
        self.agent = create_react_agent(
            model="google_genai:gemini-2.5-flash",
            tools=[send_diet_plan],
            checkpointer=InMemorySaver(),
            prompt=(
                "You are a friendly and helpful diet planner assistant."
                "Your goal is to collect all necessary information from the user "
                "to create a personalized diet plan. Once you have all the details "
                "that you need to create a diet plan for the user, create the plan "
                "and send it to the user's email using the `send_diet_plan` tool. "
                "Once you've created the plan, and **successfully** sent it to the user's "
                "email, respond with 'Success! The diet plan has been sent to you.' "
                "If you fail to send the diet plan to the user's email, tell the user "
                "that the diet plan was not sent."
            ),
        )

    async def stream(self, query: str, thread_id: str):
        """
        Streams the agent's response for a given query and thread_id.

        Args:
            query (str): The user's input message.
            thread_id (str): A unique identifier for the conversation thread.

        Yields:
            The streamed chunks from the agent's execution.
        """
        inputs = {"messages": [HumanMessage(content=query)]}

        # The config dictionary specifies the thread_id for persistence.
        config = {"configurable": {"thread_id": thread_id}}

        async for chunk in self.agent.astream(inputs, config=config):
            yield chunk


    async def resume(self, resume_value: Any, thread_id: str):
        """
        Resumes a paused (interrupted) agent execution.

        Args:
            resume_value: The value to pass back to the graph to continue execution.
            thread_id (str): The ID of the conversation thread to resume.
        """
        # The Command primitive is used to send control signals to the graph.
        resume_command = Command(resume=resume_value)
        config = {"configurable": {"thread_id": thread_id}}

        async for chunk in self.agent.astream(resume_command, config=config):
            yield chunk