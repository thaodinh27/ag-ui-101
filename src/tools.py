from agent_framework import ai_function
from pydantic import Field
from typing import Annotated, Any


class WeatherTools:
    """Collection of weather-related tools."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    @ai_function
    def get_current_weather(
        self,
        location: Annotated[str, Field(description="The city.")],
    ) -> str:
        """Get current weather for a location."""
        # Use self.api_key to call API
        return f"Current weather in {location}: Sunny, 22°C"

    @ai_function
    def get_forecast(
        self,
        location: Annotated[str, Field(description="The city.")],
        days: Annotated[int, Field(description="Number of days")] = 3,
    ) -> dict[str, Any]:
        """Get weather forecast for a location."""
        # Use self.api_key to call API
        return {"location": location, "forecast": [...]}
