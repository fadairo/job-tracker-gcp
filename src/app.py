from flask import Flask, jsonify, request
from dotenv import load_dotenv
from auth.auth import AuthManager
from api.routes import api as api_blueprint
import os
import logging

def configure_logging():
    """
    Sets up application-wide logging configuration.
    Ensures we capture important information for debugging and monitoring.
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def create_app():
    """
    Application factory function that creates and configures the Flask application.
    This pattern allows us to create multiple instances of our app with different
    configurations, which is particularly useful for testing.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # Initialize logging
    configure_logging()
    
    # Create Flask application instance
    app = Flask(__name__)
    
    # Configure core application settings
    app.config.update(
        # Secret key for session management and CSRF protection
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-key-please-change'),
        
        # Maximum content length for file uploads (10 MB)
        MAX_CONTENT_LENGTH=10 * 1024 * 1024,
        
        # Additional security headers
        SEND_FILE_MAX_AGE_DEFAULT=31536000,
        PERMANENT_SESSION_LIFETIME=1800
    )
    
    # Initialize authentication manager
    auth_manager = AuthManager()
    auth_manager.init_app(app)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors with a JSON response."""
        return jsonify({
            'error': 'Resource not found',
            'message': 'The requested resource does not exist',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors with a JSON response."""
        app.logger.error(f'Server Error: {error}')
        return jsonify({
            'error': 'Internal server error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500
    
    # Register basic health check route
    @app.route('/health', methods=['GET'])
    def health_check():
        """
        Health check endpoint to verify the application is running.
        Used by load balancers and monitoring systems.
        """
        return jsonify({
            'status': 'healthy',
            'service': 'job-tracker',
            'version': '0.1.0',
            'environment': os.getenv('FLASK_ENV', 'development')
        })
    
    # Register API routes blueprint
    app.register_blueprint(api_blueprint, url_prefix='/api')
    
    # Log application startup
    app.logger.info(f'Application started in {os.getenv("FLASK_ENV", "development")} mode')
    
    return app

def get_database_url():
    """
    Constructs the database URL from environment variables.
    This ensures sensitive database credentials aren't hardcoded.
    """
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'jobtracker')
    db_user = os.getenv('DB_USER', 'postgres')
    db_pass = os.getenv('DB_PASSWORD', '')
    
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"

# Create the application instance
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment variables
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('FLASK_ENV', 'development') == 'development'
    
    # Configure logging level based on environment
    log_level = logging.DEBUG if debug else logging.INFO
    app.logger.setLevel(log_level)
    
    # Start the application
    app.run(
        host='0.0.0.0',  # Makes the server externally visible
        port=port,
        debug=debug
    )
    
    app.logger.info(f'Application running on port {port}')