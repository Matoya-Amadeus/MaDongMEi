#!/usr/bin/env python3
from __future__ import annotations

import re

INTENT_TYPES = ("preference", "temporal", "factual", "multi-session")

_WORD_RE = re.compile(r"[a-z0-9]+")
_RELATIVE_TIME_RE = re.compile(r"\b(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago\b")
_WINDOW_RE = re.compile(r"\b(?:past|last|within)\s+(\d+)\s+(day|days|week|weeks|month|months|year|years)\b")
_NUM_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}
_WINDOW_WORD_RE = re.compile(r"\b(?:past|last|within)\s+(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)\s+(day|days|week|weeks|month|months|year|years)\b")

PREFERENCE_TERMS = {
    "prefer",
    "preference",
    "favorite",
    "favourite",
    "like",
    "liked",
    "love",
    "enjoy",
    "usually",
    "rather",
}

RECOMMENDATION_TERMS = {
    "recommend",
    "recommended",
    "suggest",
    "suggestions",
    "advice",
    "tips",
    "ideas",
}

TEMPORAL_TERMS = {
    "when",
    "before",
    "after",
    "since",
    "until",
    "earliest",
    "latest",
    "today",
    "yesterday",
    "tomorrow",
    "currently",
    "current",
    "recent",
    "recently",
}

SOFT_TEMPORAL_TERMS = {"current", "currently", "recent", "recently", "latest"}

MULTI_SESSION_HINTS = (
    "how many",
    "different types",
    "currently have",
    "currently leading",
    "led or am currently leading",
    "across sessions",
    "multiple sessions",
    "multi-session",
    "from earliest to latest",
    "order of the",
)

ASSISTANT_MEMORY_HINTS = (
    "you suggested",
    "you recommended",
    "you said",
    "you mentioned",
    "you recommend last time",
    "you recommended last time",
    "you provided",
    "you told me",
    "our previous chat",
    "previous chat",
    "can you remind me",
    "what did you",
    "move you made",
    "recommended last time",
    "provided me earlier",
)

ASSISTANT_TURN_HINTS = (
    "you suggested",
    "you said",
    "you mentioned",
    "you recommended last time",
    "you recommend last time",
    "our previous chat",
    "previous chat",
    "can you remind me",
    "could remind me",
    "what did you",
    "move you made",
)

RELATIONAL_HINTS = (
    "how many projects",
    "from whom",
    "what new kitchen gadget did i invest",
    "life event of one of my relatives",
    "how many years older am i than when i graduated",
)

WEEKDAYS = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
}

FOCUS_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "at",
    "can",
    "could",
    "did",
    "do",
    "for",
    "from",
    "get",
    "give",
    "help",
    "i",
    "in",
    "is",
    "it",
    "learn",
    "me",
    "might",
    "more",
    "my",
    "of",
    "on",
    "or",
    "recent",
    "recently",
    "recommend",
    "resources",
    "some",
    "suggest",
    "that",
    "the",
    "to",
    "trip",
    "upcoming",
    "what",
    "where",
    "which",
    "with",
    "you",
}

TEMPORAL_FOCUS_STOPWORDS = FOCUS_STOPWORDS | TEMPORAL_TERMS | {
    "ago",
    "day",
    "days",
    "week",
    "weeks",
    "month",
    "months",
    "year",
    "years",
    "last",
    "past",
    "within",
    "order",
    "earliest",
    "latest",
}

def normalize_text(text: str) -> str:
    return " ".join(_WORD_RE.findall((text or "").lower()))

def word_set(text: str) -> set[str]:
    return set(_WORD_RE.findall((text or "").lower()))

def salient_tokens(text: str, *, temporal: bool = False) -> set[str]:
    words = word_set(text)
    stopwords = TEMPORAL_FOCUS_STOPWORDS if temporal else FOCUS_STOPWORDS
    return {w for w in words if w not in stopwords}

def _contains_phrase(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)

