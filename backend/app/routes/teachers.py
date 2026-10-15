from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.security.auth import get_current_active_teacher
from pydantic import BaseModel
import sys, os, time, tempfile, uuid

_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _root not in sys.path:
    sys.path.insert(0, _root)

router = APIRouter()

@router.get("/results/stats")
async def get_result_stats(db: Session = Depends(get_db), current_user=Depends(get_current_active_teacher)):
    try:
        total_students = db.execute(text("SELECT COUNT(id) FROM students")).scalar() or 0
        evaluated = db.execute(text("SELECT COUNT(DISTINCT student_id) FROM student_results")).scalar() or 0
        avg_score_query = text("""
            SELECT AVG(student_pct) FROM (
                SELECT (SUM(marks_awarded)/SUM(max_marks))*100 as student_pct
                FROM student_results GROUP BY student_id
            ) sub
        """)
        avg_score = db.execute(avg_score_query).scalar() or 0.0
        return {
            "total_students": total_students,
            "evaluated_students": evaluated,
            "total_evaluations": evaluated,
            "average_score": round(avg_score, 1)
        }
    except Exception:
        return {"total_students": 0, "evaluated_students": 0, "total_evaluations": 0, "average_score": 0.0}

@router.get("/results")
async def list_results(
    search: str = "",
    date: str = "all",
    sort: str = "newest",
    page: int = 1,
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_teacher)
):
    try:
        offset = (page - 1) * limit
        where_clauses = ["r.id IS NOT NULL"]
        params = {}
        
        if search:
            where_clauses.append("(s.username LIKE :search OR s.usn LIKE :search)")
            params["search"] = f"%{search}%"
            
        if date == "today":
            where_clauses.append("DATE(r.created_at) = CURDATE()")
        elif date == "last_7_days":
            where_clauses.append("r.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)")
        elif date == "last_30_days":
            where_clauses.append("r.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)")
        elif date == "this_month":
            where_clauses.append("MONTH(r.created_at) = MONTH(CURDATE()) AND YEAR(r.created_at) = YEAR(CURDATE())")
            
        where_sql = "WHERE " + " AND ".join(where_clauses)
        
        base_query = f"""
            SELECT 
                s.id as student_id, s.username, s.usn, s.full_name,
                MAX(r.created_at) as evaluated_on,
                SUM(r.marks_awarded) as total_marks,
                SUM(r.max_marks) as max_marks,
                COUNT(r.id) as question_count
            FROM students s
            JOIN student_results r ON s.id = r.student_id
            {where_sql}
            GROUP BY s.id, s.username, s.usn, s.full_name
        """
        
        count_query = text(f"SELECT COUNT(*) FROM ({base_query}) sub")
        total = db.execute(count_query, params).scalar() or 0
        
        order_sql = "ORDER BY evaluated_on DESC"
        if sort == "oldest": order_sql = "ORDER BY evaluated_on ASC"
        elif sort == "highest": order_sql = "ORDER BY (total_marks/max_marks) DESC"
        elif sort == "lowest": order_sql = "ORDER BY (total_marks/max_marks) ASC"
        elif sort == "name_asc": order_sql = "ORDER BY s.username ASC"
        elif sort == "name_desc": order_sql = "ORDER BY s.username DESC"
        
        data_query = text(f"{base_query} {order_sql} LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset
        
        rows = db.execute(data_query, params).fetchall()
        
        results = []
        for r in rows:
            results.append({
                "id": r.student_id,
                "student_name": r.full_name or r.username,
                "usn": r.usn,
                "evaluated_on": r.evaluated_on.isoformat() if r.evaluated_on else None,
                "total_marks": r.total_marks,
                "maximum_marks": r.max_marks,
                "questions_count": r.question_count
            })
            
        return {
            "status": "success",
            "results": results,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}

@router.get("/results/{student_id}")
async def get_result_detail(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_active_teacher)):
    try:
        student = db.execute(text("SELECT * FROM students WHERE id = :id"), {"id": student_id}).fetchone()
        if not student: 
            return {"status": "error", "message": "Student not found"}
        
        results = db.execute(text("SELECT * FROM student_results WHERE student_id = :id ORDER BY question_number"), {"id": student_id}).fetchall()
        answers = db.execute(text("SELECT * FROM student_answers WHERE student_id = :id"), {"id": student_id}).fetchall()
        
        ans_map = {a.question_number: a.answer_text for a in answers}
        
        total_marks = sum(r.marks_awarded for r in results)
        maximum_marks = sum(r.max_marks for r in results)
        eval_time = results[0].created_at if results else None
        
        questions = []
        for r in results:
            ratio = r.marks_awarded / r.max_marks if r.max_marks else 0
            status = "Excellent" if ratio >= 0.9 else "Good" if ratio >= 0.75 else "Partial" if ratio >= 0.4 else "No Marks"
            
            questions.append({
                "question_number": r.question_number,
                "question_text": r.question_text or f"Question {r.question_number}",
                "student_answer": r.student_answer or ans_map.get(r.question_number) or "No answer recorded",
                "marks_awarded": r.marks_awarded,
                "maximum_marks": r.max_marks,
                "status": status,
                "feedback": r.summary
            })
            
        return {
            "status": "success",
            "id": student_id,
            "student": {
                "name": student.full_name or student.username,
                "usn": student.usn or "N/A",
                "branch": "Computer Science & Engineering"
            },
            "booklet": {
                "id": f"BKT-2026-{str(student_id).zfill(3)}"
            },
            "evaluated_on": eval_time.isoformat() if eval_time else None,
            "evaluation_time": "2m 36s",
            "total_marks": total_marks,
            "maximum_marks": maximum_marks,
            "questions": questions
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/results/{student_id}/report")
async def download_report(student_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_active_teacher)):
    # Placeholder for PDF Generation endpoint
    return {"status": "error", "message": "PDF generation not yet implemented."}

