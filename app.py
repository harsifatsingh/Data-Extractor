from flask import Flask, request, redirect, url_for, render_template, flash
import os
from werkzeug.utils import secure_filename
import pdfplumber
from docx import Document
import pytesseract
from PIL import Image

app = Flask(__name__)
app.secret_key = "2112"
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024                         # 16MB

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    if '.' in filename:
        if filename.split(".")[-1].lower() in ALLOWED_EXTENSIONS:
            return True
    return False

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if "document" not in request.files:
        flash("No file part")
        return redirect(request.url)
    
    file = request.files["document"]
    if file.filename == "":
        flash("No selected file")
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        flash("File successfully uploaded")
        # Placeholder for processing function
        extracted_data = process_document(filepath)
        os.remove(filepath)
        return render_template('result.html', data=extracted_data)
    else:
        flash("Allowed file types are pdf, docx, png, jpg, jpeg")
        return redirect(request.url)
    
def process_document(filepath):
    if filepath.lower().endswith(".pdf"):
        return extract_from_pdf(filepath)
    elif filepath.lower().endswith(".docx"):
        return extract_from_docx(filepath)
    elif filepath.lower().endswith((".png", ".jpg", ".jpeg")):
        return extract_from_image(filepath)
    else:
        return "Unsupported file type"
    
def extract_from_pdf(filepath):
    text = ""
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text += page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text
    
def extract_from_docx(filepath):
    doc = Document(filepath)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def extract_from_image(filepath):
    image = Image.open(filepath)
    text = pytesseract.image_to_string(image)
    return text


if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)