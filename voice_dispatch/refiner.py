"""
Rule-based transcript refiner.

Entry point: refine(transcript) -> str

To replace with an LLM API call, swap the body of refine() with something like:

    import anthropic
    client = anthropic.Anthropic()
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": (
                "Clean up the following spoken transcript: strip filler words, "
                "fix capitalisation, add punctuation. Return only the cleaned text.\n\n"
                + transcript
            ),
        }],
    )
    return message.content[0].text.strip()
"""

import re


_FILLERS = re.compile(
    r"\b(um+|uh+|like|you know|basically|sort of|kind of|i mean|right|okay|so|well)\b,?\s*",
    re.IGNORECASE,
)

_MULTI_SPACE = re.compile(r" {2,}")


def refine(transcript: str) -> str:
    """Strip filler words, fix capitalisation, and add trailing punctuation."""
    text = transcript.strip()
    if not text:
        return text

    # remove filler words
    text = _FILLERS.sub(" ", text).strip()
    text = _MULTI_SPACE.sub(" ", text)

    if not text:
        return transcript.strip()

    # capitalise first character of each sentence
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s[0].upper() + s[1:] if s else s for s in sentences]
    text = " ".join(sentences)

    # capitalise very first character
    text = text[0].upper() + text[1:]

    # add trailing period if no terminal punctuation
    if text and text[-1] not in ".!?,;:":
        text += "."

    return text