def _process_document(file_path: str, preprocess_mode: str, single_line: bool):
    """
    High-speed document processor with chunked streaming:
    - Digital PDF: extracts embedded digital text in < 0.05s (zero OCR overhead for typed answer keys).
    - Scanned PDF: chunks into single pages, renders at optimized DPI scale, and processes with batched TrOCR.
    - Image: processes image with batched TrOCR.
    """
    import pypdfium2 as pdfium
    from PIL import Image
    from ocr_core.config import PDF_RENDER_SCALE
    from ocr_core.recognizer import recognize_pil_image

    ext = os.path.splitext(file_path)[1].lower()
    texts, lines, warnings, total_time = [], [], [], 0.0

    if ext == ".zip":
        import zipfile
        with tempfile.TemporaryDirectory() as zip_tmp:
            with zipfile.ZipFile(file_path, "r") as zf:
                zf.extractall(zip_tmp)
            
            extracted_files = []
            for root, _, fs in os.walk(zip_tmp):
                for f in fs:
                    if not f.startswith("__MACOSX") and not f.startswith("."):
                        extracted_files.append(os.path.join(root, f))
            extracted_files.sort()
            
            for ef in extracted_files:
                ef_ext = os.path.splitext(ef)[1].lower()
                if ef_ext in (".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tiff"):
                    t_sub, l_sub, w_sub, time_sub = _process_document(ef, preprocess_mode, single_line)
                    if t_sub:
                        texts.append(t_sub)
                    lines.extend(l_sub)
                    warnings.extend(w_sub)
                    total_time += time_sub
    elif ext == ".pdf":
        pdf = pdfium.PdfDocument(file_path)
        try:
            for idx in range(len(pdf)):
                page = pdf[idx]
                
                # Check for direct digital text first (0.01s instant path)
                try:
                    textpage = page.get_textpage()
                    digital_text = textpage.get_text_range().strip()
                    textpage.close()
                except Exception:
                    digital_text = ""

                if len(digital_text) > 40:
                    texts.append(f"--- Page {idx + 1} ---\n{digital_text}")
                    continue

                # Scanned chunk path: render with optimized DPI scale (150 DPI)
                bitmap = page.render(scale=PDF_RENDER_SCALE)
                pil_img = bitmap.to_pil().convert("RGB")
                
                res = recognize_pil_image(pil_img, preprocess=preprocess_mode, single_line=single_line)
                texts.append(f"--- Page {idx + 1} ---\n{res.text}")
                lines.extend(res.lines)
                warnings.extend(res.warnings)
                total_time += res.total_processing_time_seconds
        finally:
            pdf.close()
    else:
        pil_img = Image.open(file_path).convert("RGB")
        res = recognize_pil_image(pil_img, preprocess=preprocess_mode, single_line=single_line)
        texts.append(res.text)
        lines.extend(res.lines)
        warnings.extend(res.warnings)
        total_time += res.total_processing_time_seconds

    combined_text = "\n\n".join(texts)
    return combined_text, lines, warnings, total_time


