# Stateful Task Agent

This project builds upon the "Hello World" example by introducing the concept of a stateful `Task` and structured `Artifacts`.

## Learning Objectives

-   Understand the difference between a stateless `Message` response and a stateful `Task` object.
-   Learn about the A2A Task lifecycle states: `submitted`, `working`, and `completed`.
-   Use the `TaskUpdater` from the A2A Python SDK to manage and broadcast task state changes.
-   Return structured data from an agent using an `Artifact`.
-   Implement a client that can receive and interpret a final `Task` object.

## How It Works

This project contains a simple "Dice Rolling" agent. When a client sends a message, the agent doesn't just reply instantly. Instead, it:

1.  **Creates a `Task`**: A formal, trackable unit of work with a unique ID.
2.  **Broadcasts State Changes**: It sends status updates to the client, announcing that the task is `submitted`, then `working`.
3.  **Performs an Action**: It "rolls a die" to get a number from 1 to 6.
4.  **Packages the Result**: The result of the roll is placed inside a formal `Artifact`.
5.  **Completes the Task**: It sends a final status update, marking the task as `completed`.

Even though this process is very fast, it demonstrates the full, stateful protocol flow that is essential for long-running and complex agent interactions.

## How to Run

Ensure you have activated your virtual environment and installed the dependencies. Make sure you are in `02_stateful_task_agent` directory.

### 1. Start the Server

```bash
uv run server.py
```
The server will start on `http://localhost:10002`.

### 2. Run the Client

In a **new terminal** (with the virtual environment activated), run the client:
```bash
uv run client.py
```

The client will connect to the agent, send a request, and print the final, complete `Task` object it receives in the response, including the result from the artifact.