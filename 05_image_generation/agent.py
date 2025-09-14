import os
from dotenv import load_dotenv
import asyncio

from google import genai
from google.genai import types

load_dotenv()

class MultimodalAgent:
    """The agent's logic using the Gemini 2.0 Flash model."""
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = "gemini-2.0-flash-preview-image-generation"

    async def generate_image(self, prompt: str) -> list[types.Part]:
        """Generates an image from a text prompt."""
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            )
        )
        return response.candidates[0].content.parts

    async def remix_image(self, prompt: str, image_bytes: bytes) -> list[types.Part]:
        """Generates a new image based on an existing image and a text prompt."""
        image_part = types.Part.from_bytes(data=image_bytes, mime_type='image/png')
        
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=self.model,
            contents=[image_part, prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )
        return response.candidates[0].content.parts