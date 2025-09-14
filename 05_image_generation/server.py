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
    Part,
    TextPart,
    FilePart,
    FileWithBytes,
)
from a2a.utils import new_task, get_file_parts

from google.genai import types as genai_types
import base64
from agent import MultimodalAgent

# --- The A2A Executor ---
class ImageAgentExecutor(AgentExecutor):
    def __init__(self):
        self.agent = MultimodalAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input_text = context.get_user_input()
        user_input_files = get_file_parts(context.message.parts)

        task = context.current_task or new_task(context.message)
        updater = TaskUpdater(event_queue, task.id, task.context_id)

        print(f"\n--- A2A Task {task.id} Started ---")
        await updater.submit()

        gemini_parts: list[genai_types.Part] = []

        if user_input_files:
            await updater.start_work(
                message=updater.new_agent_message(
                    parts=[
                        Part(
                            root=TextPart(
                                text="Starting to remix your image... Please wait."
                            )
                        )
                    ]
                )
            )
            if isinstance(user_input_files[0], FileWithBytes):
                image_bytes_b64 = user_input_files[0].bytes
                image_bytes = base64.b64decode(image_bytes_b64)
                gemini_parts = await self.agent.remix_image(
                    user_input_text, image_bytes
                )
            else:
                raise NotImplementedError("Image remix via URI is not implemented.")
        else:
            await updater.start_work(
                message=updater.new_agent_message(
                    parts=[
                        Part(
                            root=TextPart(
                                text="Starting to generate your image... This may take up to a minute."
                            )
                        )
                    ]
                )
            )
            gemini_parts = await self.agent.generate_image(user_input_text)

        for i, part in enumerate(gemini_parts):
            if part.text is not None:
                await updater.add_artifact(parts=[Part(root=TextPart(text=part.text))], name=f"description_{i}")

            elif part.inline_data is not None:
                image_bytes_b64 = base64.b64encode(part.inline_data.data).decode("utf-8")
                a2a_file_part = FilePart(
                    file=FileWithBytes(
                        bytes=image_bytes_b64,
                        mime_type=part.inline_data.mime_type,
                        name=f"generated_image_{i}.png",
                    )
                )
                await updater.add_artifact(parts=[Part(root=a2a_file_part)], name=f"image_{i}")

        await updater.complete(
            message=updater.new_agent_message(
                parts=[Part(root=TextPart(text="Image processing complete!"))]
            )
        )
        print(f"--- A2A Task {task.id} Completed ---")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError()

# --- A2A Server Setup ---
if __name__ == "__main__":
    generate_skill = AgentSkill(
        id="generate_image",
        name="Generate Image",
        description="Generates an image from a text prompt.",
        tags=["image", "generation"],
    )
    remix_skill = AgentSkill(
        id="remix_image",
        name="Remix Image",
        description="Takes an image and a text prompt to create a new image.",
        tags=["image", "remix", "edit"],
    )

    agent_card = AgentCard(
        name="Image Generation & Remix Agent",
        description="A multimodal agent that can create and edit images using Gemini.",
        url="http://localhost:10005/",
        version="1.0.0",
        default_input_modes=["text/plain", "image/png"],
        default_output_modes=["text/plain", "image/png"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[generate_skill, remix_skill],
    )

    request_handler = DefaultRequestHandler(
        agent_executor=ImageAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server_app_builder = A2AStarletteApplication(
        agent_card=agent_card, http_handler=request_handler
    )
    print("Starting Image Generation Agent Server on http://localhost:10005")
    uvicorn.run(server_app_builder.build(), host="0.0.0.0", port=10005)
