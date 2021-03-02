import pandas as pd
import numpy as np
from pymongo import MongoClient
import os
import re
from EDAPipeline.util_func.util import extract_year, simplify_title, one_hot

from pyspark.sql import SparkSession
from pyspark.sql import functions as f
from pyspark.sql import types as t
from pyspark.sql.types import *

from dotenv import load_dotenv
from logging.config import fileConfig
import logging

from EDAPipeline.data_pipeline import load_analysisdata, load_embedfeature, load_metadata

"""
This is data pipeline to create basic collections on MongoDB database,
Information Schema

- Movie Meta-data with Genres: MovieMeta
- User Ratings: UserRating
- Movie Tags from User Edited: MovieTag
- User Information: UserInfo

Statictis Analysis Schema

- Recent Movie Rating Count: RecentMovieRateCnt
- Movie Average Rating: MovieAvgRate
- Total Movie Rating Count: MovieRateCnt
- Top10 Movie in each genres: Top10MoviewGenres

Recommendation Schema:

- offline： each movie similarity matrix: MovieSimOffline
- offline： each user recommend movie matrix: RecMovie2UserOffline
- online:   each user recommend movie matrix: RecMovie2UserOnline

Note: for recommendation schema, make sure you already training the embedding model in your local
since we need computation based on Movie&User Embedding model

"""
jsonpath = '../data/json/'
modelpath = "../models/neural_cf"
csvpath = "../data/ml-25m/"
envpath = "./config/.env"

fileConfig('./config/logging.conf')

def load_MovieLensDF(csvpath, jsonpath):
    """

    :param csvpath: csv path
    :param jsonpath: json path
    :return:
    """

    try:
        movies_df = pd.read_csv(csvpath + "movies.csv")
        ratings_df = pd.read_csv(csvpath + "ratings.csv")
        tags_df = pd.read_csv(csvpath + "tags.csv")

        ## web-scrapping
        movies_df_link = pd.read_json(jsonpath + "movieMeta.json")
        user_df = pd.read_json(jsonpath + "userLogin.json")
        logging.info("dataframe loaded")

    except Exception as e:
        logging.error("Error in dataframe loading" + e)


    return movies_df, ratings_df, movies_df_link, user_df



def MongoDB_init():
    """
    Initialize MongoDB database, load configuration from ./config/.env file
    :return:
    """
    load_dotenv(envpath)
    MONGO_URI = os.environ.get('MONGODB_URI')
    client = MongoClient(MONGO_URI)
    db = client['PandoRecDB']

    return db


if __name__ == "__main__":
    """
    Since total dataset size is very large, total pipeline should take 
    ~60 hours
    """
    db = MongoDB_init()

    ## create all collection
    movie_meta = db['MovieMeta']
    user_rating = db['UserRating']
    user_info = db['UserInfo']

    # recent_movie_rating_count = db['RecentMovieRateCnt']
    movie_avg_rating = db['MovieAvgRate']
    total_movie_rating_count = db['MovieRateCnt']
    # top10_movie_in_each_genres = db['Top10MovieEachGenres']
    #
    movie_sim_matrix_offline = db['MovieSimOffline']
    user_sim_matrix_offline = db['UserSimOffline']
    recommend_movie_matrix_toUser_offline = db['RecMovie2UserOffline']
    recommend_movie_matrix_toUser_online = db['RecMovie2UserOnline']

    # user_favorite_top10 = db['UserLikeTop10']
    analysis_movie_meta = db["MovieAnalysis"]
    #
    Sim_User_RecomMovie = db["SimUserRecomOffline"]
    Sim_Movie_RecomMovie = db["SimMovieRecomOffline"]

    [movies_df, ratings_df, movies_df_link, user_df] = load_MovieLensDF(csvpath, jsonpath)

    ### Basic info Schema ingestion
    load_metadata.load_movieMeta(movie_meta, movies_df_link)
    load_metadata.load_ratings(user_rating, ratings_df)
    load_metadata.load_userinfo(user_info, user_df)

    logging.info("=====================================Basic Info Schema Ingestion Completed==========================")

    ### Analysis Data Schema ingestion
    spark, ratings_spark_df = load_analysisdata.spark_init(csvpath)
    MovieIDMapping, UserIDMapping = load_embedfeature.load_IdMapping(jsonpath)
    model = load_embedfeature.load_model_weights(modelpath)

    load_analysisdata.load_totalRateCnt(total_movie_rating_count, ratings_df)
    load_analysisdata.load_movieMetaWithAnalysis(analysis_movie_meta, ratings_spark_df, movies_df, movies_df_link)

    user_sim_dict = load_embedfeature.load_usersim(user_sim_matrix_offline, model, UserIDMapping)
    movie_sim_dict = load_embedfeature.load_moviesim(movie_sim_matrix_offline, model, MovieIDMapping)


    load_analysisdata.load_recomResultbySimMovie(Sim_User_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping, user_sim_dict)
    load_analysisdata.load_recomResultbySimUser(Sim_Movie_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping, movie_sim_dict)
    logging.info("=====================================Analysis Data Schema Ingestion Completed=======================")

    ### Recommendation result prediction offline ingestion
    load_analysisdata.load_recomResultbySimUser(Sim_User_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping,user_sim_dict)
    load_analysisdata.load_recomResultbySimMovie(Sim_Movie_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping, movie_sim_dict)

    logging.info("=====================================Recommendation Result Ingestion Completed======================")
    spark.stop()



