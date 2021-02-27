
from flask import Flask
from flask_cors import CORS

from .coldstart import BP_coldstart
from .login import BP_login
from .recomsys import BP_recomsys
from .extensions import mongo

from logging.config import fileConfig

### config init for logging
fileConfig('./config/logging.conf')


### flask run will search create_app() function or you need to set environment variable of app.py
def create_app(config_object='restapi.settings'):
    try:
        app = Flask(__name__)
        CORS(app)  ## cross region 跨域处理
        app.config.from_object(config_object)
        register_blueprint(app)
        mongo.init_app(app)

        app.logger.info('Flask Application Initialize Successfully!')
    except Exception as e:
        app.logger.error(e)

    return app

def register_blueprint(app):
    try:
        app.register_blueprint(BP_coldstart)
        app.register_blueprint(BP_login)
        app.register_blueprint(BP_recomsys)

        app.logger.info("BluePrint Initialize Successfully!")
    except Exception as e:
        app.logger.error(e)


    return None

app = create_app(config_object='restapi.settings')

