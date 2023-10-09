import os
import re
import requests
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from PyPDF2 import PdfReader, PdfWriter, PdfMerger

app = Flask(__name__)

def extract_data_from_api_text(api_text):
    sections = re.split(r'ANSWER KEY:\s*', api_text, flags=re.IGNORECASE)
    questions_text = sections[0].strip()
    answer_key_text = sections[1].strip() if len(sections) > 1 else ''
    questions = re.split(r'\d+\.', questions_text)
    questions = [q.strip() for q in questions if q.strip()]
    return questions, answer_key_text

def extract_question_data(question_text):
    parts = re.split(r'\s[a-e]\)', question_text)
    question = parts[0].strip()
    choices = [f"{chr(97 + idx)}) {choice.strip()}" for idx, choice in enumerate(parts[1:])]
    return question, choices

def generate_pdf_page(questions, answer_key_text, page_number):
    doc = SimpleDocTemplate(f"mcqs_page_{page_number}.pdf", pagesize=letter)
    story = []
    question_style = getSampleStyleSheet()["Normal"]
    question_style.fontSize = 14
    question_style.fontName = "Helvetica-Bold"
    question_style.textColor = colors.blue

    choice_style = getSampleStyleSheet()["Normal"]
    choice_style.fontSize = 12
    choice_style.fontName = "Helvetica"
    choice_style.textColor = colors.black

    per_page = 10
    start_index = (page_number - 1) * per_page
    end_index = min(page_number * per_page, len(questions))

    for i in range(start_index, end_index):
        question_number = i + 1
        question, choices = extract_question_data(questions[i])
        question_text = f"<u>Q{question_number}:</u> {question}"
        story.append(Paragraph(question_text, question_style))
        for j, choice in enumerate(choices):
            story.append(Paragraph(choice, choice_style))
        story.append(Spacer(1, 12))

    if page_number == ((len(questions) + per_page - 1) // per_page):
        story.append(PageBreak())
        story.append(Paragraph("<u>Answer Key:</u>", question_style))
        story.append(Paragraph(answer_key_text, choice_style))

    doc.build(story)

def generate_watermark(output="watermark.pdf"):
    c = canvas.Canvas(output)
    c.setPageSize(letter)
    c.saveState()
    c.translate(300, 400)
    c.rotate(45)
    c.setFont("Helvetica", 36)
    c.setFillColorRGB(0.8, 0.8, 0.8)
    c.drawString(-150, 0, "radiologia-inteligente.framer.ai|RadQuiz")
    c.restoreState()
    c.showPage()
    c.save()

def add_watermark(input_pdf, output_pdf, watermark):
    with open(input_pdf, "rb") as orig_file:
        pdf = PdfReader(orig_file)
        watermark_obj = PdfReader(watermark)
        watermark_page = watermark_obj.pages[0]
        pdf_writer = PdfWriter()
        for page in pdf.pages:
            page.merge_page(watermark_page)
            pdf_writer.add_page(page)
        with open(output_pdf, "wb") as output_file_handle:
            pdf_writer.write(output_file_handle)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form.get('topic')
        subtopic = request.form.get('subtopic')
        num_questions = int(request.form.get('num_questions'))
        if num_questions < 1 or num_questions > 15:
            return "Invalid number of questions. Please choose a number between 1 and 15."
        topic_and_subtopic = f"{topic.replace(' ', '%20')}%20/{subtopic.replace(' ', '%20')}"
        api_url = f"https://quizgpt.com/api/quiz?topic=Elaborate%20clinical%20scenarios%20leading%20to%20intricate%20imaging%20interpretation%20diagnoses%20or%20differential%20diagnoses%20concerning%20{topic_and_subtopic}&num_questions={num_questions}&num_choices=5&difficulty=PhD"
        response = requests.get(api_url)
        if response.status_code != 200:
            return "Error fetching quiz data. Please try again later."
        questions_text, answer_key_text = extract_data_from_api_text(response.text)
        per_page = 5
        num_pages = (len(questions_text) + per_page - 1) // per_page
        for page_number in range(1, num_pages + 1):
            generate_pdf_page(questions_text, answer_key_text, page_number)
        generate_watermark()
        merged_pdf_filename = "mcqs_merged.pdf"
        merged_pdf = PdfMerger()
        for page_number in range(1, num_pages + 1):
            add_watermark(f"mcqs_page_{page_number}.pdf", f"mcqs_page_watermarked_{page_number}.pdf", "watermark.pdf")
            merged_pdf.append(f"mcqs_page_watermarked_{page_number}.pdf")
        merged_pdf.write(merged_pdf_filename)
        merged_pdf.close()
        return send_file(merged_pdf_filename, as_attachment=True)
    return render_template('index.html')

if __name__ == '__main__':
    for file_name in os.listdir():
        if file_name.startswith("mcqs_page_") and file_name.endswith(".pdf"):
            os.remove(file_name)
    app.run(debug=True)
