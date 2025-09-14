import asyncio
import httpx
import os
from uuid import uuid4
import base64

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
    TaskStatusUpdateEvent,
    Artifact
)

AGENT_URL = "http://localhost:10005"
GENERATED_IMAGE_PATH = "generated_image.png"
REMIXED_IMAGE_PATH = "remixed_image.png"

def save_image_from_task(task: Task, output_filename: str):
    """Finds the first image artifact in a task and saves it to a file."""
    image_artifact = next((art for art in task.artifacts if art.name.startswith("image")), None)
    text_artifact = next((art for art in task.artifacts if art.name.startswith("description")), None)
    
    if image_artifact:
        file_part = image_artifact.parts[0].root
        if isinstance(file_part, FilePart) and isinstance(file_part.file, FileWithBytes):
            image_bytes = base64.b64decode(file_part.file.bytes)

            with open(output_filename, "wb") as f:
                f.write(image_bytes)
        else:
            print("ERROR: Image artifact did not contain expected FileWithBytes part.")
    else:
        print("ERROR: No image artifact found in the task response.")
        
    if text_artifact:
        text_part = text_artifact.parts[0].root
        if isinstance(text_part, TextPart):
            print("\n--- Image Description ---")
            print(text_part.text)
            print("-------------------------\n")


async def main():
    # Set a long timeout for the client, as the whole operation can be slow.
    async with httpx.AsyncClient(timeout=60.0) as async_client:
        # Client must support streaming to handle long-running tasks
        config = ClientConfig(streaming=True, supported_transports=[TransportProtocol.jsonrpc])
        factory = ClientFactory(config)

        card_resolver = A2ACardResolver(async_client, AGENT_URL)
        agent_card = await card_resolver.get_agent_card()
        client: Client = factory.create(agent_card)

        print(f"--- Client Initialized for: {agent_card.name} ---\n")

        # --- Part 1: Generate an Image from a Text Prompt ---
        print("--> 1. Requesting to generate a new image...")
        generate_prompt = "A futuristic robot artist painting a portrait of a cat in a surreal, neon-lit city"

        generate_message = Message(
            role=Role.user,
            parts=[Part(root=TextPart(text=generate_prompt))],
            message_id=str(uuid4()),
        )

        final_task_object = None
        print("--- Real-time Stream from Agent ---")
        async for event in client.send_message(request=generate_message):
            # The event is a tuple: (Task, UpdateEvent | None)
            current_task_state, update_event = event
            if isinstance(update_event, TaskStatusUpdateEvent) and update_event.status.message:
                progress_message = update_event.status.message.parts[0].root.text
                print(f"  [STATUS: {current_task_state.status.state.upper()}] {progress_message}")
            final_task_object = current_task_state
        print("--- Stream Finished ---\n")

        if not isinstance(final_task_object, Task):
            print("Failed to get a valid task object for image generation.")
            return

        save_image_from_task(final_task_object, GENERATED_IMAGE_PATH)

        if not os.path.exists(GENERATED_IMAGE_PATH):
            print("Image generation failed, cannot proceed to remixing.")
            return

        # --- Part 2: Remix the Generated Image ---
        print(f"--> 2. Requesting to remix the generated image '{GENERATED_IMAGE_PATH}'...")

        with open(GENERATED_IMAGE_PATH, "rb") as f:
            image_bytes_raw = f.read()

        # We must base64 encode the raw bytes to send them in the string field.
        image_bytes_b64 = base64.b64encode(image_bytes_raw).decode('utf-8')

        remix_prompt = "Make the art style more like Van Gogh's Starry Night"
        remix_message = Message(
            role=Role.user,
            parts=[
                Part(
                    root=FilePart(
                        file=FileWithBytes(
                            bytes=image_bytes_b64,
                            mime_type="image/png",
                            name=GENERATED_IMAGE_PATH,
                        )
                    )
                ),
                Part(root=TextPart(text=remix_prompt)),
            ],
            message_id=str(uuid4()),
        )

        final_remix_task = None
        print("--- Real-time Stream from Agent ---")
        async for event in client.send_message(request=remix_message):
            current_task_state, update_event = event
            if isinstance(update_event, TaskStatusUpdateEvent) and update_event.status.message:
                progress_message = update_event.status.message.parts[0].root.text
                print(f"  [STATUS: {current_task_state.status.state.upper()}] {progress_message}")
            final_remix_task = current_task_state
        print("--- Stream Finished ---\n")

        if not isinstance(final_remix_task, Task):
            print("Failed to get a valid task object for image remixing.")
            return

        save_image_from_task(final_remix_task, REMIXED_IMAGE_PATH)

if __name__ == "__main__":
    asyncio.run(main())
