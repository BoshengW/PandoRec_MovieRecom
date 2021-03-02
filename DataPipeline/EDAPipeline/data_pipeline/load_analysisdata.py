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

from queue import PriorityQueue
from logging.config import fileConfig
import logging

fileConfig('./config/logging.conf')
genres_list = ['(no genres listed)', 'Action', 'Adventure', 'Animation', 'Children',
       'Comedy', 'Crime', 'Documentary', 'Drama', 'Fantasy', 'Film-Noir',
       'Horror', 'IMAX', 'Musical', 'Mystery', 'Romance', 'Sci-Fi', 'Thriller',
       'War', 'Western']

def getUserTop10Favorite(ratings_df):
    """
    Get user top10 favorite movies
    :param ratings_df: user rating history dataframe
    :return: a dictionary: key -> userID, value-> list of favorite movies
    """
    users_favorite_movies_df = ratings_df[ratings_df.rating > 3.5]

    user_top10 = users_favorite_movies_df.groupby('userId').rating.nlargest(10)
    top10Movies_indexs = user_top10.index.get_level_values(1)

    df_userTop10Movies = users_favorite_movies_df.loc[top10Movies_indexs]
    df_userTop10Movies.userId = df_userTop10Movies.userId.astype(int)
    df_userTop10Movies.movieId = df_userTop10Movies.movieId.astype(int)

    user_top10_favorite = {}
    for _userId in df_userTop10Movies.userId.unique():
        _favorite_movielist = df_userTop10Movies[df_userTop10Movies.userId == _userId].movieId.values.tolist()
        user_top10_favorite[int(_userId)] = _favorite_movielist

    return user_top10_favorite

"""
analysis schema 
"""

def load_totalRateCnt(total_movie_rating_count, ratings_df):
    """
    calculate each movie total rate cnt and load into MongoDB
    :param total_movie_rating_count: MongoDB collection name
    :param ratings_df: user rating history dataframe
    :return:
    """
    try:
        movies_rate_df = ratings_df.groupby('movieId')['userId'].size() \
            .reset_index(name='count') \
            .sort_values(['count'], ascending=False)

        movies_rate_dict = movies_rate_df.to_dict('record')

        total_movie_rating_count.insert_many(movies_rate_dict)
        logging.info("Total Rating Count for each movies insertion completed.")

    except Exception as e:
        logging.error("Total Rating Count for each movies insertion failed." + e)


"""
Spark analysis
"""


def spark_init(csvpath):
    """
    Init spark session
    :param csvpath: ratings.csv path
    :return:
    """
    try:
        spark = SparkSession.builder.appName("PandoRec").getOrCreate()

        ratings_spark_df = spark.read.csv(
            csvpath + "ratings.csv",
            sep=",",
            header=True,
            quote='"',
            inferSchema=True
        )

        logging.info("Spark Session init succeed.")
    except Exception as e:
        logging.error("Spark Session init failed." + e)

    return spark, ratings_spark_df


def load_movieMetaWithAnalysis(analysis_movie_meta, ratings_spark_df, movies_df, movies_df_link):
    """
    use spark session to compute movie avg and rate total count then load into MongoDB
    :param analysis_movie_meta: MongoDB collection name for movie_meta info with Avgrate & Total rate count
    :param ratings_spark_df: user rating dataframe load by spark
    :param movies_df: movies metadata dataframe
    :param movies_df_link: movies poster link info dataframe
    :return:
    """
    try:
        ratings_spark_df = ratings_spark_df.withColumn('timestamp',
                                                       f.date_format(
                                                           ratings_spark_df.timestamp.cast(dataType=t.TimestampType()),
                                                           "yyyy-MM-dd"))
        ratings_spark_df = ratings_spark_df.withColumn('timestamp',
                                                       f.to_date(
                                                           ratings_spark_df.timestamp.cast(dataType=t.TimestampType())))

        total_ratings_cnt_spark_df = ratings_spark_df.groupBy('movieId') \
            .count() \
            .orderBy('count', ascending=False)

        total_ratings_cnt_df = total_ratings_cnt_spark_df.toPandas()

        avg_ratings_spark_df = ratings_spark_df.groupBy('movieId').avg('rating')
        avg_ratings_spark_df = avg_ratings_spark_df.withColumn('avg(rating)',
                                                               f.round(avg_ratings_spark_df['avg(rating)'], 2))

        avg_ratings_df = avg_ratings_spark_df.toPandas()

        avg_ratings_df = avg_ratings_df.rename(columns={'avg(rating)': 'avg_rate'})

        movies_df['release_year'] = movies_df.title.apply(lambda row: extract_year(row))
        movies_df['title'] = movies_df.title.apply(lambda row: simplify_title(row))
        movies_df = movies_df.apply(lambda row: one_hot(row), axis=1)
        movies_df = movies_df.fillna(0)

        rated_movies_df = avg_ratings_df.merge(movies_df, left_on='movieId', right_on='movieId')
        rated_movies_withCount_df = total_ratings_cnt_df.merge(rated_movies_df, left_on="movieId", right_on="movieId")
        rated_movies_withCount_df = rated_movies_withCount_df.drop(genres_list, axis=1)
        rated_movies_w_count_link_df = rated_movies_withCount_df.merge(
                                                                        movies_df_link[["movieId", "poster_link"]],
                                                                        left_on="movieId", right_on="movieId")
        analysis_movie_meta.insert_many(rated_movies_w_count_link_df.to_dict("record"))
        logging.info("Movie Meta data with AvgRate and Total Rate Count insertion completed.")
    except Exception as e:
        logging.error("Movie Meta data with AvgRate and Total Rate Count insertion failed." + e)


