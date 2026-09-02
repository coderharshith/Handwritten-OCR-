import re
import logging
from typing import List

from app.config import MARK_UNCLEAR, UNCLEAR_MARKER, UNCERTAIN_MARKER

logger = logging.getLogger("ocr")

def postprocess_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r' +', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = text.replace('\0', '')
    return text

def detect_ocr_issues(text: str) -> List[str]:
    issues = []
    
    if not text:
        issues.append("OCR produced no output. The image may be blank or unreadable.")
        return issues
        
    if len(text) < 2:
        issues.append("Suspiciously short output detected.")
        
    if re.search(r'(.)\1{3,}', text):
        match = re.search(r'(.)\1{3,}', text)
        issues.append(f"Unusual repeated characters detected: '{match.group(1)}'")
        
    words = text.split()
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            issues.append(f"Repeated words detected: '{words[i]}'")
            break
            
    punctuation_count = sum(1 for c in text if c in '.,!?;:"\'()[]{}<>-')
    if len(text) > 0 and (punctuation_count / len(text)) > 0.3:
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
    img_score = image_quality.get('overall', 0.5)
    txt_score = assess_text_quality(text)
    
    length_quality = 1.0
    if len(text) < 3:
        length_quality = 0.2
    elif len(text) > 100:
        length_quality = 0.8
        
    overall_score = (img_score * 0.4) + (txt_score * 0.4) + (length_quality * 0.2)
    logger.debug(f"Estimated Recognition Quality: {overall_score:.2f}")
    return overall_score

def assemble_lines(line_texts: list) -> str:
    text = "\n".join([t for t in line_texts if t])
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()
