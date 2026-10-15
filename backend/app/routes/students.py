from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.security.auth import get_current_active_student

router = APIRouter()

@router.get("/my-results")
async def get_my_results(db: Session = Depends(get_db), current_student=Depends(get_current_active_student)):
    try:
        student_id = current_student.id
        
        # Get overall results summary
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
            "student_info": {
                "name": current_student.full_name or current_student.username,
                "usn": current_student.usn,
                "username": current_student.username
            },
            "summary": {
                "total_marks": total_marks,
                "maximum_marks": maximum_marks,
                "evaluated_on": eval_time.isoformat() if eval_time else None
            },
            "questions": questions
        }
    except Exception as e:
        import traceback; traceback.print_exc()
        return {"status": "error", "message": str(e)}
