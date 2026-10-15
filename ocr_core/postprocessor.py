"""
postprocessor.py
────────────────
Deep post-processing pipeline for raw TrOCR output.

Stages (in order):
    1. clean_raw_line()   — strip per-line noise / hallucination artefacts
    2. is_formula_line()  — detect lines that contain maths / formulas
    3. assemble_lines()   — join continuation lines into sentences, group into paragraphs
    4. postprocess_text() — final normalisation pass on a block of text
    5. detect_ocr_issues()/ compute_quality_score() — unchanged quality helpers
"""

import re
import logging
from typing import List

from ocr_core.config import MARK_UNCLEAR, UNCLEAR_MARKER, UNCERTAIN_MARKER

logger = logging.getLogger("ocr")

# ---------------------------------------------------------------------------
# Hallucination / noise patterns produced by TrOCR on unclear handwriting
# ---------------------------------------------------------------------------

# Single lone punctuation / hash lines (e.g. "  # ", "  . ", "  , ")
_RE_LONE_PUNCT = re.compile(r'^\s*[#@|*~`\^&\\]{1,3}\s*$')

# All-uppercase-garbage sequences with dots (e.g. "S.S.S.P.S.S.S.S.P.S.S.")
_RE_DOT_REPEAT = re.compile(r'([A-Z]\.){5,}')

# Runs of the same letter/char 4+ times (e.g. "RUDBURTURNING", "SSSSSSSS")
_RE_CHAR_REPEAT = re.compile(r'([A-Za-z])\1{4,}')

# Runs of the same word 3+ times in a row
_RE_WORD_REPEAT = re.compile(r'\b(\w+)\s+\1\s+\1\b')

# Lines that are mostly punctuation noise (> 40 % punctuation characters)
_PUNCT_CHARS = set('.,!?;:\'"()[]{}<>-#@|*~`^&\\')


def _punct_ratio(text: str) -> float:
    if not text:
        return 0.0
    return sum(1 for c in text if c in _PUNCT_CHARS) / len(text)


def _word_ratio(text: str) -> float:
    """Ratio of real alphabetic words (3+ chars) to total tokens."""
    tokens = text.split()
    if not tokens:
        return 0.0
    real = sum(1 for t in tokens if re.search(r'[a-zA-Z]{2,}', t))
    return real / len(tokens)


# ---------------------------------------------------------------------------
# Stage 1 — Per-line cleaning
# ---------------------------------------------------------------------------

def clean_raw_line(line: str) -> str:
    """
    Clean a single OCR-output line:
    - Strip lone hash / punctuation artefacts
    - Remove repeated dot-letter sequences like H.H.H.H.H.
    - Collapse repeated characters (SSSSSS → S)
    - Remove triple-repeated words
    - Normalize whitespace
    """
    stripped = line.strip()

    # Completely discard lone punctuation lines
    if _RE_LONE_PUNCT.match(stripped):
        return ""

    # Remove dot-repeat garbage inline
    stripped = _RE_DOT_REPEAT.sub("", stripped)

    # Collapse character runs (keep 1)
    stripped = _RE_CHAR_REPEAT.sub(r'\1', stripped)

    # Remove triple-word repetitions
    stripped = _RE_WORD_REPEAT.sub(r'\1', stripped)

    # Normalize whitespace
    stripped = re.sub(r'  +', ' ', stripped).strip()

    # Discard lines that are mostly punctuation noise
    if _punct_ratio(stripped) > 0.45:
        return ""

    # Discard very short lines that are pure symbol garbage
    if len(stripped) <= 3 and not re.search(r'[a-zA-Z0-9]', stripped):
        return ""

    # Discard lines where fewer than 15 % of tokens look like real words
    # (catches things like "RUDBURTURNING" or "VENNY U COUNT")
    if len(stripped) > 8 and _word_ratio(stripped) < 0.15:
        return ""

    return stripped


# ---------------------------------------------------------------------------
# Stage 2 — Formula / block-diagram detection
# ---------------------------------------------------------------------------

_FORMULA_TOKENS = re.compile(
    r'[=\+/\^_²³√∑∫∂≤≥≠∞→←↑↓]|'       # math operators / arrows (removed raw hyphen)
    r'\s+[-*]\s+|'                             # standalone minus or asterisk (e.g. 5 - 3)
    r'\b(log|sin|cos|tan|exp|lim|max|min|det|div|grad|mod)\b|'  # math functions
    r'[A-Za-z]\s*[=]\s*[0-9A-Za-z(]|'       # variable assignment
    r'\d+\s*/\s*\d+|'                        # fraction  2/3
    r'\(\s*[A-Za-z0-9]\s*[+\-*/]\s*[A-Za-z0-9]',  # expression in parens
    re.IGNORECASE
)


def is_formula_line(line: str) -> bool:
    """Return True if this line looks like it contains maths / a formula."""
    return bool(_FORMULA_TOKENS.search(line))


def is_block_diagram_line(line: str) -> bool:
    """Rough heuristic: arrows, boxes described in text, or 'Fig', 'Block', 'Diagram'."""
    lower = line.lower()
    return (
        bool(re.search(r'(→|←|↑|↓|-->|<--|^\s*\||\|\s*$)', line)) or
        bool(re.search(r'\b(fig(ure)?|diagram|block\s+diagram|flow\s*chart)\b', lower))
    )


# ---------------------------------------------------------------------------
# Stage 3 — Assemble cleaned lines into paragraphs
# ---------------------------------------------------------------------------

_SENTENCE_END = re.compile(r'[.?!:]\s*$')


