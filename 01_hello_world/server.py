import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import AgentCard, AgentSkill, AgentCapabilities
from a2a.utils import new_agent_text_message

# --- 1. Define the Agent's "Business Card" (AgentCard) ---
# This card tells other agents what this agent can do and where to find it.

skill = AgentSkill(
    id='hello_world_skill',
    name='Returns "Hello World"',
    description='A simple skill that returns a greeting.',
    tags=['hello', 'greeting']
)

agent_card = AgentCard(
    name='HelloWorld Agent',
    description='A basic A2A agent that says hello.',
    # This URL must match where the server will be running.
    url='http://localhost:9999/',
    version='1.0.0',
    default_input_modes=['text'],
    default_output_modes=['text'],
    capabilities=AgentCapabilities(streaming=True), # We support streaming
    skills=[skill],
)

# --- 2. Define the Agent's Core Logic ---
# This is the actual "brain" of your agent.

class HelloWorldAgent:
    """The actual agent logic, completely separate from A2A protocol details."""
    async def invoke(self) -> str:
        return 'Hello A2A World!'

# --- 3. Create the A2A Executor ---
# This class acts as a bridge between the A2A server and your agent's logic.

class HelloWorldAgentExecutor(AgentExecutor):
    """Implements the A2A AgentExecutor interface."""
    def __init__(self):
        self.agent = HelloWorldAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        This method is called by the A2A server when it receives a message.
        - 'context' contains the incoming user message.
        - 'event_queue' is used to send responses back.
        """
        print(f"Received user message: '{context.get_user_input()}'")
        
        # 1. Run the agent's logic
        result_text = await self.agent.invoke()

        # 2. Enqueue the response. The server will handle sending it.
        # `new_agent_text_message` is a helper from the SDK.
        await event_queue.enqueue_event(new_agent_text_message(result_text))
        print("Sent 'Hello A2A World!' response to the event queue.")

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        # This simple agent doesn't support cancellation.
        raise NotImplementedError('Cancellation is not supported.')

# --- 4. Wire Everything Together and Run the Server ---

if __name__ == '__main__':
    # The DefaultRequestHandler handles the JSON-RPC methods (message/send, etc.)
    # and calls our HelloWorldAgentExecutor.
    request_handler = DefaultRequestHandler(
        agent_executor=HelloWorldAgentExecutor(),
        task_store=InMemoryTaskStore(), # Manages task state (simple for this agent)
    )

    # The A2AStarletteApplication creates the web server application.
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )

    print("Starting HelloWorld A2A Agent Server on http://localhost:9999")
    uvicorn.run(server_app_builder.build(), host='0.0.0.0', port=9999)