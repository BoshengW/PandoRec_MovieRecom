from flask import Blueprint
from flask import request
from flask import Response

from . import BP_login
from ..extensions import mongo
from flask import current_app

import json
from bson.json_util import dumps


def checkNewUserOrNot(user):
    try:
        _user_features = mongo.db.UserSimOffline.find_one({'userId': user['userId']})
        if not _user_features:
            #this is new user since there is no user-feature matrix
            current_app.logger.info("userId: %d is new user" %user['userId'])
            return True
        else:
            current_app.logger.info("userId: %d is already in DB" %user['userId'])
            return False
    except Exception as e:
        current_app.logger.error(e)
        return Response(status=203, mimetype="application/json")


@BP_login.route("/register", methods=['POST'])
def registerUser():
    try:
        _registerUser = request.get_json(force=True)


        _username = _registerUser['username']
        _password = _registerUser['password']
        _email = _registerUser['email']
        _newId = mongo.db.UserInfo.count()+1

        # First check if user already registered
        _user = mongo.db.UserInfo.find_one({'username': _username})
        ## current_app.logger.debug(_user)

        if not _user:
            current_app.logger.info("Register User info not exist in Database, ready to insert")
            _registerUser2DB = {
                "username": _username,
                "password": _password,
                "email": _email,
                "userId": _newId
            }

            # check if insertion succeed
            _id = mongo.db.UserInfo.insert_one(_registerUser2DB)

            if not _id:
                current_app.logger.info("New user registration failed, return fail status code 203")
                return Response(status=203, mimetype="application/json")
            else:
                current_app.logger.info("New user registration succeed, return status code 200")
                return Response(status=200, mimetype="application/json")
        else:
            current_app.logger.info("Register User already exist in database!")
            return Response(status=203, mimetype="application/json")
    except Exception as e:
        current_app.error(e)

        return Response(status=203, mimetype="application/json")




@BP_login.route("/loginInfo", methods=['GET', 'POST'])
def validateUserInfo():

    response = {}
    try:
        _loginUser = request.get_json(force=True)
        ## current_app.logger.debug(_loginUser)

        # add username and password back to frontend- not recommand
        _user = mongo.db.UserInfo.find_one({'username': _loginUser['username']})
        if not _user:
            current_app.logger.info('username not found, current user is new')
            response['userExist'] = False
            response['newUser'] = ""
            response['username'] = ""
            response['password'] = ""
            response['userId'] = ""

        else:
            current_app.logger.info('username existed in database')
            response['userExist'] = True
            response['newUser'] = checkNewUserOrNot(_user)
            response['username'] = _user['username']
            response['password'] = _user['password']
            response['userId'] = _user['userId']

        resp = dumps(response)
        current_app.logger.debug(resp)

        current_app.logger.info("User Validation Completed, ready to package data back to frontend")

    except Exception as e:

        current_app.logger.error(e)
        return Response(status=203, mimetype="application/json")

    return resp
