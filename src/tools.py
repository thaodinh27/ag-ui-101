from typing import Annotated, Any
from agent_framework import ai_function
from pydantic import Field


@ai_function
def get_weather(
    location: Annotated[str, Field(description="The city.")],
) -> str:
    """Get the current weather for a location."""
    return f"The weather in {location} is sunny with a temperature of 22°C."


@ai_function
def get_forecast(
    location: Annotated[str, Field(description="The city.")],
    days: Annotated[int, Field(description="Number of days to forecast")] = 3,
) -> dict[str, Any]:
    """Get the weather forecast for a location."""
    return {
        "location": location,
        "days": days,
        "forecast": [
            {"day": 1, "weather": "Sunny", "high": 24, "low": 18},
            {"day": 2, "weather": "Partly cloudy", "high": 22, "low": 17},
            {"day": 3, "weather": "Rainy", "high": 19, "low": 15},
        ],
    }