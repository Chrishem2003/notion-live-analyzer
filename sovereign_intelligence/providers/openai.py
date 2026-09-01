from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):

    name = "openai"

    def __init__(self):
        super().__init__(
            base_url="https://api.openai.com/v1"
        )