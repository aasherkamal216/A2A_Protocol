import chainlit as cl
import httpx
import base64
from uuid import uuid4

from a2a.client import Client, ClientConfig, ClientFactory, A2ACardResolver
from a2a.types import (
    Message,
    Part,
    Role,
    TextPart,
    FilePart,
    FileWithBytes,
    TransportProtocol,
    Task,
    TaskStatusUpdateEvent
)

AGENT_URL = "http://localhost:10005"

@cl.on_chat_start
async def on_chat_start():
    """
    Initializes the A2A client when a new chat session starts.
    The client is stored in the user session for reuse.
    """

    async_client = httpx.AsyncClient(timeout=120.0)
    config = ClientConfig(streaming=True, supported_transports=[TransportProtocol.jsonrpc])
    factory = ClientFactory(config)
    card_resolver = A2ACardResolver(async_client, AGENT_URL)

    try:
        agent_card = await card_resolver.get_agent_card()
        client: Client = factory.create(agent_card)
        cl.user_session.set("a2a_client", client)
        cl.user_session.set("httpx_client", async_client)
        print(f"--- A2A Client Initialized for: {agent_card.name} ---")
    except Exception as e:
        await cl.Message(
            content=f"Error: Could not connect to the A2A server at `{AGENT_URL}`. Please ensure the server is running."
        ).send()
        print(f"Failed to initialize A2A client: {e}")

@cl.on_chat_end
async def on_chat_end():
    httpx_client = cl.user_session.get("httpx_client")
    if httpx_client:
        await httpx_client.aclose()
        print("--- HTTPX Client closed ---")

@cl.on_message
async def on_message(msg: cl.Message):
    a2a_client = cl.user_session.get("a2a_client")
    if not a2a_client:
        await cl.Message(content="A2A Client not initialized. Cannot process request.").send()
        return

    image_elements = [el for el in msg.elements if "image" in el.mime]
    user_prompt = msg.content
    a2a_message = None
    step_name = ""

    # --- 1. Prepare the A2A Message ---
    if image_elements:
        step_name = "Remixing Image"
        image_element = image_elements[0]
        image_bytes_raw = None
        with open(image_element.path, "rb") as f:
            image_bytes_raw = f.read()
        image_bytes_b64 = base64.b64encode(image_bytes_raw).decode('utf-8')

        a2a_message = Message(
            role=Role.user,
            parts=[
                Part(
                    root=FilePart(
                        file=FileWithBytes(
                            bytes=image_bytes_b64,
                            mime_type=image_element.mime,
                            name=image_element.name,
                        )
                    )
                ),
                Part(root=TextPart(text=user_prompt)),
            ],
            message_id=str(uuid4()),
        )
    elif user_prompt:
        step_name = "Generating Image"
        a2a_message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=user_prompt))],
            message_id=str(uuid4()),
        )
    else:
        await cl.Message(content="Please provide a prompt.").send()
        return

    # --- 2. Show Progress and Stream the A2A Response ---
    final_task_object = None
    async with cl.Step(name=step_name, type="tool", show_input=False) as step:
        step.input = user_prompt
        try:
            async for event in a2a_client.send_message(request=a2a_message):
                current_task_state, update_event = event
                if isinstance(update_event, TaskStatusUpdateEvent) and update_event.status.message:
                    progress_message = update_event.status.message.parts[0].root.text
                    step.output = progress_message # Update the step's output with the progress
                final_task_object = current_task_state
        except Exception as e:
            step.output = f"An error occurred: {e}"
            print(f"Error during A2A communication: {e}")
            return

    # --- 3. Process and Display the Final Result ---
    if isinstance(final_task_object, Task):
        image_artifact = next((art for art in final_task_object.artifacts if art.name.startswith("image")), None)
        text_artifact = next((art for art in final_task_object.artifacts if art.name.startswith("description")), None)

        result_elements = []
        result_text = "Here is your generated image."

        if text_artifact and isinstance(text_artifact.parts[0].root, TextPart):
            result_text = text_artifact.parts[0].root.text

        if image_artifact:
            file_part = image_artifact.parts[0].root
            if isinstance(file_part, FilePart) and isinstance(file_part.file, FileWithBytes):
                image_bytes_decoded = base64.b64decode(file_part.file.bytes)
                result_elements.append(
                    cl.Image(content=image_bytes_decoded, name="generated_image.png", display="inline")
                )

        if not result_elements:
            await cl.Message(content="Sorry, the agent did not return an image.").send()
        else:
            await cl.Message(content=result_text, elements=result_elements, author="Image Agent").send()
    else:
        await cl.Message(content="Failed to get a valid response from the agent.").send()
