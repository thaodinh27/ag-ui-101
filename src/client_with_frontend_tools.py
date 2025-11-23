"""AG-UI client with frontend tools."""

import asyncio
import json
import os
from typing import Annotated, AsyncIterator

import httpx
from pydantic import BaseModel, Field
from dotenv import load_dotenv



load_dotenv()


class SensorReading(BaseModel):
    """Sensor reading from client device."""
    temperature: float
    humidity: float
    air_quality_index: int


# Define frontend tools
def read_climate_sensors(
    include_temperature: Annotated[bool, Field(description="Include temperature")] = True,
    include_humidity: Annotated[bool, Field(description="Include humidity")] = True,
) -> SensorReading:
    """Read climate sensor data from the client device."""
    return SensorReading(
        temperature=22.5 if include_temperature else 0.0,
        humidity=45.0 if include_humidity else 0.0,
        air_quality_index=75,
    )


def get_user_location() -> dict:
    """Get the user's current GPS location."""
    # Simulate GPS reading
    return {
        "latitude": 52.3676,
        "longitude": 4.9041,
        "accuracy": 10.0,
        "city": "Amsterdam",
    }


# Tool registry maps tool names to functions
FRONTEND_TOOLS = {
    "read_climate_sensors": read_climate_sensors,
    "get_user_location": get_user_location,
}


class AGUIClientWithTools:
    """AG-UI client with frontend tool support."""

    def __init__(self, server_url: str, tools: dict):
        self.server_url = server_url
        self.tools = tools
        self.thread_id: str | None = None

    async def send_message(self, message: str) -> AsyncIterator[dict]:
        """Send a message and handle streaming response with tool execution."""
        # Prepare tool declarations for the server with proper parameter schemas
        tool_declarations = []
        
        # Define parameter schemas for each tool
        tool_schemas = {
            "read_climate_sensors": {
                "type": "object",
                "properties": {
                    "include_temperature": {
                        "type": "boolean",
                        "description": "Include temperature",
                        "default": True,
                    },
                    "include_humidity": {
                        "type": "boolean",
                        "description": "Include humidity",
                        "default": True,
                    },
                },
                "required": [],  # Both parameters have defaults
            },
            "get_user_location": {
                "type": "object",
                "properties": {},  # No parameters
                "required": [],
            },
        }
        
        for name, func in self.tools.items():
            parameters_schema = tool_schemas.get(name, {"type": "object", "properties": {}})
            
            tool_declarations.append({
                "name": name,
                "description": func.__doc__ or "",
                "parameters": parameters_schema,
            })

        request_data = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant with access to client tools."},
                {"role": "user", "content": message},
            ],
            "tools": tool_declarations,  # Send tool declarations to server
        }

        if self.thread_id:
            request_data["thread_id"] = self.thread_id

        print('Payload sent to server:', json.dumps(request_data, indent=2))

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream(
                "POST",
                self.server_url,
                json=request_data,
                headers={"Accept": "text/event-stream"},
            ) as response:
                response.raise_for_status()

                # Map of pending tool calls: toolCallId -> {name, buffer}
                pending_tool_calls: dict[str, dict] = {}

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            event = json.loads(data)

                            ev_type = event.get("type")

                            # TOOL_CALL_START: create buffer for args
                            if ev_type == "TOOL_CALL_START":
                                tcid = event.get("toolCallId")
                                pending_tool_calls[tcid] = {
                                    "name": event.get("toolCallName"),
                                    "buffer": "",
                                }

                            # TOOL_CALL_ARGS: append delta fragments
                            elif ev_type == "TOOL_CALL_ARGS":
                                tcid = event.get("toolCallId")
                                delta = event.get("delta", "")
                                if tcid in pending_tool_calls:
                                    pending_tool_calls[tcid]["buffer"] += delta
                                else:
                                    # If we haven't seen a start, create an entry conservatively
                                    pending_tool_calls[tcid] = {"name": event.get("toolCallName"), "buffer": delta}

                            # TOOL_CALL_END: parse accumulated args and invoke handler
                            elif ev_type == "TOOL_CALL_END":
                                tcid = event.get("toolCallId")
                                info = pending_tool_calls.pop(tcid, None)
                                args = {}
                                if info and info.get("buffer"):
                                    buf = info["buffer"]
                                    try:
                                        args = json.loads(buf)
                                    except Exception:
                                        # best-effort fallback: try replacing single quotes
                                        try:
                                            args = json.loads(buf.replace("'", '"'))
                                        except Exception:
                                            args = {}

                                # Build a consolidated event for the handler
                                handler_event = {
                                    "toolCallName": (info.get("name") if info else event.get("toolCallName")),
                                    "toolCallId": tcid,
                                    "arguments": args,
                                }
                                await self._handle_tool_call(handler_event, client)

                            else:
                                # Non-tool events are yielded to the caller
                                # Capture thread_id if present
                                if ev_type == "RUN_STARTED" and not self.thread_id:
                                    self.thread_id = event.get("threadId")
                                yield event

                        except json.JSONDecodeError:
                            continue

    async def _handle_tool_call(self, event: dict, client: httpx.AsyncClient):
        """Execute frontend tool and send result back to server."""
        tool_name = event.get("toolCallName")
        tool_call_id = event.get("toolCallId")
        arguments = event.get("arguments", {})

        print(f"\n\033[95m[Client Tool Call: {tool_name}]\033[0m")
        print(f"  Arguments: {arguments}")

        try:
            # Execute the tool
            tool_func = self.tools.get(tool_name)
            if not tool_func:
                raise ValueError(f"Unknown tool: {tool_name}")

            result = tool_func(**arguments)

            # Convert Pydantic models to dict
            if hasattr(result, "model_dump"):
                result = result.model_dump()

            print(f"\033[94m[Client Tool Result: {result}]\033[0m")

            # Send result back to server
            await client.post(
                f"{self.server_url}/tool_result",
                json={
                    "tool_call_id": tool_call_id,
                    "result": result,
                },
            )

        except Exception as e:
            print(f"\033[91m[Tool Error: {e}]\033[0m")
            # Send error back to server
            await client.post(
                f"{self.server_url}/tool_result",
                json={
                    "tool_call_id": tool_call_id,
                    "error": str(e),
                },
            )


async def main():
    """Main client loop with frontend tools."""
    server_url = os.environ.get("AGUI_SERVER_URL", "http://127.0.0.1:8888/")
    print(f"Connecting to AG-UI server at: {server_url}\n")

    client = AGUIClientWithTools(server_url, FRONTEND_TOOLS)

    try:
        while True:
            message = input("\nUser (:q or quit to exit): ")
            if not message.strip():
                continue

            if message.lower() in (":q", "quit"):
                break

            print()
            async for event in client.send_message(message):
                event_type = event.get("type", "")

                if event_type == "RUN_STARTED":
                    print(f"\033[93m[Run Started]\033[0m")

                elif event_type == "TEXT_MESSAGE_CONTENT":
                    print(f"\033[96m{event.get('delta', '')}\033[0m", end="", flush=True)

                elif event_type == "RUN_FINISHED":
                    print(f"\n\033[92m[Run Finished]\033[0m")

                elif event_type == "RUN_ERROR":
                    error_msg = event.get("message", "Unknown error")
                    print(f"\n\033[91m[Error: {error_msg}]\033[0m")

            print()

    except KeyboardInterrupt:
        print("\n\nExiting...")
    except Exception as e:
        print(f"\n\033[91mError: {e}\033[0m")


if __name__ == "__main__":
    asyncio.run(main())