# The Interactive Agent (Multi-Turn Conversation with Human-in-the-loop)

This project takes a major step forward by integrating a sophisticated, diet planner agent built with **LangGraph**. It demonstrates how A2A can wrap any agent logic and, most importantly, how to handle continuous, multi-turn conversations where the agent can either ask clarifying questions or pause for user approval before acting.

## Learning Objectives

-   **Integrate an External Agent**: Wrap an agent built with an external framework (LangGraph) inside an A2A `AgentExecutor`.
-   **Manage a Continuous Conversation**: Use a single A2A `Task` and `contextId` to manage a conversation that spans multiple back-and-forth exchanges.
-   **Master `input_required`**: Use `TaskState.input_required` as the universal signal for when the agent is waiting for user input. This project implements the critical logic to differentiate between two types of interruptions:
    1.  **Tool Approval (Structured `DataPart`)**: When the agent is about to perform an action and needs confirmation.
    2.  **Clarifying Questions (Simple `TextPart`)**: When the agent needs more information to proceed with the conversation.
-   **Build a State-Aware Server**: The A2A server will use the `Task.metadata` field to reliably track the *reason* for a pause, allowing it to correctly decide whether to continue a conversation (`stream()`) or resume from a tool-call interruption (`resume()`).
-   **Build a Conversational Client**: Create a client with a `while` loop that can chat continuously, handle both types of interruptions, and seamlessly continue the conversation.

## How It Works

The `agent.py` file contains a Diet Planner agent that uses a tool to "send an email." Before it calls the tool, it interrupts its own execution to ask for human approval. We map this entire conversational flow to the A2A protocol:

1.  **Client -> Server (Turn 1)**: The user sends an initial prompt in a `while` loop (e.g., "Hello").
2.  **Server (`AgentExecutor`)**:
    -   Receives the message. Since it's a new conversation, it creates a new A2A `Task` and calls the LangGraph agent's `stream()` method.
    -   The agent asks a clarifying question ("How can I help you today to plan your diet?"). The server sees the stream ended with this question.
    -   It sends a `TaskStatusUpdateEvent` with `state: input_required` and the agent's question in a `TextPart`.
3.  **Client**:
    -   The `while` loop receives the `input_required` state, sees the `TextPart`, and prints the agent's question, prompting the user for the next input.
4.  **Client -> Server (Turn 2)**: The user provides more info ("Please send a diet plan to user@example.com"). The client sends this in a new message, reusing the `taskId` and `contextId`.
5.  **Server (`AgentExecutor`)**:
    -   It sees an incoming message for an existing task in the `input_required` state. It inspects the `Task.metadata` and sees it's a normal conversational turn (not a tool approval). **It correctly calls the agent's `stream()` method again.**
    -   The agent now has enough info and decides to call the `send_diet_plan` tool. This triggers an `__interrupt__` in LangGraph.
    -   The executor catches this, packages the approval data into a `DataPart`, sets `task.metadata['interrupt_type'] = 'approval'`, and sets the A2A task state to `input_required`.
6.  **Client (Approval Micro-Turn)**:
    -   The client's loop receives the `input_required` state, but this time it sees a structured `DataPart`. It recognizes this is an approval request.
    -   It prompts the user ("yes/no") and sends the response back, reusing the `taskId` and `contextId`.
7.  **Server (`AgentExecutor`)**:
    -   It receives a message for a task in the `input_required` state. It inspects the `Task.metadata` and sees `interrupt_type` is 'approval'. **It now calls the agent's `resume()` method.**
    -   The agent's tool call completes, and the agent streams the final confirmation.
8.  **Server -> Client (Completion)**: The executor sends the final result in an `Artifact` and sets the A2A task state to `completed`. The client loop prints the result and is ready for a new conversation.

## How to Run

### Prerequisites

*   Python 3.12+
*   [uv](https://docs.astral.sh/uv/getting-started/installation/)

### Project Setup

1. Ensure you are in the `04_interactive_agent` directory.
```bash
cd 04_interactive_agent
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

Create a `.env` file in the **root of the `04_interactive_agent` directory** and add your Google Gemini API key:

```bash
# .env file
GOOGLE_API_KEY=your_gemini_api_key_here
```

### 2. Start the Server

```bash
uv run server.py
```
The server will start on `http://localhost:10004`.

### 3. Run the Client

In a **new terminal** (with the virtual environment activated), run the client:
```bash
uv run client.py
```
You can now have a continuous conversation with the agent. It will ask for your email, and then ask for approval before completing its task.