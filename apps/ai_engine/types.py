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
