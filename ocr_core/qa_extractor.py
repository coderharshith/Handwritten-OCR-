import re
import json
from typing import List, Dict

def extract_qa_from_text(text: str) -> Dict[str, str]:
    """
    Extracts Question Numbers and Answers from a block of text.
    Handles university exam question formats:
      - '1a', '1b', '1c', '2a', '2b', 'Q1a', 'Q.1a', 'Question 1a', '1(a)', '1.a', '1-a'
      - Standalone question headers: 'Question 1:', 'Q1:'
    Ensures enumerated list items inside answers (e.g. '1. State Machine...', '2. Consensus...', '5. E-cash...')
    remain part of the solution rather than creating false questions.
    """
    # Pattern strictly matching genuine question headers
    pattern = re.compile(
        r'^\s*[\"\'\*\#\_\-]*'
        r'(?:'
        r'(?:[Qq]uestion\s*|[Qq]ues\s*|[Qq]\.?\s*|[Aa]ns\.?\s*)?([0-9Il|]{1,2})\s*[\.\-\/]?\s*\(?([a-eA-E])\)?(?![a-zA-Z\-])[\.\:\)\-\s]*'
        r'|'
        r'(?:[Qq]uestion|[Qq]ues|[Qq]\.?)\s*([0-9Il|]{1,2})\s*[\.\:\)]'
        r')'
        r'\s*(.*)$'
    )
    
    qa_dict = {}
    current_q = "Overall"
    current_ans = []
    
    # Page separators
    page_sep_pattern = re.compile(r'^---\s+Page\s+\d+\s+---$')
    
    for raw_line in text.split('\n'):
        line = raw_line.strip()
        if not line or page_sep_pattern.match(line):
            continue
            
        # Skip exam header metadata
        if ('Q.No' in line and 'Solution' in line) or line.startswith('Visvesvaraya') or \
           line.startswith('Scheme & Solutions') or line.startswith('Subject Title') or \
           (line.startswith('Question 1') and 'Full Answers' in line):
            continue
            
        match = pattern.match(line)
        if match:
            # Save accumulated answer for previous question
            if current_q is not None:
                ans_text = "\n".join(current_ans).strip()
                if ans_text:
                    if current_q in qa_dict and qa_dict[current_q]:
                        qa_dict[current_q] += "\n" + ans_text
                    else:
                        qa_dict[current_q] = ans_text
            
            # Determine question identifier
            if match.group(1) and match.group(2):
                q_num = match.group(1).replace('I', '1').replace('l', '1').replace('|', '1')
                q_sub = match.group(2).lower()
                current_q = f"{q_num}{q_sub}"
            elif match.group(3):
                current_q = match.group(3).replace('I', '1').replace('l', '1').replace('|', '1')
            else:
                current_q = "1a"
                
            ans_part = match.group(4) if len(match.groups()) >= 4 else ""
            if ans_part and ans_part.strip():
                clean_ans = re.sub(r'^[\*\#\_]+\s*', '', ans_part.strip())
                current_ans = [clean_ans]
            else:
                current_ans = []
        else:
            if current_q is not None:
                current_ans.append(line)
                
    # Append the last accumulated question
    if current_q is not None:
        ans_text = "\n".join(current_ans).strip()
        if ans_text:
            if current_q in qa_dict and qa_dict[current_q]:
                qa_dict[current_q] += "\n" + ans_text
            else:
                qa_dict[current_q] = ans_text
        
    return qa_dict
        
    return qa_dict

def save_qa_json(qa_dict: Dict[str, str], output_path: str):
    # If the file already exists, we should probably read it and update it 
    # so that multiple scans on the same day append to the same dictionary!
    import os
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if isinstance(existing_data, dict):
                    # Update existing data with new keys, or append to existing keys
                    for k, v in qa_dict.items():
                        if k in existing_data:
                            existing_data[k] += "\n" + v
                        else:
                            existing_data[k] = v
                    qa_dict = existing_data
        except Exception:
            pass # If it fails to read, we'll just overwrite it
            
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(qa_dict, f, indent=2, ensure_ascii=False)


