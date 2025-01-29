from flask import Blueprint, request, jsonify, current_app
from ..database.operations import JobApplicationStore
from ..database.models import JobApplication
from ..storage.storage import CloudStorageManager
from ..auth.auth import AuthManager
from werkzeug.utils import secure_filename
from typing import Dict, Any
from datetime import datetime
import logging

def create_error_response(message: str, status_code: int) -> tuple[Dict[str, Any], int]:
    """
    Creates a standardized error response for our API endpoints.
    
    This helper function ensures consistent error reporting across all our API endpoints.
    It structures the error response to include all necessary information in a predictable format.
    
    Args:
        message: A human-readable description of what went wrong
        status_code: The HTTP status code that best describes the error
        
    Returns:
        A tuple containing the JSON response body and HTTP status code
    
    Example Usage:
        return create_error_response("File not found", 404)
    """
    return jsonify({
        'error': True,
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'status_code': status_code
    }), status_code

# Initialize our services
api = Blueprint('api', __name__)
store = JobApplicationStore()
auth = AuthManager()
storage_manager = CloudStorageManager()

# Constants for file upload handling
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'txt', 'rtf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB in bytes

def allowed_file(filename: str) -> bool:
    """
    Validates that the uploaded file has an allowed extension.
    Security measure to prevent upload of potentially dangerous files.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file(file) -> tuple[bool, str]:
    """
    Performs comprehensive validation on an uploaded file.
    Checks file presence, filename security, extension, and size.
    Returns a tuple of (is_valid, error_message).
    """
    if not file:
        return False, "No file provided"
        
    if not file.filename:
        return False, "Invalid filename"
        
    if not allowed_file(file.filename):
        return False, f"File type not allowed. Accepted types: {', '.join(ALLOWED_EXTENSIONS)}"
        
    if len(file.read()) > MAX_FILE_SIZE:
        file.seek(0)  # Reset file pointer after reading
        return False, f"File size exceeds maximum limit of {MAX_FILE_SIZE // 1024 // 1024}MB"
        
    file.seek(0)  # Reset file pointer after validation
    return True, ""

@api.route('/applications/upload', methods=['POST'])
@auth.require_auth
async def upload_resume():
    """
    Handles resume file uploads independently of job application creation.
    This allows for more flexible file management and error handling.
    """
    try:
        if 'file' not in request.files:
            return create_error_response("No file part in the request", 400)
            
        file = request.files['file']
        is_valid, error_message = validate_file(file)
        
        if not is_valid:
            return create_error_response(error_message, 400)
            
        # Upload file to cloud storage
        file_data = file.read()
        storage_path, signed_url = storage_manager.upload_file(
            file_data, 
            secure_filename(file.filename)
        )
        
        return jsonify({
            'message': 'File uploaded successfully',
            'storage_path': storage_path,
            'download_url': signed_url
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {str(e)}")
        return create_error_response("Error processing file upload", 500)

@api.route('/applications', methods=['POST'])
@auth.require_auth
async def create_application():
    """
    Creates a new job application with optional resume attachment.
    Handles both the application data and file upload in a single request.
    """
    try:
        # Handle file upload if present
        resume_storage_path = None
        if 'resume' in request.files:
            file = request.files['resume']
            is_valid, error_message = validate_file(file)
            
            if not is_valid:
                return create_error_response(error_message, 400)
                
            # Upload resume to cloud storage
            file_data = file.read()
            storage_path, _ = storage_manager.upload_file(
                file_data,
                secure_filename(file.filename)
            )
            resume_storage_path = storage_path
        
        # Process application data
        data = request.form.to_dict()  # Use form data instead of JSON for multipart requests
        
        # Create job application with resume path if uploaded
        application = JobApplication(
            company=data.get('company'),
            position=data.get('position'),
            status=data.get('status', 'applied'),
            notes=data.get('notes'),
            resume_url=resume_storage_path
        )
        
        # Save to database
        application_id = await store.create(application)
        
        return jsonify({
            'message': 'Application created successfully',
            'application_id': application_id,
            'has_resume': resume_storage_path is not None
        }), 201
        
    except ValueError as e:
        return create_error_response(str(e), 400)
    except Exception as e:
        current_app.logger.error(f"Error creating application: {str(e)}")
        return create_error_response("Internal server error", 500)

@api.route('/applications/<application_id>/resume', methods=['GET'])
@auth.require_auth
async def get_resume_url(application_id: str):
    """
    Generates a temporary signed URL for accessing a job application's resume.
    The URL expires after 15 minutes for security.
    """
    try:
        application = await store.get(application_id)
        
        if not application:
            return create_error_response("Application not found", 404)
            
        if not application.resume_url:
            return create_error_response("No resume attached to this application", 404)
            
        signed_url = storage_manager.get_file_url(application.resume_url)
        
        if not signed_url:
            return create_error_response("Resume file not found in storage", 404)
            
        return jsonify({
            'download_url': signed_url
        })
        
    except Exception as e:
        current_app.logger.error(f"Error generating resume URL: {str(e)}")
        return create_error_response("Error accessing resume", 500)