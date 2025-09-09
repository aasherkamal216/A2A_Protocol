# Your First A2A Agent (Hello World)

This example is the "Hello World" of the Agent2Agent protocol. It demonstrates the fundamental components of an A2A server and how a client can discover and interact with it.

![A2A Communication](/public/a2a_communication.png)

### File Structure

This example consists of three key files:

*   `server.py`: Contains the complete A2A agent server. It defines the agent's capabilities, its core logic, and the HTTP server that hosts it.
*   `raw_client.py`: A client that communicates with the server using only the `requests` library. This is to demonstrate the underlying A2A protocol without any SDK abstractions.
*   `client.py`: A modern client that uses the `a2a-sdk`'s `ClientFactory` to simplify discovery and communication.

### Running the Example

Follow these steps in order. You will need **two separate terminal windows**.

#### Step 1: Prerequisites

Ensure you have activated your virtual environment and installed the dependencies. Make sure you are in `01_hello_world` directory.


#### Step 2: Start the A2A Server

In your **first terminal**, run the server:

```bash
uv run server.py
```

You should see a message indicating the server is running on `http://localhost:9999`.


Your agent is now live and waiting for requests!

#### Step 3: Interact with Raw HTTP

In your **second terminal**, run the `raw_client.py`.

```bash
uv run raw_client.py
```

The script will first fetch the Agent Card to "discover" the agent and then send it a message. The output will clearly show each step of the process and the final successful response from the agent.

#### Step 4: Interact with the A2A SDK Client

Now, see how the SDK simplifies the process. In the **same second terminal**, run the `client.py`:

```bash
uv run client.py
```

This script performs the same actions but uses the `ClientFactory` and `Client` objects from the SDK to handle the details of discovery and JSON-RPC communication for you. It also demonstrates both a standard and a streaming request.

### Code Deep Dive (`server.py`)

The `server.py` file is organized into four logical parts:

1.  **The Agent Card:** This is a Pydantic model (`AgentCard`) that acts as the agent's public advertisement. It defines its name, URL, and skills. This is what the client fetches for discovery.
2.  **The Agent Logic (`HelloWorldAgent`):** This is a simple class containing the core "business logic." It's completely independent of the A2A protocol itself.
3.  **The A2A Executor (`HelloWorldAgentExecutor`):** This class is the bridge. It implements the `AgentExecutor` interface from the SDK. Its `execute` method receives the client's message, calls your agent's logic, and puts the response onto an `event_queue`.
4.  **The Server Setup:** The `if __name__ == '__main__':` block uses components from the SDK (`DefaultRequestHandler`, `A2AStarletteApplication`) to wrap your executor in a fully compliant A2A web server and run it with `uvicorn`.

### Congratulations!

You have successfully built and interacted with your first A2A agent.
