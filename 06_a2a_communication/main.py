import asyncio
import httpx
from uuid import uuid4

from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import Message, Part, Role, TextPart, TransportProtocol, Task

EINSTEIN_AGENT_URL = "http://localhost:10006"
NEWTON_AGENT_URL = "http://localhost:10007"

DEBATE_TOPIC = "The Nature of Time"
DEBATE_TURNS = 5 # The number of times each agent will speak

async def get_a2a_client(http_client: httpx.AsyncClient, agent_url: str) -> Client:
    """Discovers an agent and returns an A2A client instance for it."""
    config = ClientConfig(streaming=False, supported_transports=[TransportProtocol.jsonrpc])
    factory = ClientFactory(config)
    card_resolver = A2ACardResolver(http_client, agent_url)
    agent_card = await card_resolver.get_agent_card()
    print(f"Successfully discovered agent: {agent_card.name}")
    return factory.create(agent_card)

async def send_message_and_get_response(
    client: Client, message_text: str, context_id: str
) -> str:
    """Sends a message to an agent and extracts the text response from the artifact."""
    user_message = Message(
        role=Role.user,
        parts=[Part(root=TextPart(text=message_text))],
        message_id=str(uuid4()),
        context_id=context_id,
    )

    final_task_object = None
    async for event in client.send_message(request=user_message):
        if isinstance(event, tuple):
            final_task_object = event[0]
        else:
            final_task_object = event

    if isinstance(final_task_object, Task) and final_task_object.artifacts:
        return final_task_object.artifacts[0].parts[0].root.text
    
    return "Error: Agent did not provide a valid response."

async def main():
    # Use a single httpx client for all communications
    async with httpx.AsyncClient(timeout=120.0) as async_client:

        # 1. Discover and create clients for both agents
        print("\n--> Discovering agents...")
        einstein_client, newton_client = await asyncio.gather(
            get_a2a_client(async_client, EINSTEIN_AGENT_URL),
            get_a2a_client(async_client, NEWTON_AGENT_URL),
        )

        # 2. Start the debate
        debate_id = f"debate-{uuid4()}"
        print(f"\n--> Starting debate on '{DEBATE_TOPIC}'\n")

        # Einstein starts the debate
        current_speaker_name = "Einstein"
        current_speaker_client = einstein_client
        next_speaker_client = newton_client
        
        # Formulate the initial prompt for the first speaker
        current_message = f"Let's argue about {DEBATE_TOPIC}."
        
        # 3. Main debate loop
        for i in range(DEBATE_TURNS * 2):
            print(f"\n---\033[92m Turn {i+1}: {current_speaker_name}'s turn \033[0m---")

            response = await send_message_and_get_response(
                current_speaker_client, current_message, debate_id
            )
            print(f"\033[94m{current_speaker_name}:\033[0m {response}\n")

            # Prepare for the next turn
            current_message = response # The response becomes the next input
            
            # Swap speakers
            if current_speaker_name == "Einstein":
                current_speaker_name = "Newton"
                current_speaker_client = newton_client
                next_speaker_client = einstein_client
            else:
                current_speaker_name = "Einstein"
                current_speaker_client = einstein_client
                next_speaker_client = newton_client

        print("\n--- Debate Concluded ---")

if __name__ == "__main__":
    asyncio.run(main())