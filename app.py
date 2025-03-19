from flask import Flask, render_template, request, jsonify, make_response, abort
import requests
import uuid
import os
from werkzeug.utils import secure_filename

from config import Config

config = Config()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/frontend'
# Convert MB to bytes for MAX_CONTENT_LENGTH
app.config['MAX_CONTENT_LENGTH'] = config.api.max_image_upload_size * 1024 * 1024  # Convert MB to bytes
app.config['API_URL'] = "http://localhost:8000"  # Your FastAPI backend URL

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.form
    prompt = data.get('message')
    
    # Get session cookie if it exists in the request
    session_cookie = request.cookies.get('session_id')
    
    # Process any uploaded file
    uploaded_file = None
    if 'file' in request.files:
        file = request.files['file']
        
        if file and file.filename != '':
            # Validate file type
            if not allowed_file(file.filename):
                return jsonify({
                    "status": "error",
                    "agent": "System",
                    "response": "Unsupported file type. Allowed formats: PNG, JPG, JPEG, GIF"
                }), 400
            
            # Validate file size before saving
            file.seek(0, os.SEEK_END)
            file_size = file.tell()
            file.seek(0)  # Reset file pointer
            
            if file_size > app.config['MAX_CONTENT_LENGTH']:
                return jsonify({
                    "status": "error", 
                    "agent": "System",
                    "response": f"File too large. Maximum size allowed: {config.api.max_image_upload_size}MB"
                }), 413
            
            # Save file securely
            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_file = filepath
    
    try:
        # Create cookies dict if session exists
        cookies = {}
        if session_cookie:
            cookies['session_id'] = session_cookie
        
        if uploaded_file:
            # API request with image
            with open(uploaded_file, "rb") as image_file:
                files = {"image": (os.path.basename(uploaded_file), image_file, "image/jpeg")}
                data = {"text": prompt}
                response = requests.post(
                    f"{app.config['API_URL']}/upload", 
                    files=files, 
                    data=data,
                    cookies=cookies
                )
            
            # Remove temporary file after sending
            try:
                os.remove(uploaded_file)
            except Exception as e:
                print(f"Failed to remove temporary file: {str(e)}")
        else:
            # API request for text only
            payload = {
                "query": prompt,
                "conversation_history": []  # Empty array since backend maintains history
            }
            response = requests.post(
                f"{app.config['API_URL']}/chat", 
                json=payload,
                cookies=cookies
            )
        
        if response.status_code == 200:
            result = response.json()
            
            # Create response object to modify
            response_data = {
                "status": "success",
                "agent": result["agent"],
                "response": result["response"]
            }
            
            # Add result image URL if it exists
            if "result_image" in result:
                # Prefix with the FastAPI URL
                response_data["result_image"] = f"{app.config['API_URL']}{result['result_image']}"
            
            flask_response = jsonify(response_data)
            
            # Extract session cookie from response if it exists
            if 'session_id' in response.cookies:
                # Set the cookie in our Flask response
                flask_response.set_cookie('session_id', response.cookies['session_id'])
            
            return flask_response
        else:
            return jsonify({
                "status": "error",
                "agent": "System",
                "response": f"Error: {response.status_code} - {response.text}"
            }), response.status_code
    except Exception as e:
        print(f"Exception: {str(e)}")
        return jsonify({
            "status": "error",
            "agent": "System",
            "response": f"Error: {str(e)}"
        }), 500

# Add a custom error handler for request entity too large
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        "status": "error",
        "agent": "System",
        "response": f"File too large. Maximum size allowed: {config.api.max_image_upload_size}MB"
    }), 413

if __name__ == '__main__':
    app.run(debug=True, port=5000)