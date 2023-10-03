import requests
from flask import Flask, request, render_template, send_file
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from PyPDF2 import PdfMerger

app = Flask(__name__)

# Function to generate a PDF page with questions
def generate_pdf_page(questions, page_number):
    doc = SimpleDocTemplate(f"mcqs_page_{page_number}.pdf", pagesize=letter)
    story = []

    # Define styles for questions, choices, and answer key
    question_style = getSampleStyleSheet()["Normal"]
    question_style.fontSize = 14
    question_style.fontName = "Helvetica-Bold"
    question_style.textColor = colors.blue

    choice_style = getSampleStyleSheet()["Normal"]
    choice_style.fontSize = 12
    choice_style.fontName = "Helvetica"
    choice_style.textColor = colors.black

    answer_style = getSampleStyleSheet()["Normal"]
    answer_style.fontSize = 12
    answer_style.fontName = "Helvetica-Bold"
    answer_style.textColor = colors.red

    per_page = 5  # Adjust this value based on the number of questions per page
    start_index = (page_number - 1) * per_page
    end_index = min(page_number * per_page, len(questions))

    for i in range(start_index, end_index):
        question_number = i + 1  # Adjusted question numbering

        # Extract question, choices, and answer from the response text
        question, choices, answer = extract_question_data(questions[i])

        # Add the question
        question_text = f"<u>Q{question_number}:</u> {question}"
        story.append(Paragraph(question_text, question_style))

        # Add choices
        for j, choice in enumerate(choices):
            story.append(Paragraph(f"{chr(65 + j)}. {choice}", choice_style))

        # Add the answer key
        answer_text = f"<strong>Answer:</strong> {answer}"
        story.append(Paragraph(answer_text, answer_style))

        # Add spacing between questions
        story.append(Spacer(1, 12))

    doc.build(story)

# Function to extract question data from the response text
def extract_question_data(response_text):
    # Split the response text to extract question, choices, and answer
    data = response_text.split('\n')
    question = data[0].strip()
    choices = [c.strip() for c in data[1:6]]  # Assuming there are 5 choices
    answer = data[-1].strip()
    return question, choices, answer

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        subspecialty = request.form.get('subspecialty')
        num_questions = int(request.form.get('num_questions'))

        if num_questions < 1 or num_questions > 20:
            return "Invalid number of questions. Please choose a number between 1 and 20."

        # Replace this URL with the actual URL of your API
        api_url = f"https://quizgpt.com/api/quiz?topic={subspecialty}&num_questions={num_questions}&num_choices=5&difficulty=PhD"
        response = requests.get(api_url)

        if response.status_code != 200:
            return "Error fetching quiz data. Please try again later."

        # Split the response text into individual questions
        questions = response.text.split('\n\n')  # Assuming each question is separated by two newlines

        # Calculate the number of pages required
        per_page = 5  # Adjust this value based on the number of questions per page
        num_pages = (len(questions) + per_page - 1) // per_page

        # Generate PDF pages
        for page_number in range(1, num_pages + 1):
            generate_pdf_page(questions, page_number)

        # Combine all generated PDF pages into a single PDF
        merged_pdf_filename = "mcqs_merged.pdf"
        merged_pdf = PdfMerger()
        for page_number in range(1, num_pages + 1):
            merged_pdf.append(f"mcqs_page_{page_number}.pdf")
        merged_pdf.write(merged_pdf_filename)
        merged_pdf.close()

        # Send the merged PDF file as a response for download
        return send_file(merged_pdf_filename, as_attachment=True)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
