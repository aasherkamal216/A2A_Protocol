import asyncio
import httpx
from uuid import uuid4

from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    TransportProtocol,
    Task,
    TaskState,
    TaskStatusUpdateEvent,
    DataPart,
)

AGENT_URL = "http://localhost:10004"

def create_user_message(user_input: str, thread_info: dict) -> Message:
    """Creates a user message, including task/context IDs if they exist."""
    return Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=user_input))],
        message_id=str(uuid4()),
        task_id=thread_info.get("task_id"),
        context_id=thread_info.get("context_id"),
    )

async def run_conversation_turn(client: Client, message: Message) -> Task | None:
    """Handles a single turn, streaming events and returning the final task state."""
    final_task_state = None
    async for event in client.send_message(request=message):
        # The event is a tuple: (Task, UpdateEvent | None)
        current_task, update_event = event
        final_task_state = current_task
    
    return final_task_state

def handle_agent_response(task: Task | None) -> str:
    """Processes the final task state to determine the next action for the user."""
    if not task:
        print("Conversation ended unexpectedly.")
        return "quit"

    if task.status.state == TaskState.completed:
        print("✅ Task Completed Successfully!")
        if task.artifacts:
            result_text = task.artifacts[0].parts[0].root.text
            print(f"   Agent Final Response: '{result_text}'")
        return "quit" # Signal to end conversation

    if task.status.state in [TaskState.failed, TaskState.rejected, TaskState.canceled]:
         print(f"❌ Task ended with status: {task.status.state}")
         return "quit"
    
    if task.status.state == TaskState.input_required:
        agent_message = task.status.message
        if agent_message and agent_message.parts:
            # Check if this is an approval request (has DataPart)
            data_part = next((p.root for p in agent_message.parts if isinstance(p.root, DataPart)), None)
            if data_part:
                print(f"\033[91m--- APPROVAL REQUIRED ---\033[0m")
                print(f"\033[94m Question: {data_part.data.get('question')}\033[0m")
                print(f"\033[94m Diet Plan:\033[0m", data_part.data.get('plan'))
                print("--" * 20)
                return input("\033[92m\nYour response (yes/no): \033[0m")

            # Otherwise, it's a regular question (TextPart)
            text_part = agent_message.parts[0].root
            if isinstance(text_part, TextPart):
                print("\033[94mAgent: \033[0m", text_part.text)
                return input("\033[92m\nYou: \033[0m")

async def main():
    async with httpx.AsyncClient(timeout=60.0) as async_client:
        config = ClientConfig(supported_transports=[TransportProtocol.jsonrpc])
        factory = ClientFactory(config)
        
        card_resolver = A2ACardResolver(async_client, AGENT_URL)
        agent_card = await card_resolver.get_agent_card()
        client: Client = factory.create(agent_card)
        
        print(f"--- Client Initialized for: {agent_card.name} ---")
        print("--- Type 'quit' or 'exit' to end the conversation. ---\n")
        
        thread_info = {}
        user_input = input("\033[92mYou: \033[0m")

        while user_input.lower() not in ["quit", "exit"]:
            message = create_user_message(user_input, thread_info)
            final_task = await run_conversation_turn(client, message)
            
            # Update state for the next turn
            if final_task:
                thread_info["task_id"] = final_task.id
                thread_info["context_id"] = final_task.context_id
            
            user_input = handle_agent_response(final_task)
            
            if user_input.lower() in ["quit", "exit"]:
                break
        
        print("Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())