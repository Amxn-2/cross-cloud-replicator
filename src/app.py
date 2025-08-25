from dotenv import load_dotenv
load_dotenv()
import time
import logging
import time
from flask import Flask, request, jsonify
from marshmallow import Schema, fields, ValidationError as MarshmallowValidationError

from .config import Config
from .replicator import CrossCloudReplicator
from .exceptions import ValidationError, ConfigurationError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReplicationRequestSchema(Schema):
    """Schema for validating replication requests."""
    s3_bucket = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)
    s3_key = fields.Str(required=True, validate=lambda x: len(x.strip()) > 0)

def create_app(config: Config = None) -> Flask:
    """Application factory."""
    app = Flask(__name__)
    
    # Load configuration
    if config is None:
        config = Config.from_env()
    
    try:
        config.validate()
    except ValueError as e:
        raise ConfigurationError(f"Invalid configuration: {e}")
    
    # Initialize replicator
    replicator = CrossCloudReplicator(config)
    request_schema = ReplicationRequestSchema()
    
    @app.before_request
    def log_request():
        """Log incoming requests."""
        logger.info(f"Incoming request: {request.method} {request.path}")
    
    @app.after_request
    def log_response(response):
        """Log outgoing responses."""
        logger.info(f"Response: {response.status_code}")
        return response
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "endpoint_not_found",
            "message": "The requested endpoint does not exist",
            "timestamp": int(time.time())
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "timestamp": int(time.time())
        }), 500
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "timestamp": int(time.time()),
            "version": "1.0.0"
        })
    
    @app.route('/v1/replicate', methods=['POST'])
    def replicate_endpoint():
        """Main replication endpoint."""
        try:
            # Validate request
            if not request.is_json:
                return jsonify({
                    "error": "invalid_content_type",
                    "message": "Content-Type must be application/json",
                    "timestamp": int(time.time())
                }), 400
            
            # Parse and validate JSON payload
            try:
                data = request_schema.load(request.json)
            except MarshmallowValidationError as e:
                return jsonify({
                    "error": "validation_error",
                    "message": "Invalid request payload",
                    "details": e.messages,
                    "timestamp": int(time.time())
                }), 400
            
            # Perform replication
            result = replicator.replicate(
                s3_bucket=data['s3_bucket'].strip(),
                s3_key=data['s3_key'].strip()
            )
            
            # Add timestamp to response
            result['timestamp'] = int(time.time())
            
            # Return appropriate status code
            status_code = 200 if result['status'] in ['success', 'skipped'] else 500
            
            return jsonify(result), status_code
            
        except Exception as e:
            logger.error(f"Unexpected error in replication endpoint: {e}")
            return jsonify({
                "error": "internal_server_error",
                "message": "An unexpected error occurred during replication",
                "timestamp": int(time.time())
            }), 500
    
    return app

if __name__ == '__main__':
    config = Config.from_env()
    app = create_app(config)
    app.run(host=config.host, port=config.port, debug=config.debug)
