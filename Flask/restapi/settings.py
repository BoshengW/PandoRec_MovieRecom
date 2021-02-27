import os

MONGO_URI = os.environ.get('MONGODB_URI')
MODEL_PATH = os.environ.get('MODEL_PATH')

FLASK_ENV=os.environ.get('FLASK_ENV')
SECRET_KEY=os.environ.get('SECRET_KEY')
FLASK_APP=os.environ.get('FLASK_APP')