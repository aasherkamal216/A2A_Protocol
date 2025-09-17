import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Part, TextPart
from a2a.utils import new_task
from debaters.newton_agent import NewtonAgent

NEWTON_PORT = 10007

# --- Agent Card ---
skill = AgentSkill(
    id="debate_skill",
    name="Debate as Newton",
    description="Participates in a debate from the perspective of Isaac Newton.",
    tags=["debate"],
)
agent_card = AgentCard(
    name="Isaac Newton Agent",
    description="An A2A agent impersonating Isaac Newton for a debate.",
    url=f"http://localhost:{NEWTON_PORT}/",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
)

# --- A2A Executor ---
class NewtonExecutor(AgentExecutor):
    def __init__(self):
        self.agent = NewtonAgent()
        print("Newton Executor initialized.")

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
        print(f"[Newton Task {task.id}] Responded and completed.")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- Main Server Setup ---
if __name__ == "__main__":
    request_handler = DefaultRequestHandler(
        agent_executor=NewtonExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print(f"Starting Newton Agent Server on http://localhost:{NEWTON_PORT}")
    uvicorn.run(server_app_builder.build(), host="0.0.0.0", port=NEWTON_PORT)