# app.py
from flask import Flask, request, redirect, url_for, render_template, flash, jsonify
import os
from werkzeug.utils import secure_filename
import pdfplumber
from docx import Document
import pytesseract
from PIL import Image
import fitz  # PyMuPDF
import re
import spacy
from textblob import TextBlob
import hashlib
import redis
import json
import logging
# from your_custom_modules import process_document_task  # If using Celery

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_secret_key')  # Use environment variable in production
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB limit

# Initialize Logging
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(message)s'
)

# Allowed MIME types
ALLOWED_MIMES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'image/png',
    'image/jpeg'
}

# Initialize Redis for caching
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Load spaCy model
nlp = spacy.load("en_core_web_sm")  # Ensure the model is downloaded

def allowed_file_mime(filepath, allowed_mimes):
    import magic
    mime = magic.from_file(filepath, mime=True)
    return mime in allowed_mimes

def get_file_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def clean_text(text):
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove non-printable characters
    text = ''.join(filter(lambda x: x.isprintable(), text))
    return text.strip()

def extract_entities(text):
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

def analyze_sentiment(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment  # polarity and subjectivity
    return sentiment

def process_document(filepath):
    # Check file type
    if filepath.lower().endswith('.pdf'):
        return extract_from_pdf(filepath)
    elif filepath.lower().endswith('.docx'):
        return extract_from_docx(filepath)
    elif filepath.lower().endswith(('.png', '.jpg', '.jpeg')):
        return extract_from_image(filepath)
    else:
        return "Unsupported file type"

def extract_from_pdf(filepath):
    text = ""
    try:
        with fitz.open(filepath) as doc:
            for page_num, page in enumerate(doc, start=1):
                page_text = page.get_text("text")
                if page_text:
                    text += f"--- Page {page_num} ---\n{page_text}\n"
                else:
                    # Perform OCR if no text is found
                    pix = page.get_pixmap()
                    img_path = f"temp_page_{page_num}.png"
                    pix.save(img_path)
                    ocr_text = pytesseract.image_to_string(Image.open(img_path))
                    text += f"--- Page {page_num} (OCR) ---\n{ocr_text}\n"
                    os.remove(img_path)
    except Exception as e:
        logging.error(f"Error extracting text from PDF {filepath}: {e}")
        text = "An error occurred while extracting text from PDF."
    return clean_text(text)

def extract_from_docx(filepath):
    try:
        doc = Document(filepath)
        text = "\n".join([para.text for para in doc.paragraphs])
    except Exception as e:
        logging.error(f"Error extracting text from DOCX {filepath}: {e}")
        text = "An error occurred while extracting text from DOCX."
    return clean_text(text)

def extract_from_image(filepath):
    try:
        image = Image.open(filepath)
        text = pytesseract.image_to_string(image)
    except Exception as e:
        logging.error(f"Error extracting text from Image {filepath}: {e}")
        text = "An error occurred while extracting text from Image."
    return clean_text(text)

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'document' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['document']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        logging.info(f"File uploaded: {filename}")
        
        # Validate MIME type
        if not allowed_file_mime(filepath, ALLOWED_MIMES):
            flash('Invalid file type.')
            os.remove(filepath)
            logging.warning(f"Invalid MIME type for file: {filename}")
            return redirect(request.url)
        
        # Check cache
        file_hash = get_file_hash(filepath)
        cached_data = redis_client.get(file_hash)
        if cached_data:
            extracted_data = json.loads(cached_data)
            logging.info(f"Cache hit for file: {filename}")
        else:
            # Process the document
            extracted_text = process_document(filepath)
            extracted_data = {
                "raw_text": extracted_text,
                "entities": extract_entities(extracted_text),
                "sentiment": analyze_sentiment(extracted_text)
            }
            # Cache the data
            redis_client.set(file_hash, json.dumps(extracted_data), ex=86400)  # Cache for 1 day
            logging.info(f"Processed and cached file: {filename}")
        
        # Optionally delete the file after processing
        try:
            os.remove(filepath)
            logging.info(f"Deleted file after processing: {filename}")
        except Exception as e:
            logging.error(f"Error deleting file {filename}: {e}")
        
        return render_template('result.html', data=extracted_data)
    else:
        flash('Allowed file types are pdf, docx, png, jpg, jpeg')
        return redirect(request.url)

@app.route('/status/<task_id>')
def check_status(task_id):
    # Placeholder for async task status checking
    return jsonify({"status": "Not Implemented"})

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)
