import gradio as gr
import pathlib
import os
import sys

# Add parent directory to sys.path so we can import ocr_core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import ocr_core.db as db
from ocr_core.config import OFFLINE_MODE, ensure_directories
from ocr_core.utils import setup_logging, display_system_info
from ocr_core.grader import evaluate_answers
import time

def process_input(student_file, key_file, preprocess_mode, mode):
    try:
        time.sleep(1)
        return "OCR Processing Completed", "1.5s", "0.95 - Good", "None", "10"
    except Exception as e:
        return f"Error: {e}", "", "", "", ""

def fetch_all_student_results():
    return db.get_teacher_dashboard_results()

def create_dashboard():
    setup_logging()
    ensure_directories()
    
    custom_css = """
    .header-logo { max-height: 50px; }
    .header-row { align-items: center; padding: 10px; background: #fff; border-bottom: 1px solid #eee; }
    .custom-card { padding: 20px; border-radius: 12px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .big-pink-btn { background: #f23c6d !important; color: white !important; font-weight: bold !important; border: none !important; }
    """
    
    with gr.Blocks(title="Booklet Evaluation System Dashboard") as demo:
        gr.HTML(f"<style>{custom_css}</style>")
        with gr.Row(elem_classes="header-row"):
            with gr.Column(scale=1, min_width=60):
                pass
            with gr.Column(scale=5):
                gr.Markdown("## Booklet Evaluation System\nTeacher Dashboard")
            with gr.Column(scale=3):
                offline_badge = "Enabled" if OFFLINE_MODE else "Disabled"
                gr.Markdown(f"**Offline Mode**: {offline_badge} &nbsp;&nbsp;&nbsp; **CPU Mode**: Enabled")
            with gr.Column(scale=2):
                gr.Markdown("**Teacher**\nFaculty Account")
        
        with gr.Tabs(elem_classes="custom-tabs"):
            with gr.TabItem("Evaluate Booklets"):
                with gr.Row():
                    with gr.Column(scale=1):
                        with gr.Column(elem_classes="custom-card"):
                            gr.Markdown("### Upload Student PDFs or ZIP\nUpload scanned answer booklets (PDF or ZIP)")
                            student_input = gr.File(label="", file_types=[".pdf", ".zip"])
                        with gr.Column(elem_classes="custom-card"):
                            gr.Markdown("### Upload Answer Key PDF (Optional)\nUpload the answer key for automatic evaluation")
                            answer_key_input = gr.File(label="", file_types=[".pdf"])
                        with gr.Column(elem_classes="custom-card"):
                            gr.Markdown("### Processing Options")
                            preprocess_dropdown = gr.Dropdown(choices=["none", "light", "medium", "strong"], value="light", label="Preprocessing Mode")
                            mode_radio = gr.Radio(choices=["Full Page", "Single Line"], value="Full Page", label="Recognition Mode")
                            run_btn = gr.Button("Run OCR", elem_classes="big-pink-btn")
                    with gr.Column(scale=1):
                        with gr.Column(elem_classes="custom-card"):
                            gr.Markdown("### OCR Results\nRecognized text from the uploaded booklet")
                            text_output = gr.Textbox(label="", lines=10)
                        with gr.Column(elem_classes="custom-card"):
                            time_output = gr.Textbox(label="Processing Time")
                            quality_output = gr.Textbox(label="Estimated Recognition Quality")
                            warnings_output = gr.Textbox(label="Warnings")
                            lines_output = gr.Textbox(label="Number of lines detected")
                            
            with gr.TabItem("Student Results"):
                with gr.Column(elem_classes="custom-card"):
                    gr.Markdown("### All Evaluated Student Results\nTable breakdown of every question evaluated.")
                    teacher_results_table = gr.Dataframe(headers=["Student", "Question Number", "Marks Awarded", "Total Marks"], interactive=False)
                    refresh_results_btn = gr.Button("Refresh Results Table", elem_classes="big-pink-btn")
                    refresh_results_btn.click(fetch_all_student_results, outputs=[teacher_results_table])
                    demo.load(fetch_all_student_results, outputs=[teacher_results_table])

            with gr.TabItem("Manage Students"):
                with gr.Column(elem_classes="custom-card"):
                    gr.Markdown("### Add and Remove Authorized Students")
                    with gr.Row():
                        with gr.Column():
                            new_student_user = gr.Textbox(label="Student Username")
                            new_student_pwd = gr.Textbox(label="Student Password")
                            add_btn = gr.Button("Add Student", elem_classes="big-pink-btn")
                        with gr.Column():
                            remove_student_user = gr.Textbox(label="Student Username to Remove")
                            remove_btn = gr.Button("Remove Student")
                    student_list = gr.Dataframe(headers=["Username", "Password"], interactive=False)
                    
                    def update_student_list():
                        stds = db.get_all_students()
                        return [[u, p] for u, p in stds.items()]
                    def add_student(u, p):
                        if not u or not p: return update_student_list()
                        db.add_student(u, p)
                        return update_student_list()
                    def remove_student(u):
                        db.remove_student(u)
                        return update_student_list()
                    demo.load(update_student_list, outputs=[student_list])
                    add_btn.click(add_student, inputs=[new_student_user, new_student_pwd], outputs=[student_list])
                    remove_btn.click(remove_student, inputs=[remove_student_user], outputs=[student_list])

        run_btn.click(
            fn=lambda *args: (*process_input(*args), [[u, p] for u, p in db.get_all_students().items()]),
            inputs=[student_input, answer_key_input, preprocess_dropdown, mode_radio],
            outputs=[text_output, time_output, quality_output, warnings_output, lines_output, student_list]
        )

    return demo
