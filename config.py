"""
Configuration module for ProctorGuard backend
Contains all configuration settings for the Flask application
"""

import os

# Database configuration
DATABASE_PATH = os.path.join(os.path.dirname(__file__), 'database.db')

def _env_bool(name: str, default: bool = False) -> bool:
	value = os.getenv(name)
	if value is None:
		return default
	return value.strip().lower() in {'1', 'true', 'yes', 'on'}


# Flask configuration
DEBUG = _env_bool('FLASK_DEBUG', default=False)
TESTING = _env_bool('FLASK_TESTING', default=False)
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')

# CORS configuration
CORS_ALLOWED_ORIGINS = [
	'http://localhost:3000',
	'http://127.0.0.1:3000',
	'http://localhost:5173',
	'http://127.0.0.1:5173',
	'http://localhost:8080',
	'http://127.0.0.1:8080'
]
CORS_ALLOW_HEADERS = ['Content-Type', 'Authorization']
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']

# Server configuration
FLASK_PORT = int(os.getenv('FLASK_PORT', os.getenv('PORT', '5000')))
FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ProctorGuard specific settings
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

print("[CONFIG] Configuration loaded successfully")
