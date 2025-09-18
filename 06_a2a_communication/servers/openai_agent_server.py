import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Part, TextPart
from a2a.utils import new_task

from debaters.openai_agent import OpenAIAgent
from debaters.agents_config import AGENTS_CONFIG

PORT = 10007
AGENT_CONFIG = AGENTS_CONFIG["newton"]

# --- Agent Card ---
agent_card = AgentCard(
    name=AGENT_CONFIG["name"],
    description=AGENT_CONFIG["description"],
    url=f"http://localhost:{PORT}/",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[AgentSkill(**skill) for skill in AGENT_CONFIG["skills"]],
)

# --- A2A Executor ---
class OpenAIExecutor(AgentExecutor):
    def __init__(self):
        self.agent = OpenAIAgent(name=AGENT_CONFIG["name"], prompt=AGENT_CONFIG["prompt"])

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        task = context.current_task or new_task(context.message)
        session_id = task.context_id  # Use A2A context_id as the debate session_id

        updater = TaskUpdater(event_queue, task.id, session_id)
        await updater.submit()

        await updater.start_work()

        # Run the agent logic
        response_text = await self.agent.run(query=user_input, session_id=session_id)

        # Package the result into an Artifact
        await updater.add_artifact(
            parts=[Part(root=TextPart(text=response_text))], name="debate_response"
        )
        await updater.complete()

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- Main Server Setup ---
if __name__ == "__main__":
    request_handler = DefaultRequestHandler(
        agent_executor=OpenAIExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print(f"Starting OpenAI Agent Server on http://localhost:{PORT}")
    uvicorn.run(server_app_builder.build(), host="0.0.0.0", port=PORT)