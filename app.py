from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import json
import time


app = Flask(__name__, static_url_path='')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'xlsx', 'csv'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve index/landing page
@app.route('/')
def serve_root():
    return send_from_directory('.', 'landing.html')

# Serve HTML pages
@app.route('/<path:filename>.html')
def serve_html(filename):
    return send_from_directory('.', f'{filename}.html')

# Serve assets (js, css files)
@app.route('/assets/<path:filepath>')
def serve_assets(filepath):
    return send_from_directory('assets', filepath)

# Catch-all route for client-side routing
@app.route('/<path:path>')
def catch_all(path):
    # First try to serve as a file
    if os.path.exists(path):
        return send_from_directory('.', path)
    # If not found, return landing page for client-side routing
    return send_from_directory('.', 'landing.html')

@app.route('/api/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No files in request'}), 400
    
    files = request.files.getlist('files[]')
    case_number = request.form.get('caseNumber', 'unknown_case')
    
    # Use only case number for folder name
    upload_dir = os.path.join(UPLOAD_FOLDER, f'case_{case_number}')
    os.makedirs(upload_dir, exist_ok=True)
    
    saved_files = []
    
    for file in files:
        if file and file.filename:
            # Calculate file size and delay
            file_content = file.read()
            file_size_mb = len(file_content) / (1024 * 1024)  # Convert to MB
            
            # Delay formula: 200ms base + 100ms per MB, max 2 seconds
            delay = min(2.0, 0.2 + (file_size_mb * 0.1))
            time.sleep(delay)
            
            # Reset file pointer to start
            file.seek(0)
            
            filename = secure_filename(file.filename)
            
            # Handle nested folder structure
            relative_path = request.form.get(f'paths[{file.name}]', '').strip('/')
            if relative_path:
                file_dir = os.path.join(upload_dir, os.path.dirname(relative_path))
                os.makedirs(file_dir, exist_ok=True)
                file_path = os.path.join(file_dir, filename)
            else:
                file_path = os.path.join(upload_dir, filename)
            
            try:
                # Check if file already exists
                if os.path.exists(file_path):
                    # Add timestamp to filename if it exists
                    base, ext = os.path.splitext(filename)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"{base}_{timestamp}{ext}"
                    file_path = os.path.join(os.path.dirname(file_path), filename)
                
                with open(file_path, 'wb') as f:
                    f.write(file_content)
                
                saved_files.append({
                    'name': filename,
                    'path': os.path.relpath(file_path, UPLOAD_FOLDER),
                    'size': os.path.getsize(file_path)
                })
            except Exception as e:
                return jsonify({'error': f'Error saving file {filename}: {str(e)}'}), 500
    
    # Update or create manifest
    manifest_path = os.path.join(upload_dir, 'manifest.json')
    
    # Create new manifest data
    current_manifest_data = {
        'case_number': case_number,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'files': saved_files
    }
    
    # If manifest exists, update it
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, 'r') as f:
                existing_manifest = json.load(f)
                # Update files list while keeping existing files
                current_manifest_data['files'] = existing_manifest.get('files', []) + saved_files
        except json.JSONDecodeError:
            pass  # Use current_manifest_data if manifest is corrupted
    
    # Write the manifest
    with open(manifest_path, 'w') as f:
        json.dump(current_manifest_data, f, indent=2)
    
    return jsonify({
        'message': 'Files uploaded successfully',
        'upload_dir': upload_dir,
        'files': saved_files
    })

@app.route('/api/cases', methods=['GET'])
def get_cases():
    cases = []
    
    for case_dir in os.listdir(UPLOAD_FOLDER):
        case_path = os.path.join(UPLOAD_FOLDER, case_dir)
        if os.path.isdir(case_path):
            manifest_path = os.path.join(case_path, 'manifest.json')
            if os.path.exists(manifest_path):
                with open(manifest_path, 'r') as f:
                    cases.append(json.load(f))
    
    return jsonify(cases)

@app.route('/api/cases/<case_id>/files', methods=['GET'])
def get_case_files(case_id):
    case_dir = os.path.join(UPLOAD_FOLDER, case_id)
    if not os.path.exists(case_dir):
        return jsonify({'error': 'Case not found'}), 404
        
    manifest_path = os.path.join(case_dir, 'manifest.json')
    if not os.path.exists(manifest_path):
        return jsonify({'error': 'Case manifest not found'}), 404
        
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        
    return jsonify(manifest)

# Download route for accessing uploaded files
@app.route('/api/download/<path:filepath>')
def download_file(filepath):
    try:
        return send_from_directory(UPLOAD_FOLDER, filepath)
    except Exception as e:
        return jsonify({'error': f'Error accessing file: {str(e)}'}), 404

if __name__ == '__main__':
    app.run(debug=True, port=5000)