"""AG-UI client with tool event handling."""

import asyncio
import os

from agent_framework import ChatAgent, FunctionCallContent, FunctionResultContent
from agent_framework_ag_ui import AGUIChatClient
from dotenv import load_dotenv
load_dotenv()


async def main():
    """Main client loop with tool event display."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:8888/")
    print(f"Connecting to AG-UI server at: {server_url}\n")

    # Create AG-UI chat client
    chat_client = AGUIChatClient(endpoint=server_url)

    # Create agent with the chat client
    agent = ChatAgent(
        name="ClientAgent",
        chat_client=chat_client,
        instructions="You are a helpful assistant.",
    )

    # Get a thread for conversation continuity
    thread = agent.get_new_thread()

    try:
        while True:
            message = input("\nUser (:q or quit to exit): ")
            if not message.strip():
                continue

            if message.lower() in (":q", "quit"):
                break

            print("\nAssistant: ", end="", flush=True)
            async for update in agent.run_stream(message, thread=thread):
                # Display text content
                if update.text:
                    print(f"\033[96m{update.text}\033[0m", end="", flush=True)

                # Display tool calls and results
                for content in update.contents:
                    if isinstance(content, FunctionCallContent):
                        # FunctionCallContent represents a tool/function call from the assistant
                        print(f"\n\033[95m[Calling tool: {content.name}]\033[0m")
                    elif isinstance(content, FunctionResultContent):
                        # FunctionResultContent represents the result of a tool/function
                        result_text = content.result if isinstance(content.result, str) else str(content.result)
                        print(f"\033[94m[Tool result: {result_text}]\033[0m")

            print("\n")

    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n\033[91mError: {e}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())