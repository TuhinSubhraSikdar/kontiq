from django.conf import settings
from openai import OpenAI

from apps.ai_engine.types import GenerationRequest, GenerationResult


class OpenAICompatibleProvider:
    def __init__(self, *, name, api_key, model, base_url):
        self.name = name
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @property
    def is_configured(self):
        return bool(self.api_key and self.model and self.base_url)

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if not self.is_configured:
            raise RuntimeError(
                "The selected AI provider is not configured with an API key, model, and base URL."
            )
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=float(settings.AI_TIMEOUT_SECONDS),
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=request.model,
            messages=[
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.prompt},
            ],
            max_tokens=request.max_output_tokens,
        )
        if not response.choices or not response.choices[0].message.content:
            raise RuntimeError("The selected AI provider returned no text.")
        usage = {}
        if getattr(response, "usage", None):
            usage_obj = response.usage
            usage = usage_obj.model_dump(mode="json") if hasattr(usage_obj, "model_dump") else {}
        return GenerationResult(
            text=response.choices[0].message.content,
            provider=self.name,
            model=request.model,
            response_id=getattr(response, "id", "") or "",
            usage=usage,
        )
