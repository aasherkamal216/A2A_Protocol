import uvicorn

from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import (
    AgentCard,
    AgentSkill,
    AgentCapabilities,
    TaskState,
    Part,
    TextPart,
    DataPart,
)
from a2a.utils import new_task

# Import the LangGraph agent
from agent import DietPlannerAgent

# --- 1. Agent Card ---
skill = AgentSkill(
    id="diet_planner",
    name="Diet Planner",
    description="Creates a diet plan and sends it to user's email.",
    tags=["health", "diet", "planning"],
)
agent_card = AgentCard(
    name="Interactive Diet Planner Agent",
    description="An agent that uses LangGraph and interacts with user to create a diet plan. It then sends the plan to user's email after approval.",
    url="http://localhost:10004/",
    version="1.0.0",
    default_input_modes=["text/plain"],
    default_output_modes=["application/json", "text/plain"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[skill],
)

# --- 2. The A2A Executor ---
class DietPlannerAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = DietPlannerAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()

        task = context.current_task or new_task(context.message)
        thread_id = task.context_id

        updater = TaskUpdater(event_queue, task.id, thread_id)

        print(f"\n--- A2A Task {task.id} (Thread: {thread_id}) ---")

        agent_stream = None

        # --- Multi-Turn Logic with State Tracking ---
        is_resuming_from_approval = (
            task.status.state == TaskState.input_required and
            task.metadata and
            task.metadata.get('interrupt_type') == 'approval'
        )

        if is_resuming_from_approval:
            # The last pause was for a tool approval. We MUST RESUME.
            print(f"Resuming task from approval with: '{user_input}'")
            agent_stream = self.agent.resume(resume_value=user_input, thread_id=thread_id)
        else:
            # This is a new task or a regular conversational turn. We STREAM.
            print(f"Continuing conversation with: '{user_input}'")
            if not context.current_task:
                await updater.submit()
            agent_stream = self.agent.stream(query=user_input, thread_id=thread_id)

        # --- Stream Mapping ---
        final_message_content = ""
        interrupted_for_approval = False

        async for chunk in agent_stream:
            if "__interrupt__" in chunk:
                interrupted_for_approval = True
                print(">>> LangGraph Agent Requested Approval. Setting state to 'input_required'.")
                interrupt_data = chunk["__interrupt__"][0].value
                prompt_part = Part(root=DataPart(data=interrupt_data))
                prompt_message = updater.new_agent_message(parts=[prompt_part])

                # Set metadata to remember WHY we are pausing.
                await updater.update_status(
                    TaskState.input_required,
                    message=prompt_message,
                    final=True,
                    metadata={'interrupt_type': 'approval'} # State tracking!
                )
                print("--- A2A Task Paused for Approval ---")
                return

            messages = chunk.get("agent", {}).get("messages", [])
            if messages:
                last_message = messages[-1]

                if hasattr(last_message, 'content'):
                    final_message_content = str(last_message.content)

                print(f"Streaming progress: {final_message_content}")
                await updater.update_status(
                    TaskState.working,
                    message=updater.new_agent_message(parts=[Part(root=TextPart(text=final_message_content))])
                )

        # --- Task Completion or Continuation ---
        if not interrupted_for_approval:
            # Clear any previous interrupt metadata
            task.metadata = None 

            if not final_message_content.startswith("Success!"):
                print(">>> Agent is asking a question. Setting state to 'input_required'.")
                question_message = updater.new_agent_message(
                    parts=[Part(root=TextPart(text=final_message_content))]
                )
                await updater.requires_input(message=question_message, final=True)
                print("--- A2A Task Paused for Information ---")
            else:
                print(f"Agent finished. Final output: {final_message_content}")
                await updater.add_artifact(
                    parts=[Part(root=TextPart(text=final_message_content))],
                    name="diet_plan_result",
                )
                await updater.complete()
                print(f"--- A2A Task {task.id} Completed ---")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- 3. Main Server Setup ---
if __name__ == '__main__':
    request_handler = DefaultRequestHandler(
        agent_executor=DietPlannerAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print("Starting Interactive Diet Planner Agent Server on http://localhost:10004")
    uvicorn.run(server_app_builder.build(), host='0.0.0.0', port=10004)
