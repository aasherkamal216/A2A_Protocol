import asyncio
import httpx
from uuid import uuid4
from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import Message, Part, Role, TextPart, TransportProtocol, Task

AGENT_URL = "http://localhost:10002"

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
            parts=[Part(root=TextPart(text="Roll the die!"))],
            message_id=str(uuid4()),
        )

        client._config.streaming = False
        
        print("--> Sending 'message/send' request...\n")
        
        final_task_object = None
        # The iterator yields events. For a non-streaming task, it yields one event.
        async for event in client.send_message(request=user_message):
            # The event for a task is a tuple (Task, UpdateEvent | None)
            if isinstance(event, tuple):
                # The Task object is the first element of the tuple.
                final_task_object = event[0]
            else:
                # This would handle cases where the agent returns a simple Message, not a Task.
                final_task_object = event

        print("--- Final Task Object Received ---")
        if final_task_object:
            # Now that we have the Task object, we can print it.
            print(final_task_object.model_dump_json(indent=2))
        else:
            print("No final task object was received.")
        print("----------------------------------\n")

        # --- Interpret the Task object ---
        if isinstance(final_task_object, Task):
            print("--> Interpreting the Task:")
            print(f"    Final Status: {final_task_object.status.state}")
            if final_task_object.artifacts:
                result_text = final_task_object.artifacts[0].parts[0].root.text
                print(f"    Result from Artifact: '{result_text}'")
            else:
                print("    No artifacts found in the completed task.")
        else:
            print(f"Expected a Task object, but got {type(final_task_object)}")

if __name__ == "__main__":
    asyncio.run(main())