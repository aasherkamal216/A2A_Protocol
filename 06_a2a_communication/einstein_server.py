import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Part, TextPart
from a2a.utils import new_task
from debaters.einstein_agent import EinsteinAgent

EINSTEIN_PORT = 10006

# --- Agent Card ---
skill = AgentSkill(
    id="debate_skill",
    name="Debate as Einstein",
    description="Participates in a debate from the perspective of Albert Einstein.",
    tags=["debate"],
)
agent_card = AgentCard(
    name="Albert Einstein Agent",
    description="An A2A agent impersonating Albert Einstein for a debate.",
    url=f"http://localhost:{EINSTEIN_PORT}/",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["text/plain"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[skill],
)

# --- A2A Executor ---
class EinsteinExecutor(AgentExecutor):
    def __init__(self):
        self.agent = EinsteinAgent()
        print("Einstein Executor initialized.")

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()
        task = context.current_task or new_task(context.message)
        thread_id = task.context_id  # Use A2A context_id as the debate thread_id

        updater = TaskUpdater(event_queue, task.id, thread_id)
        await updater.submit()

        await updater.start_work()

        # Run the agent logic
        response_text = await self.agent.run(query=user_input, thread_id=thread_id)

        # Package the result into an Artifact
        await updater.add_artifact(
            parts=[Part(root=TextPart(text=response_text))], name="debate_response"
        )
        await updater.complete()
        print(f"[Einstein Task {task.id}] Responded and completed.")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- Main Server Setup ---
if __name__ == "__main__":
    request_handler = DefaultRequestHandler(
        agent_executor=EinsteinExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print(f"Starting Einstein Agent Server on http://localhost:{EINSTEIN_PORT}")
    uvicorn.run(server_app_builder.build(), host="0.0.0.0", port=EINSTEIN_PORT)