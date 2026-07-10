"""
Translation engine — offline-first, AI-backed.

Flow:
  1. User inputs English + selects a mode
  2. Query offline_translation.db cache
  3. Cache hit → return (increment frequency)
  4. Cache miss → call AI API with mode-specific prompt
  5. Save AI result to offline cache
  6. Return result
"""

import json
import re
from openai import OpenAI, APIError, APITimeoutError, APIConnectionError
from config.config import get_api_key, get_api_url, get_model
from database.offline_database import search_translation, save_translation


CATEGORY_MAP = {
    "daily":    "Daily Conversation",
    "anime":    "Anime / Manga",
    "movie":    "Movie",
    "game":     "Game",
    "internet": "Internet Slang",
    "formal":   "Formal Expression",
}


# ---------------------------------------------------------------------------
# Mode-specific system prompts
# ---------------------------------------------------------------------------

BASE_ROLE = (
    "You are a young Chinese language teacher from mainland China.\n"
    "Your student is a young Filipino woman who loves anime, manga, games, "
    "movies, and Chinese internet culture.\n"
    "Her native language is English.\n\n"
    "Your job is NOT to mechanically translate English into textbook Chinese.\n"
    "Your job is to convert English into the way REAL young Chinese people "
    "actually speak and text.\n\n"
    "Return ONLY valid JSON (no markdown fences, no extra text) with exactly "
    "this structure:\n"
    '{\n'
    '  "literal_translation": "",\n'
    '  "natural_chinese": "",\n'
    '  "internet_expression": "",\n'
    '  "acg_expression": "",\n'
    '  "pinyin": "",\n'
    '  "culture_note": "",\n'
    '  "example_sentence": "",\n'
    '  "example_translation": ""\n'
    '}\n\n'
)

RULES = (
    "Rules:\n"
    "1. literal_translation: Keep the original English meaning, like a dictionary translation.\n"
    "2. natural_chinese: Translate into how young Chinese people actually chat in real life.\n"
    "3. internet_expression: If Chinese internet has a corresponding meme/slang, USE IT.\n"
    "   Example: 'I'm dead' -> 笑死我了 / 我人没了 / 真的服了 (NOT 我死了)\n"
    "4. acg_expression: If the context involves anime/game/movie culture, use Chinese ACG terms.\n"
    "   Example: tsundere -> 傲娇, yandere -> 病娇, isekai -> 异世界\n"
    "5. pinyin: Provide pinyin for natural_chinese.\n"
    "6. culture_note: Explain the cultural context in simple English.\n"
    "7. example_sentence: A REAL example sentence that young Chinese would actually say.\n"
    "8. example_translation: English translation of the example.\n\n"
    "PRIORITY: Real young Chinese chat language > Internet slang > "
    "ACG expressions > Textbook Chinese.\n"
    "NEVER generate textbook Chinese unless the mode is 'formal'.\n"
)

PROMPTS = {
    "daily": BASE_ROLE
    + "Mode: Daily Conversation\n"
    + "Translate into everyday casual Chinese that friends use on WeChat.\n"
    + RULES,

    "anime": BASE_ROLE
    + "Mode: Anime / Manga\n"
    + "The student loves anime. When translating, prefer Chinese ACG circle "
    + "terminology. Use expressions from anime dubbing, manga translation, "
    + "and ACG fan communities.\n"
    + RULES,

    "movie": BASE_ROLE
    + "Mode: Movie\n"
    + "Translate into Chinese that sounds natural in movie dialogues, "
    + "TV series, and film subtitles. Consider both dubbed and subtitled styles.\n"
    + RULES,

    "game": BASE_ROLE
    + "Mode: Game\n"
    + "Translate into Chinese gaming community language. Consider terms used "
    + "in game localization, Chinese gamer slang (e.g. 开黑, 肝, 氪金), "
    + "and online gaming chat.\n"
    + RULES,

    "internet": BASE_ROLE
    + "Mode: Internet Slang\n"
    + "Translate using Chinese internet slang, memes, and buzzwords. "
    + "Use expressions from Weibo, Douyin, Bilibili, and Chinese social media. "
    + "Examples: 绝绝子, 破防了, 绷不住了, 蚌埠住了, YYDS.\n"
    + RULES,

    "formal": BASE_ROLE
    + "Mode: Formal Expression\n"
    + "Translate into proper, polite Chinese suitable for business, "
    + "academic, or formal settings. Use standard grammar and vocabulary.\n"
    + RULES,
}


