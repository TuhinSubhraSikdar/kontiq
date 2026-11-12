from dataclasses import dataclass, field


@dataclass(frozen=True)
class GenerationRequest:
    system: str
    prompt: str
    model: str
    max_output_tokens: int = 8000


@dataclass(frozen=True)
class GenerationResult:
    text: str
    provider: str
    model: str
    response_id: str = ""
    usage: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ImageGenerationRequest:
    prompt: str
    model: str
    size: str = "1024x1024"


@dataclass(frozen=True)
class ImageGenerationResult:
    image_bytes: bytes
    media_type: str = "image/png"
    response_id: str = ""
