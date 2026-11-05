from .forms import VARIABLE_PATTERN


def render_prompt(template, values):
    """Render only documented scalar variables; no template language is evaluated."""

    return VARIABLE_PATTERN.sub(lambda match: str(values.get(match.group(1), "")), template)
