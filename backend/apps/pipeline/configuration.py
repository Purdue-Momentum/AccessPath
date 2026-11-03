"""Pipeline-owned provider configuration; Django loads the ignored .env at startup."""

import os

from django.conf import settings


def option(name, default=None):
    return getattr(settings, name, os.environ.get(name, default))


def model_for(kind):
    name = "GENAI_VISION_MODEL" if kind in {"image", "graph", "equation"} else "GENAI_TEXT_MODEL"
    default = "gemma4:26b-a4b" if name == "GENAI_VISION_MODEL" else "gpt-oss:120b"
    return option(name, default)
