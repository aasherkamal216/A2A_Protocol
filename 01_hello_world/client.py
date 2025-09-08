import asyncio
import httpx
from uuid import uuid4

from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import Message, Part, Role, TextPart, TransportProtocol

AGENT_URL = "http://localhost:9999"

async def main():
    async with httpx.AsyncClient() as async_client:
        print("--> 1. Discovering agent and creating client...\n")

        # --- Create the client config and factory ---
        config = ClientConfig(
            httpx_client=async_client,
            supported_transports=[TransportProtocol.jsonrpc] 
        )
        factory = ClientFactory(config)
        
        card_resolver = A2ACardResolver(async_client, AGENT_URL)
        agent_card = await card_resolver.get_agent_card()

        client: Client = factory.create(agent_card)
        
        print(f"--- Client Initialized for: {agent_card.name} ---\n")

        # === Part 2: Send a standard (non-streaming) message ===
        print("--> 2. Sending a standard 'message/send' request...\n")
        
        user_message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text="Hello again, modern SDK!"))],
            message_id=str(uuid4()),
            kind="message",
        )
        
        client._config.streaming = False # Force non-streaming for this call
        
        final_response = None
        # The iterator will yield one item and finish for non-streaming calls
        async for response in client.send_message(request=user_message):
            final_response = response
        
        print("--- Response (non-streaming) ---")
        if isinstance(final_response, Message):
             print(f"Agent responded: '{final_response.parts[0].root.text}'")
        else:
             print(f"Agent responded with a Task: {final_response}")
        print("------------------------------------\n")

        # === Part 3: Send a streaming message ===
        print("--> 3. Sending a 'message/stream' request...\n")
        
        client._config.streaming = True # Re-enable streaming
        
        print("--- Response (streaming) ---")
        stream = client.send_message(request=user_message)
        
        async for event in stream:
            if isinstance(event, Message):
                print(f"Received stream event: Agent says '{event.parts[0].root.text}'")
            else:
                print(f"Received unexpected stream event type: {type(event)}")
        
        print("Stream finished.")
        print("--------------------------------\n")
        
if __name__ == "__main__":
    asyncio.run(main())