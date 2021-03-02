import pandas as pd
from pymongo import MongoClient
from logging.config import fileConfig
import logging

"""
Basic schema 
"""

fileConfig('./config/logging.conf')

def load_movieMeta(movie_meta, movies_df_link):
    """
    Used for loading MovieLens-25M movie meta data with poster link into MongoDB collection
    :param movie_meta: MongoDB collection for movie meta
    :param movies_df_link: movie metadata dataframe
    :return:
    """
    try:
        movies_link_dict = movies_df_link.to_dict('record')
        movie_meta.insert_many(movies_link_dict)
        logging.info("insert moviemeta")
    except Exception as e:
        logging.error("Error in movieMeta insertion" + e)

def load_userinfo(user_info, user_df):
    """
    Load user info (password, username, email, create_date,...) into user_info collection
    :param user_info: MongoDB collection for user info
    :param user_df: user info dataframe
    :return:
    """

    try:
        user_info_dict = user_df.to_dict('record')
        user_info.insert_many(user_info_dict)
        logging.info("insert userinfo")
    except Exception as e:
        logging.error("Error in userinfo insertion" + e)

def load_ratings(user_rating, ratings_df):
    """
    Load user rating history into MongoDB collections
    Note: Since MongoDB Compress free space only 500MB, impossible to load all data(>25000000), we only load ~10000 data inside
    :param user_rating: MongoDB collection for user rating history
    :param ratings_df: user ratings history data
    :return:
    """
    try:
        ratings_dict = ratings_df[:10000].to_dict('record')
        user_rating.insert_many(ratings_dict)
        logging.info("insert user rating")
    except Exception as e:
        logging.error("Error in ratings insertion" + e)
