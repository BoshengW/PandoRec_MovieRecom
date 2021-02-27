from flask import Blueprint
from flask import request
from flask import Response
from . import BP_coldstart

from bson.json_util import dumps
import json
from flask import current_app

with open("D:/CapstonePJ/PandoRec/venv/Flask/asset/caches/popular_movielist.json", "r") as f:
    popularMovieList = json.load(f)
f.close()


@BP_coldstart.route("/getMovieList", methods=['GET'])
def getMovieList():
    try:
        popularMovieList_Json = dumps(popularMovieList)
        current_app.logger.info('Popular movie list have packaged, ready to return')
    except Exception as e:
        current_app.logger.error('Did not get MovieList, return 203 Status code')
        return Response(status=203, mimetype="application/json")

    return popularMovieList_Json
