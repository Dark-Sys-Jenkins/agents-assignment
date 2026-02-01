import logging

import aiohttp
from dotenv import load_dotenv

from livekit.agents import AgentServer, JobContext, cli
from livekit.agents.llm import function_tool
from livekit.agents.voice import Agent, AgentSession, InterruptionFilter
from livekit.plugins import openai, silero, deepgram

logging.basicConfig(level=logging.INFO)

load_dotenv()


# Set USE_REALTIME=False to use the STT+LLM+TTS pipeline with interruption filtering
USE_REALTIME = False


class WeatherAgent(Agent):
    def __init__(self) -> None:
        if USE_REALTIME:
            # Realtime API - interruption handling is done server-side by OpenAI
            # Our InterruptionFilter won't work with this mode
            super().__init__(
                instructions="You are a weather agent.",
                llm=openai.realtime.RealtimeModel(),
            )
        else:
            # Traditional STT + LLM + TTS pipeline - our filter works here
            super().__init__(
                instructions="You are a weather agent.",
                llm=openai.LLM(model="gpt-4o-mini"),
                tts=openai.TTS(voice="nova"),
            )

    @function_tool
    async def get_weather(
        self,
        latitude: str,
        longitude: str,
    ):
        """Called when the user asks about the weather. This function will return the weather for
        the given location. When given a location, please estimate the latitude and longitude of the
        location and do not ask the user for them.

        Args:
            latitude: The latitude of the location
            longitude: The longitude of the location
        """

        url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m"
        weather_data = {}
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    # response from the function call is returned to the LLM
                    weather_data = {
                        "temperature": data["current"]["temperature_2m"],
                        "temperature_unit": "Celsius",
                    }
                else:
                    raise Exception(f"Failed to get weather data, status code: {response.status}")

        return weather_data


server = AgentServer()


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # each log entry will include these fields
    ctx.log_context_fields = {
        "room_name": ctx.room.name,
        "user_id": "your user_id",
    }

    interruption_filter = InterruptionFilter()

    if USE_REALTIME:
        session = AgentSession()
    else:
        session = AgentSession(
            stt=deepgram.STT(),  # Use Deepgram for STT
            vad=silero.VAD.load(),  # Use Silero for VAD
            interruption_filter=interruption_filter,  # Enable backchannel filtering
        )

    await session.start(
        agent=WeatherAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
