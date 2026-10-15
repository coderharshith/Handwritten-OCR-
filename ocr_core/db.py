import mysql.connector
from mysql.connector import Error
import json

DB_CONFIG = {
    'host': 'localhost',
    'database': 'evaluation',
    'user': 'root',
    'password': '' # Update if user has a password for root
}

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def verify_teacher(username, password):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM teachers WHERE username = %s AND password_hash = %s", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def verify_student(username, password):
    conn = get_connection()
    if not conn: return False
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE username = %s AND password_hash = %s", (username, password))
    user = cursor.fetchone()
    conn.close()
    return user is not None

def get_all_students():
    conn = get_connection()
    if not conn: return {}
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT username, password_hash FROM students")
    students = {row['username']: row['password_hash'] for row in cursor.fetchall()}
    conn.close()
    return students

def add_student(username, full_name=None, usn=None, password="stu@1"):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor(dictionary=True)
    try:
        clean_usn = usn or username
        clean_name = full_name or username
        cursor.execute("SELECT id FROM students WHERE username = %s OR usn = %s", (username, clean_usn))
        existing = cursor.fetchone()
        if not existing:
            cursor.execute("""
                INSERT INTO students (username, usn, full_name, password_hash, is_active)
                VALUES (%s, %s, %s, %s, 1)
            """, (username, clean_usn, clean_name, password))
            conn.commit()
    except Error as e:
        print(f"Error adding student: {e}")
    finally:
        conn.close()

def remove_student(username):
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE username = %s", (username,))
    conn.commit()
    conn.close()

def get_student_id(username):
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id FROM students 
        WHERE username = %s OR usn = %s OR full_name = %s
        ORDER BY id ASC LIMIT 1
    """, (username, username, username))
    user = cursor.fetchone()
    conn.close()
    return user['id'] if user else None

def save_student_answers(username, qa_dict, full_name=None, usn=None):
    add_student(username, full_name=full_name, usn=usn) # Ensure student exists
    student_id = get_student_id(username)
    if not student_id: return
    
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    
    # Clear prior answers for this student so old/dummy questions never persist
    cursor.execute("DELETE FROM student_answers WHERE student_id = %s", (student_id,))
    
    for q_num, ans_text in qa_dict.items():
        if q_num.lower() == "overall":
            continue
        cursor.execute("""
            INSERT INTO student_answers (student_id, question_number, answer_text)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE answer_text = VALUES(answer_text)
        """, (student_id, q_num, ans_text))
        
    conn.commit()
    conn.close()

def save_student_evaluation(username, eval_result, full_name=None, usn=None):
    add_student(username, full_name=full_name, usn=usn)
    student_id = get_student_id(username)
    if not student_id: return
    
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()
    
    # Clear prior evaluation records for this student so old/dummy questions never persist
    cursor.execute("DELETE FROM student_results WHERE student_id = %s", (student_id,))
    
    for item in eval_result['evaluation']:
        cursor.execute("""
            INSERT INTO student_results 
            (student_id, question_number, marks_awarded, max_marks, matched_keywords, summary, question_text, student_answer)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
            marks_awarded = VALUES(marks_awarded),
            max_marks = VALUES(max_marks),
            matched_keywords = VALUES(matched_keywords),
            summary = VALUES(summary),
            question_text = VALUES(question_text),
            student_answer = VALUES(student_answer)
        """, (
            student_id, 
            item['question_number'], 
            item['marks'], 
            item['max_marks'],
            json.dumps(item.get('matched_keywords', [])),
            item.get('summary', ''),
            item.get('question_text', f"Question {item['question_number']}"),
            item.get('student_answer', '')
        ))
        
    conn.commit()
    conn.close()

def get_teacher_dashboard_results():
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor(dictionary=True)
    
    # Query to get per-question marks and also calculate total marks for the student
    cursor.execute("""
        SELECT 
            s.username AS student,
            r.question_number,
            r.marks_awarded AS score,
            r.max_marks AS max_score,
            (SELECT ROUND(SUM(marks_awarded), 1) FROM student_results WHERE student_id = s.id) AS total_marks,
            (SELECT ROUND(SUM(max_marks), 1) FROM student_results WHERE student_id = s.id) AS total_max
        FROM student_results r
        JOIN students s ON r.student_id = s.id
        ORDER BY s.username, r.question_number
    """)
    
    results = []
    for row in cursor.fetchall():
        total = f"{row['total_marks']} / {row['total_max']}"
        results.append([row['student'], row['question_number'], f"{row['score']} / {row['max_score']}", total])
        
    conn.close()
    return results

def get_student_dashboard_results(username):
    student_id = get_student_id(username)
    if not student_id: return "### Account not found.", []
    
    conn = get_connection()
    if not conn: return "### Database Error.", []
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT question_number, marks_awarded, max_marks
        FROM student_results 
        WHERE student_id = %s
        ORDER BY question_number
    """, (student_id,))
    
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return "### Evaluation pending. Your teacher has not graded your booklet yet.", []
        
    total_marks = round(sum(r['marks_awarded'] for r in rows), 1)
    total_max = round(sum(r['max_marks'] for r in rows), 1)
    score_text = f"### Total Score: {total_marks} / {total_max}"
    
    table_data = [[r['question_number'], f"{r['marks_awarded']} / {r['max_marks']}"] for r in rows]
    
    return score_text, table_data