def assemble_lines(line_texts: List[str]) -> str:
    """
    1. Clean every line.
    2. Formula / block-diagram lines are kept as-is (not merged into surrounding text).
    3. Regular lines that do NOT end with punctuation are joined (continuation lines).
    4. Groups of joined sentences are wrapped into paragraphs (blank line separated).
    """
    # ---------- Step A: clean every raw line ----------
    cleaned: List[str] = []
    for raw in line_texts:
        c = clean_raw_line(raw)
        if c:
            cleaned.append(c)

    if not cleaned:
        return ""

    # ---------- Step B: join continuation lines + separate special lines ----------
    groups: List[str] = []   # each element = one logical unit (sentence / formula / diagram)
    buffer = ""

    # Regex to detect question number headers
    _Q_NUM_START = re.compile(
        r'^\s*[\"\'\*\#\_\-]*'
        r'('
        r'(?:[Qq]uestion|[Qq]ues|[Qq]\.?|[Aa]ns\.?)\s*[0-9Il|]{1,2}\s*[a-zA-Z]?\s*[\)\.:]?'
        r'|'
        r'\(?[0-9Il|]{1,2}\s*[\.\-]?\s*[\'\"]?\s*[a-zA-Z]?\s*[\)\.:]'
        r'|'
        r'\(?[0-9Il|]{1,2}\s*[a-zA-Z]\b'
        r'|'
        r'\(?[ivxIVX]{1,4}\s*[\)\.:]'
        r')'
    )

    for line in cleaned:
        if not line:
            if buffer:
                groups.append(buffer.strip())
                buffer = ""
            continue

        is_formula = is_formula_line(line)
        is_diagram = is_block_diagram_line(line)
        is_q_start = bool(_Q_NUM_START.match(line))

        if is_formula or is_diagram or is_q_start:
            # Flush any pending buffer first
            if buffer:
                groups.append(buffer.strip())
                buffer = ""
            # Formula/Diagram/Q-headers start a new logical unit
            if is_q_start or is_formula or is_diagram:
                groups.append(line)
            continue

        # Regular prose line
        if buffer:
            # If the previous buffer ends a sentence, flush it and start fresh
            if _SENTENCE_END.search(buffer):
                groups.append(buffer.strip())
                buffer = line
            else:
                # Continuation — join with a space
                buffer = buffer.rstrip() + " " + line
        else:
            buffer = line

    if buffer:
        groups.append(buffer.strip())

    # ---------- Step C: form paragraphs ----------
    # Separate formula/diagram lines with blank lines; group prose into paragraphs
    paragraphs: List[str] = []
    prose_accum: List[str] = []

    for g in groups:
        if is_formula_line(g) or is_block_diagram_line(g):
            if prose_accum:
                paragraphs.append(" ".join(prose_accum))
                prose_accum = []
            paragraphs.append(g)   # formula on its own paragraph
        else:
            prose_accum.append(g)

    if prose_accum:
        paragraphs.append(" ".join(prose_accum))

    return "\n\n".join(paragraphs).strip()


# ---------------------------------------------------------------------------
# Stage 4 — Final text normalisation
# ---------------------------------------------------------------------------

def postprocess_text(text: str) -> str:
    """
    Final normalisation on a single TrOCR line output:
    - Strip noise characters
    - Fix spacing around common punctuation
    - Ensure sentence ends with a period if it reads like a complete sentence
    """
    text = text.strip()
    if not text:
        return ""

    # Remove stray leading/trailing punctuation that isn't meaningful
    text = re.sub(r'^[#\|@\*~`]+\s*', '', text)
    text = re.sub(r'\s*[#\|@\*~`]+$', '', text)

    # Collapse multiple spaces
    text = re.sub(r'  +', ' ', text)

    # Fix spacing before punctuation  (word ,  → word,)
    text = re.sub(r'\s+([,;:!?.])', r'\1', text)

    # Fix spacing after punctuation when missing  (word.Next → word. Next)
    text = re.sub(r'([.!?])([A-Z])', r'\1 \2', text)

    # Remove null bytes
    text = text.replace('\0', '')

    return text.strip()


# ---------------------------------------------------------------------------
# Quality helpers (unchanged API)
# ---------------------------------------------------------------------------

def detect_ocr_issues(text: str) -> List[str]:
    issues = []

    if not text:
        issues.append("OCR produced no output. The image may be blank or unreadable.")
        return issues

    if len(text) < 2:
        issues.append("Suspiciously short output detected.")

    if _RE_CHAR_REPEAT.search(text):
        issues.append("Unusual repeated characters detected.")

    if _RE_WORD_REPEAT.search(text):
        issues.append("Repeated words detected.")

    if _punct_ratio(text) > 0.3:
        issues.append("Excessive punctuation in output.")

    if re.search(r'[\x01-\x1f\x7f]', text):
        issues.append("Unusual character sequences detected.")

    return issues


def assess_text_quality(text: str) -> float:
    if not text:
        return 0.0
    issues = detect_ocr_issues(text)
    score = 1.0 - (len(issues) * 0.2)
    return max(0.0, min(1.0, score))


def compute_quality_score(image_quality: dict, text: str, processing_time: float = 0.0) -> float:
    img_score = image_quality.get('overall', image_quality.get('quality', 0.5))
    txt_score = assess_text_quality(text)

    length_quality = 1.0
    if len(text) < 3:
        length_quality = 0.2
    elif len(text) > 100:
        length_quality = 0.8

    overall_score = (img_score * 0.4) + (txt_score * 0.4) + (length_quality * 0.2)
    logger.debug(f"Estimated Recognition Quality: {overall_score:.2f}")
    return overall_score
