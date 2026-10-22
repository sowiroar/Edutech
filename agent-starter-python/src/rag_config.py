"""Generation settings for document-grounded answers in a voice conversation."""

from google.genai import types


def document_generation_config() -> types.GenerateContentConfig:
    # Bound internal reasoning, not the answer length. Keep synthesis, sources,
    # retrieval and the existing Gemini 2.5 Flash model unchanged.
    return types.GenerateContentConfig(
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_budget=512),
    )
