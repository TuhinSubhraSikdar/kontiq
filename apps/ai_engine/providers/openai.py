from django.conf import settings
from openai import OpenAI

from apps.ai_engine.types import GenerationRequest, GenerationResult


class OpenAIProvider:
    name = "openai"

    def __init__(self, *, api_key=None, model=None, base_url=None):
        self.api_key = settings.OPENAI_API_KEY if api_key is None else api_key
        self.model = settings.OPENAI_MODEL if model is None else model
        self.base_url = base_url

    @property
    def is_configured(self):
        return bool(self.api_key and self.model)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_configured:
            raise RuntimeError("OpenAI is not configured with an API key and model.")
        client_options = dict(
            api_key=self.api_key,
            timeout=float(settings.AI_TIMEOUT_SECONDS),
            max_retries=0,
        )
        if self.base_url:
            client_options["base_url"] = self.base_url
        client = OpenAI(**client_options)
        response = client.responses.create(
            model=request.model,
            instructions=request.system,
            input=request.prompt,
            max_output_tokens=request.max_output_tokens,
        )
        usage = {}
        if getattr(response, "usage", None):
            usage_obj = response.usage
            usage = usage_obj.model_dump(mode="json") if hasattr(usage_obj, "model_dump") else {}
        return GenerationResult(
            text=response.output_text,
            provider=self.name,
            model=request.model,
            response_id=getattr(response, "id", "") or "",
            usage=usage,
        )
