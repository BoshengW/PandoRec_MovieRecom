from flask import Blueprint
from flask import request
from flask import Response
from . import BP_recomsys
from keras.models import load_model

from bson.json_util import dumps
import pandas as pd
import random

from ..extensions import mongo
import json

from flask import current_app


with open("D:/CapstonePJ/PandoRec/venv/Flask/asset/caches/user_id_map.json", "r") as f:
    UserIDMapping = json.load(f)

f.close()

with open("D:/CapstonePJ/PandoRec/venv/Flask/asset/caches/movie_id_map.json", "r") as f:
    MovieIDMapping = json.load(f)

f.close()

RecomModel = load_model("D:/CapstonePJ/PandoRec/venv/DL-engine/neural_cf")




def randhomChooseMovies(movie_count):
    """
    this is function randomly choose mutiple movie for new user rating
    @:param
    movies_count
    """
    try:
        if movie_count <= 1:
            current_app.logger.info("movie_count error, please check DB")
            return []
        random_movieId_list = random.sample(range(1, 200), 8)
        current_app.logger.debug(random_movieId_list)
    except Exception as e:
        current_app.logger.error(e)
    return random_movieId_list


@BP_recomsys.route("/getOldUserRecomMovieList", methods=['POST'])
def getOldUserRecomMovieLists():
    recomMovieList = {}
    recomMovieListbyMovieSim = []
    recomMovieListbyUserSim = []


    try:
        request_json = request.get_json()
        userId = request_json["userId"]
        userId_inner = UserIDMapping[str(userId)]
        recomMovieList = {}


        ## read offline recom prediction by Usersim
        recomMovieIdListbyUserSim = mongo.db.SimUserRecomOffline.find_one({"userId": userId})["recom_movies"]
        recomMovieListbyUserSim = mongo.db.MovieAnalysis.find({"movieId": {"$in": recomMovieIdListbyUserSim}})


        ## read offline recom prediction by Moviesim
        recomMovieIdListbyMovieSim = mongo.db.SimMovieRecomOffline.find_one({"userId": userId})["recom_movies"]
        recomMovieListbyMovieSim = mongo.db.MovieAnalysis.find({"movieId": {"$in": recomMovieIdListbyMovieSim}})

        current_app.logger.info("Get this user's recommendation data from MongoDB, ready to send response")
    except:
        current_app.logger.info("Old user recommend system failed, send most popular movielist")
        movies_count = mongo.db.MovieMeta.count()
        random_movieId_list = randhomChooseMovies(movies_count)

        for _movieId in random_movieId_list:
            _movieInfoRecom = mongo.db.MovieMeta.find_one({'movieId': _movieId})
            _movieInfoRecom["AvgRate"] = mongo.db.MovieAvgRate.find_one({"movieId": _movieId})['avg_rate']
            _movieInfoRecom["RateCount"] = mongo.db.MovieRateCnt.find_one({"movieId": _movieId})['count']

            ## Predict rating value
            _movieId_inner = MovieIDMapping[str(_movieId)]
            _movieInfoRecom['PredRate'] = round(
                float(RecomModel.predict([pd.Series([userId_inner]), pd.Series([_movieId_inner])])[0][0]), 2
            )

            recomMovieListbyUserSim.append(_movieInfoRecom)
            recomMovieListbyMovieSim.append(_movieInfoRecom)

    finally:
        recomMovieList["UserSim"] = recomMovieListbyUserSim
        recomMovieList["MovieSim"] = recomMovieListbyMovieSim
        current_app.logger.info("User recommendation MovieList has packaged, ready to return!")

        return dumps(recomMovieList)


