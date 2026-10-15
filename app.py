import sys
import os
import json
import tempfile
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import gradio as gr
from PIL import Image
from ocr_core.config import (
    OFFLINE_MODE, MODEL_NAME, ensure_directories, apply_offline_env
)
from ocr_core.recognizer import recognize_pil_image
from ocr_core.utils import setup_logging, display_system_info

def process_image(image, preprocess_mode, mode):
    if image is None:
        return "Please upload an image.", "", "", "No image provided.", None, None, None

    try:
        single_line = (mode == "Single Line")
        result = recognize_pil_image(image, preprocess=preprocess_mode, single_line=single_line)
        
        fd_txt, txt_path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(fd_txt, 'w', encoding='utf-8') as f:
            f.write(result.text)
            
        fd_json, json_path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd_json, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
            
        warnings_str = "\n".join(result.warnings) if result.warnings else "None"
        time_str = f"{result.total_processing_time_seconds:.2f} seconds"
        
        if result.lines:
            avg_quality = sum(l.quality_score for l in result.lines) / len(result.lines)
            quality_str = f"{avg_quality:.2f} — {'Good' if avg_quality > 0.6 else 'Needs Review'}"
        else:
            quality_str = "N/A"
        num_lines = str(len(result.lines)) if result.lines else "1"
        
        return result.text, time_str, quality_str, warnings_str, num_lines, txt_path, json_path
        
    except Exception as e:
        return f"Error: {str(e)}", "", "", "Error occurred", "", None, None

def main():
    setup_logging()
    ensure_directories()
    display_system_info()
    
    with gr.Blocks(title="Handwritten OCR") as demo:
        gr.Markdown(f"# 📝 Handwritten OCR — {MODEL_NAME}")
        offline_badge = "✅" if OFFLINE_MODE else "❌"
        gr.Markdown(f"**OFFLINE MODE:** {offline_badge} | **TrOCR Large Handwritten**")
        
        with gr.Row():
            with gr.Column():
                image_input = gr.Image(type="pil", label="Upload Handwriting Image")
                preprocess_dropdown = gr.Dropdown(
                    choices=["none", "light", "medium", "strong"],
                    value="light",
                    label="Preprocessing Mode"
                )
                mode_radio = gr.Radio(
                    choices=["Full Page", "Single Line"],
                    value="Full Page",
                    label="Recognition Mode"
                )
                run_btn = gr.Button("Run OCR", variant="primary")
                
            with gr.Column():
                text_output = gr.Textbox(label="Recognized Text", lines=10)
                time_output = gr.Textbox(label="Processing Time")
                quality_output = gr.Textbox(label="Estimated Recognition Quality")
                warnings_output = gr.Textbox(label="Warnings")
                lines_output = gr.Textbox(label="Number of lines detected")
                
                with gr.Row():
                    download_txt = gr.File(label="Download .txt")
                    download_json = gr.File(label="Download .json")
                    
        run_btn.click(
            fn=process_image,
            inputs=[image_input, preprocess_dropdown, mode_radio],
            outputs=[
                text_output, time_output, quality_output, warnings_output, 
                lines_output, download_txt, download_json
            ]
        )
        
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)

if __name__ == '__main__':
    main()
