from functools import wraps
from flask import request, jsonify, current_app
from google.oauth2 import id_token
from google.auth.transport import requests
import os

class AuthManager:
    """
    Manages authentication for the application using Google Cloud Identity Platform.
    Provides methods for token verification and protection of routes.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """
        Initialize the authentication manager with a Flask application.
        Sets up configuration and registers error handlers.
        """
        self.app = app
        # Store client ID from environment variables
        self.client_id = os.getenv('CLIENT_ID')
        
        if not self.client_id:
            app.logger.warning('CLIENT_ID not set in environment variables')

    def get_auth_token(self):
        """
        Extract the authentication token from the request header.
        Expects the token in the Authorization header as 'Bearer <token>'.
        """
        auth_header = request.headers.get('Authorization')
        if not auth_header or 'Bearer ' not in auth_header:
            return None
        return auth_header.split('Bearer ')[1]

    def verify_token(self, token):
        """
        Verify the provided authentication token with Google's OAuth2 service.
        Returns the decoded token information if valid.
        """
        try:
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.client_id
            )
            return idinfo
        except ValueError as e:
            current_app.logger.error(f"Token verification failed: {str(e)}")
            return None

    def require_auth(self, f):
        """
        Decorator for protecting routes that require authentication.
        Verifies the presence and validity of an authentication token.
        """
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = self.get_auth_token()
            
            if not token:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'No token provided',
                    'status_code': 401
                }), 401
                
            user_info = self.verify_token(token)
            if not user_info:
                return jsonify({
                    'error': 'Authentication failed',
                    'message': 'Invalid or expired token',
                    'status_code': 401
                }), 401
                
            # Add user information to request context
            request.user = user_info
            return f(*args, **kwargs)
            
        return decorated_function