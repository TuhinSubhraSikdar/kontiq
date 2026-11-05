from django.conf import settings
from openai import OpenAI

from apps.ai_engine.types import GenerationRequest, GenerationResult


class OpenAIProvider:
    name = "openai"

    @property
    def is_configured(self):
        return bool(settings.OPENAI_API_KEY and settings.OPENAI_MODEL)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_configured:
            raise RuntimeError("OpenAI is not configured. Add OPENAI_API_KEY and OPENAI_MODEL to .env.")
        client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=float(settings.AI_TIMEOUT_SECONDS),
            max_retries=0,
        )
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