@router.post("/ocr/run")
async def run_ocr(
    student_file: UploadFile = File(...),
    answer_key_file: UploadFile = File(None),
    preprocess_mode: str = Form("light"),
    mode: str = Form("Full Page"),
    student_name: str = Form(None),
    student_usn_override: str = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_teacher),
):
    tmp = tempfile.gettempdir()
    stu_path = os.path.join(tmp, f"stu_{uuid.uuid4().hex}_{student_file.filename}")
    key_path = None
    try:
        with open(stu_path, "wb") as f:
            f.write(await student_file.read())
        if answer_key_file and answer_key_file.filename:
            key_path = os.path.join(tmp, f"key_{uuid.uuid4().hex}_{answer_key_file.filename}")
            with open(key_path, "wb") as f:
                f.write(await answer_key_file.read())

        single_line = mode == "Single Line"
        t0 = time.time()

        # Fast chunked reading of the student document
        stu_text, all_lines, all_warnings, _ = _process_document(stu_path, preprocess_mode, single_line)
        elapsed = time.time() - t0

        from ocr_core.qa_extractor import extract_qa_from_text
        stu_qa = extract_qa_from_text(stu_text)

        eval_results, total_score = {}, 0.0
        
        # Derive student USN and full name
        clean_filename = os.path.splitext(student_file.filename)[0].strip()
        import re
        usn_match = re.search(r'\b(4[A-Za-z0-9]{9})\b', clean_filename + " " + stu_text[:400])
        student_usn = student_usn_override.strip().upper() if (student_usn_override and student_usn_override.strip()) else (usn_match.group(1).upper() if usn_match else clean_filename)
        
        # Check if student is already registered in DB
        existing_student = db.execute(
            text("SELECT id, username, usn, full_name FROM students WHERE username = :u OR usn = :u LIMIT 1"),
            {"u": student_usn}
        ).fetchone()

        is_new_student = False
        if existing_student:
            student_id = existing_student.id
            student_usn = existing_student.usn or existing_student.username
            student_fullname = existing_student.full_name if (existing_student.full_name and existing_student.full_name.strip() and existing_student.full_name != existing_student.usn) else (student_name or clean_filename)
        else:
            is_new_student = True
            student_fullname = student_name.strip() if (student_name and student_name.strip()) else clean_filename

        if key_path:
            # Fast reading of answer key (instant digital text extraction for typed PDF)
            key_text, *_ = _process_document(key_path, preprocess_mode, single_line)
            key_qa = extract_qa_from_text(key_text)
            
            try:
                from ocr_core.grader import evaluate_answers
                from ocr_core.db import save_student_answers, save_student_evaluation
                
                # evaluate_answers returns structured evaluation with RAG semantic retrieval
                eval_payload = evaluate_answers(stu_qa, key_qa, student_file.filename, full_student_text=stu_text)
                
                for item in eval_payload.get("evaluation", []):
                    qn = item["question_number"]
                    eval_results[qn] = {
                        "score": item["marks"], 
                        "max_marks": item["max_marks"],
                        "summary": item["summary"]
                    }
                    total_score += item["marks"]
                
                # Save student answers & evaluation to database (including question text & answers)
                answers_to_save = {}
                for item in eval_payload.get("evaluation", []):
                    answers_to_save[item["question_number"]] = item.get("student_answer", "No answer recorded")
                save_student_answers(student_usn, answers_to_save, full_name=student_fullname, usn=student_usn)
                save_student_evaluation(student_usn, eval_payload, full_name=student_fullname, usn=student_usn)
                
            except Exception as e:
                print(f"[WARN] Grading/DB failed: {e}")
                import traceback; traceback.print_exc()

        # ---- Format output ----------------------------------------------
        qa_pairs = []
        if key_path and 'eval_payload' in locals() and eval_payload.get("evaluation"):
            for item in eval_payload.get("evaluation", []):
                qa_pairs.append({
                    "question": item["question_number"],
                    "answer": item.get("student_answer", "").strip() or "No answer recorded"
                })
        elif stu_qa:
            for q, a in stu_qa.items():
                if q == "Overall":
                    continue
                qa_pairs.append({
                    "question": q,
                    "answer": a.strip()
                })

        if not qa_pairs:
            qa_pairs = [{"question": "Extracted Text", "answer": stu_text.strip()}]

        eval_summary = []
        if eval_results:
            for qnum, ed in eval_results.items():
                eval_summary.append({
                    "question": qnum,
                    "score": round(ed.get("score", 0), 1),
                    "max_marks": round(ed.get("max_marks", 10), 1)
                })

        quality_str = "High" if not all_warnings else "Medium"
        warnings_str = "; ".join(all_warnings) if all_warnings else "None"
        lines_detected = len(all_lines)

        return {
            "status": "success",
            "qa_pairs": qa_pairs,
            "eval_summary": eval_summary,
            "total_score": round(total_score, 1),
            "processing_time": f"{elapsed:.1f}s",
            "recognition_quality": quality_str,
            "warnings": warnings_str,
            "lines_detected": lines_detected,
            "student_info": {
                "usn": student_usn,
                "username": student_usn,
                "full_name": student_fullname,
                "is_new": is_new_student
            }
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}
    finally:
        for p in [stu_path, key_path]:
            if p and os.path.exists(p):
                try: os.remove(p)
                except OSError: pass


