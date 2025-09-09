import uvicorn
import random

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities, Part, TextPart
from a2a.utils import new_task

# --- 1. Agent Card ---
skill = AgentSkill(
    id="dice_roller",
    name="Roll a Die",
    description="Rolls a standard 6-sided die.",
    tags=["dice", "game"],
)
agent_card = AgentCard(
    name="Stateful Dice Agent",
    description="An agent that demonstrates the A2A Task lifecycle.",
    url="http://localhost:10002/",
    version="1.0.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

# --- 2. Agent Logic ---
class DiceAgent:
    """The agent's business logic."""
    def roll(self) -> int:
        print("Agent Logic: Rolling a 6-sided die...")
        return random.randint(1, 6)

# --- 3. The A2A Executor ---
class DiceAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = DiceAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Handles the request and manages the task lifecycle."""
        # A2A tasks should be stateful. If a task doesn't exist for this request,
        # create one. `new_task` is a helper from the SDK.
        task = context.current_task or new_task(context.message)
        
        # The TaskUpdater is the primary tool for managing a task's state.
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        # 1. Immediately tell the client the task has been submitted.
        await updater.submit()
        print(f"Task {task.id}: State -> SUBMITTED")

        # 2. Tell the client we are starting the work.
        await updater.start_work()
        print(f"Task {task.id}: State -> WORKING")
        
        # 3. Perform the actual work.
        roll_result = self.agent.roll()

        # 4. Package the result into an Artifact.
        # An artifact is the formal, structured output of a task.
        result_part = Part(root=TextPart(text=f"You rolled a {roll_result}!"))
        await updater.add_artifact([result_part], name='dice_roll_result')
        print(f"Task {task.id}: Added artifact with result '{roll_result}'")

        # 5. Tell the client the task is complete.
        await updater.complete()
        print(f"Task {task.id}: State -> COMPLETED")
    
    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- 4. Main Server Setup ---
if __name__ == '__main__':
    request_handler = DefaultRequestHandler(
        agent_executor=DiceAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print("Starting Stateful Dice Agent Server on http://localhost:10002")
    uvicorn.run(server_app_builder.build(), host='0.0.0.0', port=10002)
