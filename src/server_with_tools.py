"""AG-UI server with backend tool rendering."""

import os
from typing import Annotated, Any

from agent_framework import ChatAgent, ai_function
from agent_framework.azure import AzureOpenAIChatClient
from agent_framework_ag_ui import add_agent_framework_fastapi_endpoint
from azure.identity import AzureCliCredential
from fastapi import FastAPI
from pydantic import Field
from dotenv import load_dotenv
from tools import WeatherTools

load_dotenv()


# Define function tools
@ai_function
def get_weather(
    location: Annotated[str, Field(description="The city")],
) -> str:
    """Get the current weather for a location."""
    # Simulated weather data
    return f"The weather in {location} is sunny with a temperature of 22°C."


@ai_function
def search_restaurants(
    location: Annotated[str, Field(description="The city to search in")],
    cuisine: Annotated[str, Field(description="Type of cuisine")] = "any",
) -> dict[str, Any]:
    """Search for restaurants in a location."""
    # Simulated restaurant data
    return {
        "location": location,
        "cuisine": cuisine,
        "results": [
            {"name": "The Golden Fork", "rating": 4.5, "price": "$$"},
            {"name": "Bella Italia", "rating": 4.2, "price": "$$$"},
            {"name": "Spice Garden", "rating": 4.7, "price": "$$"},
        ],
    }


# Read required configuration
endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

if not endpoint:
    raise ValueError("AZURE_OPENAI_ENDPOINT environment variable is required")
if not deployment_name:
    raise ValueError("AZURE_OPENAI_DEPLOYMENT_NAME environment variable is required")

chat_client = AzureOpenAIChatClient(
    credential=AzureCliCredential(),
    endpoint=endpoint,
    deployment_name=deployment_name,
)

# Create tools instance
weather_tools = WeatherTools(api_key=os.environ.get("WEATHER_API_KEY", "demo-key"))

# Create agent with tools
agent = ChatAgent(
    name="TravelAssistant",
    instructions="You are a helpful travel assistant. Use the available tools to help users plan their trips.",
    chat_client=chat_client,
    tools=[weather_tools.get_current_weather, weather_tools.get_forecast, search_restaurants],
)

# Create FastAPI app
app = FastAPI(title="AG-UI Travel Assistant")
add_agent_framework_fastapi_endpoint(app, agent, "/")

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8888)