def load_recomResultbySimUser(Sim_User_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping, user_sim_dict):
    """
    compute recommendation movielist for each user based on similar user
    :param Sim_User_RecomMovie: MongoDB collection name for saving Recommendation Movies list for each user based on Similar user favorite movies
    :param model: Trained Neural CF model
    :param ratings_df: user rating dataframe
    :param UserIDMapping: User ID Mapping dictionary, map UserID in user rating into Trained model inner userID
    :param MovieIDMapping: Movie ID Mapping dictionary, map MovieID in user rating into Trained model inner movieID
    :param user_sim_dict: a dictionary: key-> userId, value-> list of similar userID
    :return:
    """
    try:
        user_top10_favorite = getUserTop10Favorite(ratings_df)

        sim_user_recom_result = []
        for _userId in range(1, 100):
            _temp_movieIdList = []
            recom_movieIdList = []
            Top20_movie_queue = PriorityQueue()
            for _sim_userId in user_sim_dict[str(_userId)].keys():
                try:
                    _temp_movieIdList += user_top10_favorite[int(_sim_userId)]
                except KeyError:
                    continue
            for _movieId in _temp_movieIdList:
                userId_inner = UserIDMapping[str(_userId)]
                _movieId_inner = MovieIDMapping[str(_movieId)]
                ##priority queue find global top20
                pred_score = -round(model.predict([pd.Series([userId_inner]), pd.Series([_movieId_inner])])[0][0], 2)
                Top20_movie_queue.put((pred_score, _movieId))
            for _ in range(20):
                recom_movieIdList += [Top20_movie_queue.get()[1]]
            sim_user_recom_result.append({
                "userId": int(_userId),
                "recom_movies": recom_movieIdList
            })

        Sim_User_RecomMovie.insert_many(sim_user_recom_result)
        logging.info("Recommendation result by similar user insertion completed")

    except Exception as e:
        logging.error("Recommendation result by similar user insertion failed" + e)


def load_recomResultbySimMovie(Sim_Movie_RecomMovie, model, ratings_df, UserIDMapping, MovieIDMapping, movie_sim_dict):
    """
    compute recommendation movielist for each user based on similar movie to each user's favorite movies
    :param Sim_Movie_RecomMovie: MongoDB collection name for saving Recommendation Movies list for each user based on similar movies to each user's favorite
    :param model: Trained Neural CF model
    :param ratings_df: user rating dataframe
    :param UserIDMapping: User ID Mapping dictionary, map UserID in user rating into Trained model inner userID
    :param MovieIDMapping: Movie ID Mapping dictionary, map MovieID in user rating into Trained model inner movieID
    :param movie_sim_dict: a dictionary: key-> userId, value-> list of recommendation movielist
    :return:
    """
    try:
        user_top10_favorite = getUserTop10Favorite(ratings_df)

        movies_sim_dict_list = {}

        for key, val in movie_sim_dict.items():
            movies_sim_dict_list[int(key)] = [int(k) for k in val.keys()]

        sim_movie_recom_result = []
        for _userId in range(1, 100):
            _temp_movieIdList = []
            recom_movieIdList = []
            Top20_movie_queue = PriorityQueue()
            for _favorite_movieId in user_top10_favorite[_userId]:
                try:
                    _temp_movieIdList += movies_sim_dict_list[_favorite_movieId]

                except KeyError:
                    continue

            for _movieId in _temp_movieIdList:
                userId_inner = UserIDMapping[str(_userId)]
                _movieId_inner = MovieIDMapping[str(_movieId)]
                pred_score = -round(model.predict([pd.Series([userId_inner]), pd.Series([_movieId_inner])])[0][0], 2)
                Top20_movie_queue.put((pred_score, _movieId))

            for _ in range(20):
                recom_movieIdList += [Top20_movie_queue.get()[1]]
            sim_movie_recom_result.append({
                "userId": int(_userId),
                "recom_movies": recom_movieIdList
            })

        Sim_Movie_RecomMovie.insert_many(sim_movie_recom_result)
        logging.info("Recommendation result by Similar movie insertion completed")

    except Exception as e:
        logging.error("Recommendation result by Similar movie insertion failed:" + e)

