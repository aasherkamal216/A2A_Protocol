import requests
import json
from uuid import uuid4

AGENT_URL = "http://localhost:9999"

def main():
    # === Part 1: Agent Discovery ===
    # A2A agents expose their capabilities via an Agent Card at a well-known URL.
    agent_card_url = f"{AGENT_URL}/.well-known/agent-card.json"
    print(f"--> 1. Fetching Agent Card from: {agent_card_url}\n")
    
    try:
        response = requests.get(agent_card_url)
        response.raise_for_status()
        agent_card = response.json()
        
        print("--- Agent Card Received ---")
        print(json.dumps(agent_card, indent=2))
        print("---------------------------\n")

        # The card tells us where the agent's RPC endpoint is.
        rpc_endpoint = agent_card.get("url")
        if not rpc_endpoint:
            print("ERROR: Agent Card does not contain a URL.")
            return

        # === Part 2: Agent Interaction (JSON-RPC) ===
        # We construct a JSON-RPC 2.0 request payload.
        # The method is `message/send`, as defined by the A2A spec.
        request_id = str(uuid4())
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "Can you say hello?"}],
                    "messageId": str(uuid4()),
                    "kind": "message",
                }
            }
        }

        print(f"--> 2. Sending JSON-RPC request to: {rpc_endpoint}\n")
        print("--- Request Payload ---")
        print(json.dumps(payload, indent=2))
        print("-----------------------\n")
        
        rpc_response = requests.post(rpc_endpoint, json=payload)
        rpc_response.raise_for_status()
        response_data = rpc_response.json()

        print("--- Response Payload ---")
        print(json.dumps(response_data, indent=2))
        print("------------------------\n")

        # === Part 3: Interpreting the Response ===
        if response_data.get("id") == request_id and "result" in response_data:
            result = response_data["result"]
            # The result for this simple agent is a Message object.
            text_part = result["parts"][0]["text"]
            print(f"--> 3. SUCCESS! Agent responded with: '{text_part}'")
        else:
            print(f"--> 3. FAILED! Agent returned an error: {response_data.get('error')}")

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")

if __name__ == "__main__":
    main()