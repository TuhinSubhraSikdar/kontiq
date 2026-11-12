from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from PIL import Image, ImageOps

from apps.ai_engine.models import AIProviderConfiguration
from apps.ai_engine.provider_configuration import get_runtime_provider_configuration
from apps.ai_engine.providers.openai import OpenAIProvider
from apps.ai_engine.types import ImageGenerationRequest


@dataclass(frozen=True)
class BrandImageAssets:
    feature: bytes
    body: bytes


def has_brand_kit(project):
    return bool(project.brand_color and project.brand_logo)


def _prompt(*, content, placement):
    project = content.project
    subject = content.title if placement == "feature" else content.task.primary_keyword
    role = "hero feature image" if placement == "feature" else "supporting editorial body image"
    return (
        f"Create a polished {role} for an article titled '{subject}' for {project.name}. "
        f"Use the brand theme color {project.brand_color} as a clear visual accent. "
        f"Match this audience: {project.audience[:400]}. "
        f"Style should align with this brand voice: {project.brand_voice[:400]}. "
        "Use an editorial, professional composition with no words, letters, watermarks, "
        "or invented logos. Leave the lower-right area visually simple for a real logo overlay."
    )


def _apply_logo(*, image_bytes, project):
    with Image.open(BytesIO(image_bytes)) as source, project.brand_logo.open("rb") as logo_source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        with Image.open(logo_source) as logo_file:
            logo = ImageOps.exif_transpose(logo_file).convert("RGBA")
        max_width = max(1, int(image.width * 0.18))
        max_height = max(1, int(image.height * 0.14))
        logo.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        margin = max(16, int(min(image.width, image.height) * 0.035))
        position = (image.width - logo.width - margin, image.height - logo.height - margin)
        image.alpha_composite(logo, dest=position)
        output = BytesIO()
        image.convert("RGB").save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()


def generate_brand_images(content):
    """Generate two private branded images when a project has a complete brand kit.

    The logo is composited locally after generation so the saved asset contains the
    exact uploaded mark rather than a model's approximation.
    """
    if not has_brand_kit(content.project):
        return None
    configuration = get_runtime_provider_configuration()
    if configuration.provider != AIProviderConfiguration.Provider.OPENAI:
        raise RuntimeError("Branded image generation requires an active OpenAI provider.")
    provider = OpenAIProvider(
        api_key=configuration.api_key,
        model=configuration.model,
        base_url=configuration.base_url,
    )
    feature = provider.generate_image(
        ImageGenerationRequest(
            prompt=_prompt(content=content, placement="feature"),
            model=settings.OPENAI_IMAGE_MODEL,
            size=settings.AI_IMAGE_SIZE,
        )
    )
    body = provider.generate_image(
        ImageGenerationRequest(
            prompt=_prompt(content=content, placement="body"),
            model=settings.OPENAI_IMAGE_MODEL,
            size=settings.AI_IMAGE_SIZE,
        )
    )
    return BrandImageAssets(
        feature=_apply_logo(image_bytes=feature.image_bytes, project=content.project),
        body=_apply_logo(image_bytes=body.image_bytes, project=content.project),
    )
