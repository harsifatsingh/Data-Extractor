from flask import Flask, request, redirect, url_for, render_template, flash
import os
from werkzeug.utils import secure_filename

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
        # extracted_data = process_document(filepath)
        # response = send_to_chatgpt(extracted_data)
        # return render_template('result.html', data=response)
        return redirect(url_for('upload_form'))
    else:
        flash("Allowed file types are pdf, docx, png, jpg, jpeg")
        return redirect(request.url)
    

if __name__ == "__main__":
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True)