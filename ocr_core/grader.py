import re
import difflib
from typing import Dict, Any, List

def normalize_qnum(q: str) -> str:
    """Normalize question number (e.g., 'Q.1a', '1a)', 'Q1(a)' -> '1a')."""
    if not q:
        return ""
    q_clean = q.lower().strip()
    q_clean = re.sub(r'^(question|ques|q\.?|ans\.?)\s*', '', q_clean)
    q_clean = re.sub(r'[^a-z0-9]', '', q_clean)
    return q_clean

def extract_keywords(text: str) -> list:
    """Extract significant keywords from text by removing stop words and punctuation."""
    if not text:
        return []
    cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
    words = cleaned.split()
    
    stopwords = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "but", 
        "in", "on", "at", "to", "for", "with", "by", "of", "this", "that",
        "it", "as", "be", "from", "which", "what", "how", "when", "where",
        "explain", "define", "describe", "discuss", "write", "about", "note"
    }
                 
    keywords = list(set([w for w in words if len(w) > 2 and w not in stopwords]))
    return keywords

def segment_document_chunks(full_text: str) -> List[dict]:
    """Segment document text into pages or distinct topical sections."""
    pages = []
    current_lines = []
    current_page = 1
    has_page_markers = bool(re.search(r'^---\s*Page\s*\d+\s*---', full_text, re.MULTILINE | re.IGNORECASE))
    if has_page_markers:
        for line in full_text.split('\n'):
            m = re.match(r'^---\s*Page\s*(\d+)\s*---', line.strip(), re.IGNORECASE)
            if m:
                if current_lines:
                    text_content = "\n".join(current_lines).strip()
                    if len(text_content) > 10:
                        pages.append({"id": f"Page {current_page}", "text": text_content})
                    current_lines = []
                current_page = int(m.group(1))
            else:
                if line.strip():
                    current_lines.append(line)
        if current_lines:
            text_content = "\n".join(current_lines).strip()
            if len(text_content) > 10:
                pages.append({"id": f"Page {current_page}", "text": text_content})
    else:
        paragraphs = [p.strip() for p in full_text.split('\n\n') if len(p.strip()) > 30]
        if paragraphs:
            for idx, p in enumerate(paragraphs):
                pages.append({"id": f"Section {idx+1}", "text": p})
        else:
            if full_text.strip():
                pages = [{"id": "Document", "text": full_text.strip()}]
    return pages

def assign_chunks_to_questions(chunks: List[dict], answer_key: Dict[str, str]) -> Dict[str, str]:
    """
    Assign document chunks / pages to the best-matching question in the answer key.
    Each page/chunk is assigned exclusively to the question it matches best.
    """
    assigned = {q: [] for q in answer_key if q.lower() != "overall"}
    q_kws = {q: extract_keywords(ans) for q, ans in answer_key.items() if q.lower() != "overall"}
    
    for c in chunks:
        c_kws = extract_keywords(c["text"])
        if not c_kws:
            continue
            
        best_q = None
        best_count = 0
        best_pct = 0.0
        
        for q, kws in q_kws.items():
            if not kws:
                continue
            matched = sum(1 for kw in kws if any(kw == ckw or difflib.SequenceMatcher(None, kw, ckw).ratio() >= 0.75 for ckw in c_kws))
            pct = matched / len(kws) if kws else 0.0
            if matched > best_count:
                best_count = matched
                best_pct = pct
                best_q = q
                
        # Confidence threshold: at least 15 keywords and 20% overlap
        if best_q and best_count >= 15 and best_pct >= 0.20:
            assigned[best_q].append(c["text"])
            
    return {q: "\n\n".join(texts) for q, texts in assigned.items()}

