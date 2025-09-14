# The Image Handler (File Artifacts)

This project covers the critical pattern of receiving and producing binary data, specifically images, over a JSON-based protocol.

We will use Google's multimodal Gemini model, which can generate an image. This makes it a perfect use case for demonstrating A2A's asynchronous task management and streaming capabilities, and the correct way to handle blocking code in an async environment.

## Learning Objectives

-   **Implement a Non-Blocking Agent Executor**: Use `asyncio.to_thread` to run synchronous, blocking code in a separate thread, keeping the main server event loop responsive.
-   **Provide Real-Time Progress Updates**: Use `TaskUpdater` to immediately acknowledge a request and send `working` status updates to the client, providing an excellent user experience while waiting for a slow backend.
-   **Handle Binary Data with Base64**: Learn the standard pattern for transmitting binary data in JSON by encoding/decoding it with Base64.
-   **Process Incoming `FilePart`**: Learn how the `AgentExecutor` receives and decodes Base64 data from an incoming `FilePart`.
-   **Produce Binary `Artifacts`**: Create `Artifacts` that contain Base64-encoded image data in a `FilePart` for the client to consume.
-   **Define Multiple Agent Skills**: Create an `AgentCard` that advertises multiple distinct capabilities for a single agent.

## How It Works

The "Image Generation & Remix Agent" has two skills, both of which are now handled asynchronously to prevent server stalls.

1.  **Generate Skill**:
    -   **Client**: Sends a `Message` with a text prompt and starts listening on the stream.
    -   **Server**: Immediately receives the request and sends back `submitted` and `working` status updates. The client knows the task is accepted and won't time out.
    -   **Server**: The `AgentExecutor` calls the Gemini `generate_content` method inside `asyncio.to_thread`. This moves the blocking API call off the main event loop.
    -   **(...Time Passes...)**
    -   **Server**: The thread completes, and the Gemini API returns the image `bytes`.
    -   **Server**: It **Base64 encodes** the raw image `bytes` into a string.
    -   **Server**: It creates an `Artifact` containing this Base64 string in a `FilePart` and sends it to the client, followed by a `completed` status.
    -   **Client**: Receives the final `Task`, finds the `FilePart`, **Base64 decodes** the string back into bytes, and saves the image to a file.

2.  **Remix Skill**:
    -   **Client**: Reads an image from a file, **Base64 encodes** it into a string, and sends a `Message` with two parts: a `FilePart` containing the encoded string and a `TextPart` with a remix instruction.
    -   **Server**: Receives the multimodal message, finds the `FilePart`, **Base64 decodes** the string back into the original image `bytes`, and extracts the text prompt.
    -   **Server**: The process then follows the same non-blocking `asyncio.to_thread` pattern as the generate skill to call the Gemini API.
    -   **Client**: Receives the remixed image and saves it.

## How to Run

### Prerequisites

*   Python 3.12+
*   [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Project Setup

1. Ensure you are in the `05_image_generation` directory.
```bash
cd 05_image_generation
```

2. Create and Activate Virtual Environment:
```bash
uv venv
.venv\Scripts\activate # for Windows
source .venv/bin/activate # for Mac
```

3. Install dependencies:
```bash
uv sync
```


### 1. Configure API Key

Create a `.env` file in the **root of the `05_image_generation` directory** and add your Google Gemini API key:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Start the Server

```bash
uv run server.py
```
The server will start on `http://localhost:10005`.

### 3. Run the Client

In a **new terminal** (with the virtual environment activated), run the client:
```bash
uv run client.py
```

The client will automatically run a two-part demonstration:
1. It will first ask the agent to generate a new image, printing real-time progress updates. It will save the result as `generated_image.png`.
2. It will then immediately use that new image to ask the agent for a remix, again with progress updates, saving the result as `remixed_image.png`.

Check your `05_image_generation` directory for the output images!