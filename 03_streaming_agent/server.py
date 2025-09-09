import uvicorn
import os
from dotenv import load_dotenv

# OpenAI Agents SDK imports
from agents import Agent, Runner, RunResultStreaming, function_tool, ToolCallItem, set_tracing_disabled
from agents.extensions.models.litellm_model import LitellmModel

# A2A SDK imports
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, TaskState, Part, TextPart
from a2a.utils import new_task

# Load .env file
load_dotenv()

# Disable OpenAI tracing
set_tracing_disabled(True)

# --- 1. The Real Agent Logic ---

@function_tool
def get_weather(city: str) -> str:
    """Returns weather info for the specified city."""
    # In a real scenario, this would call a weather API.
    return f"The weather in {city} is sunny and 75°F."

class WeatherAgent:
    """A wrapper for the OpenAI Agent."""
    def __init__(self):
        self.agent = Agent(
            name="Weather agent",
            instructions="You are a weather agent. Always use the provided tool to get weather information.",
            model=LitellmModel(model="gemini/gemini-2.0-flash", api_key=os.getenv("GOOGLE_API_KEY")),
            tools=[get_weather],
        )

    def run(self, user_input: str) -> RunResultStreaming:
        """Runs the agent and returns the run result streaming object."""
        return Runner.run_streamed(self.agent, input=user_input)

# --- 2. The A2A Executor: The Bridge ---

class WeatherAgentExecutor(AgentExecutor):
    """Bridges the OpenAI agent's streaming events to the A2A protocol."""
    def __init__(self):
        self.agent = WeatherAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        await updater.submit()
        print(f"\n--- A2A Task {task.id} Started ---")

        # Get the run result streaming object from our agent
        result = self.agent.run(user_input)

        # Stream events from the agent and map them to A2A events
        async for event in result.stream_events():
            # We ignore raw_response_event to avoid noisy logs
            if event.type == "raw_response_event":
                continue

            a2a_update_message = ""
            if event.type == "agent_updated_stream_event":
                a2a_update_message = f"Agent updated: {event.new_agent.name}"
            elif event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    a2a_update_message = f"Calling tool: {event.item.raw_item.name}"
                elif event.item.type == "tool_call_output_item":
                    a2a_update_message = f"Tool output: {event.item.output}"

            if a2a_update_message:
                print(f"Streaming update: {a2a_update_message}")
                await updater.update_status(TaskState.working, message=updater.new_agent_message(
                    parts=[Part(root=TextPart(text=a2a_update_message))]
                ))

        # Once the stream is done, get the final output
        final_output_message = result.final_output

        # Package the final output as an artifact and complete the task
        await updater.add_artifact(
            parts=[Part(root=TextPart(text=final_output_message))],
            name="weather_report"
        )
        await updater.complete()
        print(f"--- A2A Task {task.id} Completed ---\n")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- 3. A2A Server Setup ---

if __name__ == "__main__":
    skill = AgentSkill(
        id="get_weather",
        name="Get Weather",
        description="Returns weather for a city.",
        tags=["weather"],
    )

    agent_card = AgentCard(
        name="Streaming Weather Agent",
        description="Provides weather information with real-time progress updates.",
        url="http://localhost:10003/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=WeatherAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print("Starting Streaming Weather Agent Server on http://localhost:10003")
    uvicorn.run(server_app_builder.build(), host='0.0.0.0', port=10003)
