from .openai_compatible import OpenAICompatibleProvider
import os


class OpenRouterProvider(OpenAICompatibleProvider):

    name = "openrouter"

    def __init__(self):
        super().__init__(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url="https://openrouter.ai/api/v1",
        )