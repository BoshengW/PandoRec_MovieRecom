# .flaskenv use for saving some
DEBUG=True
FLASK_ENV="development"
LOG_LEVEL="debug"
SECRET_KEY="not-so-secret"

## for FLASK_APP env need to use absolute module name inside package
FLASK_APP="restapi.app:create_app()"