def evaluate_answers(student_qa: Dict[str, str], answer_key: Dict[str, str], student_filename: str, full_student_text: str = "") -> Dict[str, Any]:
    """
    Compare student answers strictly to the answer key using Question Number matching.
    If student answers are unstructured, falls back to document-level page/section assignment.
    Awards 0 marks and marks as 'No answer recorded' if a question was not answered by the student.
    """
    results = []
    total_marks = 0.0
    
    # Pre-build normalized lookup table for student QA
    normalized_student_qa = {}
    for q_raw, ans_raw in student_qa.items():
        if not ans_raw or not ans_raw.strip():
            continue
        if q_raw.lower() == "overall":
            continue
        norm_key = normalize_qnum(q_raw)
        if norm_key:
            normalized_student_qa[norm_key] = ans_raw.strip()
            
    has_explicit_student_qnums = len(normalized_student_qa) > 0
    if not full_student_text:
        full_student_text = "\n".join(student_qa.values()) if student_qa else ""
    
    # Fallback: if student handwriting did not yield explicit question headers,
    # segment booklet into pages/sections and match to answer key questions
    if not has_explicit_student_qnums and full_student_text:
        chunks = segment_document_chunks(full_student_text)
        assigned_qa = assign_chunks_to_questions(chunks, answer_key)
        for q, ans in assigned_qa.items():
            if ans and len(ans.strip()) > 10:
                normalized_student_qa[normalize_qnum(q)] = ans.strip()
    
    for qnum_raw, key_text_raw in answer_key.items():
        if qnum_raw.lower() == "overall":
            continue
            
        max_marks = 10.0
        key_text = key_text_raw.strip()
        
        # Check for marks allocated at end (e.g., '10 Marks', '(10)', '\n10\n')
        marks_match = re.search(r'(?:[\(\[\{]|\n|^|\s)(\d+(?:\.\d+)?)\s*(?:marks?|m)?[\)\]\}]?\s*$', key_text, re.IGNORECASE)
        if marks_match:
            try:
                val = float(marks_match.group(1))
                if 1.0 <= val <= 100.0:
                    max_marks = val
                    key_text = key_text[:marks_match.start()].strip()
            except ValueError:
                pass
                
        # Extract clean concise question title (first line without trailing mark indicators)
        lines = [l.strip() for l in key_text.split('\n') if l.strip()]
        question_title = lines[0] if lines else f"Question {qnum_raw}"
        question_title = re.sub(r'[\(\[\{]?\s*\d+(?:\.\d+)?\s*(?:marks?|m)?\s*[\)\]\}]?\s*$', '', question_title, flags=re.IGNORECASE).strip()
        if not question_title:
            question_title = f"Question {qnum_raw}"
            
        key_keywords = extract_keywords(key_text)
        norm_q = normalize_qnum(qnum_raw)
        
        student_text = ""
        
        # 1. Direct question match by normalized number
        if norm_q in normalized_student_qa and len(normalized_student_qa[norm_q]) > 5:
            student_text = normalized_student_qa[norm_q]
        else:
            # Check prefix/suffix matches (e.g. '1a' vs 'q1a')
            for s_norm, s_ans in normalized_student_qa.items():
                if (norm_q.endswith(s_norm) or s_norm.endswith(norm_q)) and len(s_ans) > 5:
                    student_text = s_ans
                    break
                    
        matched_keywords = []
        
        # Check if student actually wrote an answer
        if student_text and len(student_text.strip()) > 5 and student_text.strip().lower() not in ("no answer recorded", "none", "n/a"):
            student_keywords = extract_keywords(student_text)
            
            if len(key_keywords) > 0:
                match_count = 0
                for key_kw in key_keywords:
                    best_ratio = 0.0
                    best_match = None
                    for stu_kw in student_keywords:
                        ratio = difflib.SequenceMatcher(None, key_kw, stu_kw).ratio()
                        if ratio > best_ratio:
                            best_ratio = ratio
                            best_match = stu_kw
                    
                    if best_ratio >= 0.70:
                        match_count += 1
                        if key_kw == best_match:
                            matched_keywords.append(key_kw)
                        else:
                            matched_keywords.append(f"{key_kw} (~'{best_match}')")
                            
                score_ratio = match_count / len(key_keywords)
            else:
                score_ratio = 1.0 if len(student_keywords) > 0 else 0.0
                
            marks = round(min(score_ratio * max_marks, max_marks), 1)
            total_marks += marks
            
            summary = f"Matched {len(matched_keywords)} of {len(key_keywords)} key concepts."
        else:
            # Student did not write this question - award 0 marks
            marks = 0.0
            student_text = "No answer recorded"
            summary = f"Question {qnum_raw} not answered by student."
            
        results.append({
            "question_number": qnum_raw,
            "question_text": question_title,
            "student_answer": student_text.strip(),
            "marks": marks,
            "max_marks": max_marks,
            "matched_keywords": matched_keywords,
            "summary": summary
        })
            
    return {
        "file_name": student_filename,
        "total_marks": round(total_marks, 1),
        "evaluation": results
    }
