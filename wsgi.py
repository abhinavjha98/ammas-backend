"""
WSGI entry point for production deployment
This file is used by gunicorn to serve the Flask application
"""
import os
from app import create_app

# Create the Flask application instance
# Use 'production' config for deployed environments
app = create_app(config_name=os.getenv('FLASK_ENV', 'production'))

if __name__ == "__main__":
    app.run()
