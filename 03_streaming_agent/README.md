# Streaming Weather Agent

This project demonstrates how to create a real agent that provides real-time progress updates to the client by streaming events.

This example uses the new **OpenAI Agents SDK** as the agent framework, showing how A2A can wrap any underlying agent technology.

## Learning Objectives

-   Integrate a third-party agent framework (OpenAI Agents) within an A2A `AgentExecutor`.
-   Understand how to map events from an agent's internal process to the A2A streaming protocol.
-   Use the `TaskUpdater` to send multiple `working` status updates during a task's execution.
-   Build a client that can connect to a streaming endpoint and process a sequence of `TaskStatusUpdateEvent`s in real-time.
-   See the stateful `Task` lifecycle in action with a perceptible delay and intermediate feedback.

## How It Works

This project contains a "Weather Agent". When a client asks for the weather:

1.  **A2A Server** receives the request and passes it to the `WeatherAgentExecutor`.
2.  **The Executor** starts the Weather Agent's logic.
3.  **Weather Agent** begins its process, which involves steps like "agent updated," "tool call," and "tool output."
4.  **The Executor** listens to these internal events from the agent's stream.
5.  For each internal event, the executor **maps it to an A2A `TaskStatusUpdateEvent`** and sends it immediately to the client through the open HTTP connection.
6.  The client receives these updates in real-time and prints them to the console.
7.  Once the agent produces its final answer, the executor packages it into an `Artifact` and sends a `completed` status to end the stream.

## How to Run

### Prerequisites

*   Python 3.12+
*   [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Project Setup

1. Ensure you are in the `03_streaming_agent` directory.
```bash
cd 03_streaming_agent
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

Create a `.env` file in the **root of the `03_streaming_agent` directory** and add your Google Gemini API key:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key_here
```

> [!NOTE]
> You can use any model and provider supported by LiteLLM.

### 2. Start the Server

```bash
uv run server.py
```
The server will start on `http://localhost:10003`.

### 3. Run the Client

In a **new terminal** (with the virtual environment activated), run the client:
```bash
uv run client.py
```

The client will connect to the agent and you will see the progress updates printed to the console in real-time as the agent works, followed by the final result.