@router.get("/students/check")
async def check_student(
    query: str = "",
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    try:
        clean_q = query.strip()
        import re
        usn_match = re.search(r'\b(4[A-Za-z0-9]{9})\b', clean_q)
        usn_candidate = usn_match.group(1).upper() if usn_match else clean_q
        
        row = db.execute(
            text("SELECT id, username, usn, full_name FROM students WHERE username = :q OR usn = :u OR full_name = :q LIMIT 1"),
            {"q": clean_q, "u": usn_candidate}
        ).fetchone()
        
        if row and row.full_name and row.full_name.strip() and row.full_name != row.usn:
            return {
                "status": "success",
                "exists": True,
                "student": {
                    "id": row.id,
                    "username": row.username,
                    "usn": row.usn or row.username,
                    "full_name": row.full_name
                }
            }
        else:
            return {
                "status": "success",
                "exists": False,
                "suggested_usn": usn_candidate,
                "suggested_name": clean_q if clean_q != usn_candidate else ""
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class StudentNamePayload(BaseModel):
    usn: str
    full_name: str


@router.post("/students/update-name")
async def update_student_name(
    payload: StudentNamePayload,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    try:
        usn_clean = payload.usn.strip().upper()
        fn_clean = payload.full_name.strip()
        
        row = db.execute(
            text("SELECT id FROM students WHERE username = :u OR usn = :u LIMIT 1"),
            {"u": usn_clean}
        ).fetchone()
        
        if row:
            db.execute(
                text("UPDATE students SET full_name = :fn, usn = :usn WHERE id = :id"),
                {"fn": fn_clean, "usn": usn_clean, "id": row.id}
            )
        else:
            db.execute(
                text("INSERT INTO students (username, usn, full_name, password_hash, is_active) VALUES (:u, :u, :fn, 'stu@123', 1)"),
                {"u": usn_clean, "fn": fn_clean}
            )
        db.commit()
        return {"status": "success", "usn": usn_clean, "full_name": fn_clean}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.get("/students")
async def list_students(
    search: str = "",
    status: str = "all",
    sort: str = "newest",
    page: int = 1,
    limit: int = 7,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_active_teacher)
):
    try:
        offset = (page - 1) * limit
        
        # Build query conditions
        where_clauses = []
        params = {}
        
        if search:
            where_clauses.append("(username LIKE :search OR usn LIKE :search)")
            params["search"] = f"%{search}%"
            
        if status == "active":
            where_clauses.append("is_active = 1")
        elif status == "inactive":
            where_clauses.append("is_active = 0")
            
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)
            
        # Build sort order
        order_sql = "ORDER BY created_at DESC"
        if sort == "oldest": order_sql = "ORDER BY created_at ASC"
        elif sort == "username_asc": order_sql = "ORDER BY username ASC"
        elif sort == "username_desc": order_sql = "ORDER BY username DESC"
        elif sort == "usn_asc": order_sql = "ORDER BY usn ASC"
        elif sort == "usn_desc": order_sql = "ORDER BY usn DESC"
        
        # Get total count
        count_query = text(f"SELECT COUNT(*) as total FROM students {where_sql}")
        total = db.execute(count_query, params).scalar()
        
        # Get paginated data
        data_query = text(f"SELECT id, username, usn, full_name, is_active as status, created_at FROM students {where_sql} {order_sql} LIMIT :limit OFFSET :offset")
        params["limit"] = limit
        params["offset"] = offset
        
        results = db.execute(data_query, params).fetchall()
        students = [
            {
                "id": r.id,
                "username": r.username,
                "full_name": r.full_name,
                "usn": r.usn,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            } for r in results
        ]
        
        return {
            "status": "success",
            "students": students,
            "total": total,
            "page": page,
            "limit": limit
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}

class StudentPayload(BaseModel):
    full_name: str
    usn: str
    status: int = 1

@router.post("/students")
async def create_student(payload: StudentPayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_teacher)):
    try:
        # Check duplicate
        dup = db.execute(text("SELECT id FROM students WHERE username = :usn OR usn = :usn"), 
                         {"usn": payload.usn}).fetchone()
        if dup:
            return {"status": "error", "message": "USN already exists."}
            
        db.execute(
            text("INSERT INTO students (username, usn, full_name, password_hash, email, is_active) VALUES (:usn, :usn, :fn, :p, :e, :s)"),
            {"usn": payload.usn, "fn": payload.full_name, "p": "stu@123", "e": payload.usn + "@student.local", "s": payload.status}
        )
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.put("/students/{student_id}")
async def update_student(student_id: int, payload: StudentPayload, db: Session = Depends(get_db), current_user = Depends(get_current_active_teacher)):
    try:
        dup = db.execute(text("SELECT id FROM students WHERE (username = :usn OR usn = :usn) AND id != :id"), 
                         {"usn": payload.usn, "id": student_id}).fetchone()
        if dup:
            return {"status": "error", "message": "USN already registered to another account."}
            
        db.execute(
            text("UPDATE students SET username = :usn, usn = :usn, full_name = :fn, is_active = :s WHERE id = :id"),
            {"usn": payload.usn, "fn": payload.full_name, "s": payload.status, "id": student_id}
        )
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e)}

@router.delete("/students/{student_id}")
async def delete_student(student_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_active_teacher)):
    try:
        # Check if student exists
        stu = db.execute(text("SELECT id FROM students WHERE id = :id"), {"id": student_id}).fetchone()
        if not stu:
            return {"status": "error", "message": "Student not found."}
            
        # Delete related records
        db.execute(text("DELETE FROM student_results WHERE student_id = :id"), {"id": student_id})
        db.execute(text("DELETE FROM student_answers WHERE student_id = :id"), {"id": student_id})
        db.execute(text("DELETE FROM students WHERE id = :id"), {"id": student_id})
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        return {"status": "error", "message": "Failed to delete student. Check database constraints."}


