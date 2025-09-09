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
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)

AGENT_URL = "http://localhost:10003"

async def main():
    async with httpx.AsyncClient() as async_client:
        config = ClientConfig(supported_transports=[TransportProtocol.jsonrpc])
        factory = ClientFactory(config)
        
        card_resolver = A2ACardResolver(async_client, AGENT_URL)
        agent_card = await card_resolver.get_agent_card()
        client: Client = factory.create(agent_card)
        
        print(f"--- Client Initialized for: {agent_card.name} ---\n")
        
        user_message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text="What is the weather in Murree?"))],
            message_id=str(uuid4()),
        )
        
        print(f"--> Sending request: '{user_message.parts[0].root.text}'\n")
        
        final_task = None
        print("--- Real-time Stream from Agent ---")
        async for event in client.send_message(request=user_message):
            # The event is a tuple: (Task, UpdateEvent)
            current_task_state, update_event = event

            # Handle each type of update event gracefully.
            if isinstance(update_event, TaskStatusUpdateEvent):
                # This event signals a change in the task's state.
                state = update_event.status.state
                
                # Check if there is an associated message before printing it.
                if update_event.status.message:
                    progress_message = update_event.status.message.parts[0].root.text
                    print(f"  [STATE: {state.upper()}] {progress_message}")
                else:
                    # If no message, just print the state change.
                    print(f"  [STATE: {state.upper()}]")

            elif isinstance(update_event, TaskArtifactUpdateEvent):
                # In the future, agents might stream artifacts piece by piece.
                artifact_name = update_event.artifact.name
                print(f"  [ARTIFACT UPDATE] Received update for artifact: '{artifact_name}'")
            
            # Keep track of the latest full Task object
            final_task = current_task_state

        print("--- Stream Finished ---\n")

        if isinstance(final_task, Task):
            print("--> Final Task Details:")
            print(f"    Task ID: {final_task.id}")
            print(f"    Final Status: {final_task.status.state}")
            if final_task.artifacts:
                result_text = final_task.artifacts[0].parts[0].root.text
                print(f"    Result from Artifact: '{result_text}'")
            else:
                print("    No artifacts found in the completed task.")
        else:
            print("Did not receive a final Task object.")

if __name__ == "__main__":
    asyncio.run(main())
