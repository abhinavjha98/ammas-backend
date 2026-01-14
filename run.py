from app import create_app
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create application instance
app = create_app(config_name=os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)




