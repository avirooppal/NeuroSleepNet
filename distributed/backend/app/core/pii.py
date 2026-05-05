"""
PII Detection and Redaction.

Default-on. Detects emails, phone numbers, SSNs, credit cards, and IP addresses
using regex patterns. Each detected span is replaced with a typed label:
  [REDACTED:EMAIL], [REDACTED:PHONE], [REDACTED:SSN], [REDACTED:CC], [REDACTED:IP]

Optionally integrates presidio-analyzer for named-entity PII (persons, locations).
Falls back to regex-only if presidio is not installed — never crashes.

Custom domain PII is supported via the `filter_fn` parameter passed from nsn.init().
"""
import re
import logging
import os
from typing import Optional, Callable

logger = logging.getLogger(__name__)

# ── Regex patterns ────────────────────────────────────────────────────────────

_PATTERNS = [
    # Email
    (re.compile(r'[\w._%+\-]+@[\w.\-]+\.[A-Za-z]{2,}'), "[REDACTED:EMAIL]"),
    # US Phone (with/without dashes, dots, parens)
    (re.compile(r'\b(\+1[\s.\-]?)?(\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4})\b'), "[REDACTED:PHONE]"),
    # SSN
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "[REDACTED:SSN]"),
    # Credit card (major patterns — 13-16 digits with optional spaces/dashes)
    (re.compile(r'\b(?:\d[ \-]?){13,16}\b'), "[REDACTED:CC]"),
    # IPv4
    (re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'), "[REDACTED:IP]"),
]

# ── Optional presidio integration ─────────────────────────────────────────────

_presidio_analyzer = None

def _get_presidio():
    global _presidio_analyzer
    if _presidio_analyzer is not None:
        return _presidio_analyzer
    try:
        from presidio_analyzer import AnalyzerEngine
        _presidio_analyzer = AnalyzerEngine()
        logger.info("[NSN PII] presidio-analyzer loaded — enhanced NER PII detection active.")
    except ImportError:
        _presidio_analyzer = False  # Sentinel: tried and unavailable
        logger.debug("[NSN PII] presidio-analyzer not installed — using regex-only PII detection.")
    return _presidio_analyzer


def _presidio_redact(text: str) -> str:
    """Run presidio NER-based detection on top of regex pass."""
    analyzer = _get_presidio()
    if not analyzer:
        return text

    try:
        from presidio_anonymizer import AnonymizerEngine
        from presidio_anonymizer.entities import OperatorConfig
        anonymizer = AnonymizerEngine()
        results = analyzer.analyze(text=text, language="en")
        if not results:
            return text
        anonymized = anonymizer.anonymize(
            text=text,
            analyzer_results=results,
            operators={
                "PERSON": OperatorConfig("replace", {"new_value": "[REDACTED:PERSON]"}),
                "EMAIL_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED:EMAIL]"}),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "[REDACTED:PHONE]"}),
                "CREDIT_CARD": OperatorConfig("replace", {"new_value": "[REDACTED:CC]"}),
                "US_SSN": OperatorConfig("replace", {"new_value": "[REDACTED:SSN]"}),
                "IP_ADDRESS": OperatorConfig("replace", {"new_value": "[REDACTED:IP]"}),
            }
        )
        return anonymized.text
    except Exception as e:
        logger.warning(f"[NSN PII] presidio redaction failed: {e} — falling back to regex result.")
        return text


def redact_pii(
    text: str,
    enabled: bool = True,
    filter_fn: Optional[Callable[[str], bool]] = None
) -> str:
    """
    Detect and redact PII from text before storage.

    Args:
        text:       Raw memory content to sanitise.
        enabled:    Mirrors nsn.init(pii_detection=...). Default True.
        filter_fn:  Custom callable filter_fn(content) -> bool.
                    If returns False, the content is blocked entirely.
                    Use for domain-specific secrets (e.g., "SECRET:" prefix).

    Returns:
        Sanitised string with PII replaced by typed labels.
    """
    if not text:
        return text

    pii_on = enabled and os.environ.get("NSN_PII_DETECTION_ENABLED", "true").lower() != "false"

    # Custom filter — block content entirely if filter returns False
    if filter_fn is not None:
        try:
            if not filter_fn(text):
                logger.debug("[NSN PII] Content blocked by custom filter_fn.")
                return "[CONTENT BLOCKED BY FILTER]"
        except Exception as e:
            logger.warning(f"[NSN PII] filter_fn raised: {e} — content allowed through.")

    if not pii_on:
        return text

    # 1. Regex pass (always runs — fast, no dependencies)
    for pattern, label in _PATTERNS:
        text = pattern.sub(label, text)

    # 2. Presidio NER pass (runs if installed)
    text = _presidio_redact(text)

    return text