def _assistant_memory_like(text: str) -> bool:
    if _contains_phrase(text, ASSISTANT_MEMORY_HINTS):
        return True
    if "you recommend" not in text and "you suggest" not in text:
        return False
    return bool(
        re.search(
            r"\b(?:previous|earlier|last time|last chat|before|already|did|had|provided|suggested|recommended|mentioned|said|told|remind)\b",
            text,
        )
    )

def _unit_to_days(unit: str, amount: int) -> int:
    unit = unit.lower()
    if unit.startswith("day"):
        return amount
    if unit.startswith("week"):
        return amount * 7
    if unit.startswith("month"):
        return amount * 30
    if unit.startswith("year"):
        return amount * 365
    return amount

def extract_relative_days(query: str) -> int | None:
    qn = normalize_text(query)
    match = _RELATIVE_TIME_RE.search(qn)
    if not match:
        return None
    amount = int(match.group(1))
    return _unit_to_days(match.group(2), amount)

def extract_window_days(query: str) -> int | None:
    qn = normalize_text(query)
    match = _WINDOW_RE.search(qn)
    if match:
        return _unit_to_days(match.group(2), int(match.group(1)))
    match_word = _WINDOW_WORD_RE.search(qn)
    if match_word:
        amount = _NUM_WORDS.get(match_word.group(1), 0)
        if amount > 0:
            return _unit_to_days(match_word.group(2), amount)
    return None

def extract_weekday(query: str) -> str:
    words = word_set(query)
    for day in WEEKDAYS:
        if day in words:
            return day
    return ""

def extract_query_signals(query: str) -> dict:
    qn = normalize_text(query)
    words = set(qn.split())
    has_personal_anchor = bool(words.intersection({"i", "my", "me", "mine", "our"})) or "for my" in qn or "during my" in qn
    hard_preference = bool(words.intersection(PREFERENCE_TERMS))
    recommendation_like = bool(words.intersection(RECOMMENDATION_TERMS))
    assistant_memory = _assistant_memory_like(qn)
    personalized_recommendation = recommendation_like and has_personal_anchor and not assistant_memory
    relative_days = extract_relative_days(query)
    window_days = extract_window_days(query)
    weekday = extract_weekday(query)
    ordering = "earliest" in words or "latest" in words or "order" in words or "chronological" in words
    explicit_temporal = (
        relative_days is not None
        or window_days is not None
        or weekday != ""
        or ordering
        or _contains_phrase(qn, ("as of", "before", "after", "since", "until"))
    )
    counting = "how many" in qn or "number of" in qn or "different types" in qn
    multi_session = counting or _contains_phrase(qn, MULTI_SESSION_HINTS)
    soft_temporal = explicit_temporal or bool(words.intersection(SOFT_TEMPORAL_TERMS))
    advice_like = "any advice" in qn or "any tips" in qn
    relational = _contains_phrase(qn, RELATIONAL_HINTS)
    preference_like = hard_preference or personalized_recommendation
    if not preference_like and recommendation_like and has_personal_anchor and not explicit_temporal:
        preference_like = True
    return {
        "normalized": qn,
        "words": words,
        "has_personal_anchor": has_personal_anchor,
        "preference_like": preference_like,
        "personalized_recommendation": personalized_recommendation,
        "recommendation_like": recommendation_like,
        "advice_like": advice_like,
        "assistant_memory": assistant_memory,
        "relational": relational,
        "relative_days": relative_days,
        "window_days": window_days,
        "weekday": weekday,
        "ordering": ordering,
        "counting": counting,
        "explicit_temporal": explicit_temporal,
        "soft_temporal": soft_temporal,
        "multi_session": multi_session,
    }

def detect_intent(query: str) -> str:
    signals = extract_query_signals(query)
    if signals["preference_like"]:
        return "preference"
    if signals["explicit_temporal"]:
        return "temporal"
    if signals["multi_session"]:
        return "multi-session"
    if signals["soft_temporal"]:
        return "temporal"
    return "factual"

def should_include_assistant_turns(query: str) -> bool:
    qn = normalize_text(query)
    signals = extract_query_signals(query)
    return bool(
        _contains_phrase(qn, ASSISTANT_TURN_HINTS)
        or signals["advice_like"]
        or signals["relational"]
    )
