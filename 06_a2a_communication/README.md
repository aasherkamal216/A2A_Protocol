# The Agent Debate (Multi-Agent Orchestration)

This project demonstrates a true multi-agent system where a client application orchestrates a conversation between two independent A2A agents. We have an agent impersonating Albert Einstein (built with LangGraph) and another impersonating Isaac Newton (built with the OpenAI Agents SDK).

The `main.py` acts as a moderator, initiating the debate and passing messages between the two agents, which run as separate A2A servers.

## Learning Objectives

-   **Multi-Agent Systems**: Understand how to build applications that coordinate multiple, specialized A2A agents.
-   **Service Orchestration**: See how a client can act as an orchestrator, consuming services from different agents to achieve a larger goal.
-   **Stateful Cross-Agent Conversation**: Learn how to maintain a consistent conversation thread (`context_id`) across multiple agents for a cohesive interaction.
-   **Framework Interoperability**: Witness an agent built with LangGraph seamlessly communicate with an agent built with the OpenAI Agents SDK, all thanks to the A2A protocol.

## How It Works

1.  **Two Servers, Two Agents**: `einstein_server.py` and `newton_server.py` each run an independent A2A agent on a different port. They both expose a single "debate" skill.
2.  **The Orchestrator**: `main.py` is the main client application. It doesn't contain any agent logic itself.
3.  **Discovery**: The client starts by discovering both the Einstein and Newton agents by fetching their `AgentCard`s and creating an A2A `Client` instance for each.
4.  **Initiation**: It generates a unique `debate_id` that will be used as the `context_id` for the entire conversation, ensuring both agents are part of the same "thread." It sends an initial prompt about the debate topic to Einstein.
5.  **The Debate Loop**:
    -   The client waits for Einstein's response. The response comes back as a completed `Task` object.
    -   It extracts the debate response from the `Artifact` inside the task and prints it to the console.
    -   It then sends Einstein's response as the new input to the Newton agent, using the same `debate_id`.
    -   It waits for Newton's response, prints it, and sends it back to Einstein.
    -   This loop continues for a predefined number of turns.

## How to Run

### Prerequisites

*   Python 3.12+
*   [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Project Setup

1.  Ensure you are in the `06_a2a_communication` directory.
    ```bash
    cd 06_a2a_communication
    ```
2.  Create and Activate Virtual Environment:
    ```bash
    uv venv
    .venv\Scripts\activate # for Windows
    source .venv/bin/activate # for Mac
    ```
3.  Install dependencies:
    ```bash
    uv sync
    ```

### 1. Configure API Keys

Create a `.env` file in this directory and add the following environment variables:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
```

### 2. Start the Agent Servers
You need to run both agent servers in separate terminals.

- In your first terminal, start the Einstein server:
```bash
uv run einstein_server.py
```
It will run on http://localhost:10006.

- In your second terminal, start the Newton server:
```bash
uv run newton_server.py
```
It will run on http://localhost:10007.

### 3. Run the Main Orchestrator
In a third terminal, run the main file:
```bash
uv run main.py
```

Watch the terminal as the two great minds debate a topic, thanks to the A2A protocol!