# ---------------------------------------------------------------------------
# Translator
# ---------------------------------------------------------------------------

class TranslatorError(Exception):
    pass


def _extract_base_url(api_url: str) -> str:
    url = api_url.strip().rstrip("/")
    if url.endswith("/chat/completions"):
        return url[: -len("/chat/completions")]
    return url


def translate(text: str, category: str = "daily") -> dict:
    """
    Translate English text. Offline cache first, then AI API.

    Args:
        text: English sentence.
        category: One of "daily", "anime", "movie", "game", "internet", "formal".

    Returns:
        Dict with keys: literal_translation, natural_chinese, internet_expression,
        acg_expression, pinyin, culture_note, example_sentence, example_translation,
        usage (token usage), source ("cache" or "api").
    """
    # -- Step 1: Offline lookup --
    cached = search_translation(text, category)
    if cached:
        result = {
            "literal_translation": cached["literal_translation"],
            "natural_chinese": cached["natural_chinese"],
            "internet_expression": cached["internet_expression"],
            "acg_expression": cached["acg_expression"],
            "pinyin": cached["pinyin"],
            "culture_note": cached["culture_note"],
            "example_sentence": cached["example_sentence"],
            "example_translation": cached["example_translation"],
        }
        result["source"] = "cache"
        result["usage"] = {}
        return result

    # -- Step 2: AI API call --
    api_key = get_api_key()
    if not api_key:
        raise TranslatorError(
            "API key is not configured.\n"
            "Please add your API key in config.json or via File > Settings."
        )

    api_url = get_api_url()
    model = get_model()
    base_url = _extract_base_url(api_url)
    prompt = PROMPTS.get(category, PROMPTS["daily"])

    client = OpenAI(api_key=api_key, base_url=base_url)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            temperature=0.7,
            max_tokens=600,
            stream=True,
        )
    except APITimeoutError:
        raise TranslatorError("Request timed out. Please check your network.")
    except APIConnectionError:
        raise TranslatorError(
            "Network connection failed. Please check your internet and API URL."
        )
    except APIError as e:
        raise TranslatorError(f"API error: {e}")
    except Exception as e:
        raise TranslatorError(f"Request failed: {e}")

    # Collect streaming chunks + usage
    full_content = ""
    usage = {}
    try:
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                full_content += chunk.choices[0].delta.content
            if chunk.usage:
                usage = {
                    "prompt_tokens": chunk.usage.prompt_tokens,
                    "completion_tokens": chunk.usage.completion_tokens,
                    "total_tokens": chunk.usage.total_tokens,
                }
    except Exception as e:
        raise TranslatorError(f"Failed to read response stream: {e}")

    if not full_content.strip():
        raise TranslatorError(
            f"The API returned an empty response.\n"
            f"URL: {api_url}\nModel: {model}\n\n"
            "Possible causes:\n"
            "1. The model name is incorrect\n"
            "2. Your API account has insufficient balance\n"
            "3. Check your Settings (File > Settings)"
        )

    # -- Step 3: Parse JSON --
    result = _parse_translation(full_content)
    result["usage"] = usage
    result["source"] = "api"

    # -- Step 4: Save to offline cache --
    save_data = {
        "english": text,
        "category": category,
        **result,
    }
    save_data.pop("usage", None)
    save_data.pop("source", None)
    try:
        save_translation(save_data)
    except Exception:
        pass  # Non-critical; don't interrupt user

    return result


def _parse_translation(content: str) -> dict:
    """Parse JSON from AI response, handling markdown fences gracefully."""
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        first = lines[0].strip()
        start = 1 if first in ("```", "```json") else 1
        if lines[-1].strip() == "```":
            lines = lines[start:-1]
        else:
            lines = lines[start:]
        cleaned = "\n".join(lines).strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        raise TranslatorError(
            "Failed to parse the AI response as JSON.\nFirst 300 chars:\n"
            + cleaned[:300]
        )

    keys = [
        "literal_translation", "natural_chinese", "internet_expression",
        "acg_expression", "pinyin", "culture_note",
        "example_sentence", "example_translation",
    ]
    for k in keys:
        data.setdefault(k, "")

    return data
