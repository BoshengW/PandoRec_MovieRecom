import time
from sklearn.metrics.pairwise import cosine_similarity

import numpy as np
import json

from keras.models import load_model
from logging.config import fileConfig
import logging

from EDAPipeline.util_func.util import save_json

fileConfig('./config/logging.conf')
def load_IdMapping(jsonpath):
    """
    Load MovieID mapping and User ID mapping
    :param jsonpath:
    :return:
    """

    with open(jsonpath+"movie_id_map.json", "r") as f:
        movie_id_mapping = json.load(f)

    with open(jsonpath+"user_id_map.json", "r") as f:
        user_id_mapping = json.load(f)

    f.close()

    return [movie_id_mapping, user_id_mapping]


def load_model_weights(modelpath):
    """
    Load Neural CF model embedding layer weights value for latent vector for user & movie
    :param modelpath:
    :return:
    """
    try:
        model = load_model(modelpath)
        logging.info("Model loading completed.")
        return model
    except Exception as e:
        logging.error("Model loading failed." + e)
        return None


def load_usersim(user_sim_matrix_offline, model, user_id_mapping):
    """
    compute cosine similarity value for each user, find top5 similar users to each users
    :param user_sim_matrix_offline: MongoDB collection name
    :param model: Neural CF model
    :param user_id_mapping:
    :return: dictonary : key->userId, value->userId list
    """

    try:
        user_embeddings = model.layers[2].get_weights()[0].astype(np.float16)
        numrow = user_embeddings.shape[0]

        user_sim_dict = {}
        ## calculate cosine sim metric and find most sim user with each user
        for _row in range(numrow):
            _temp_dict = {}
            _sim_matrix = cosine_similarity(user_embeddings[_row, :].reshape(1, 100), user_embeddings)
            top5_users_inner_index = _sim_matrix[0].argsort()[-6:-1][::-1]

            for _inner_idx in top5_users_inner_index:
                ## get real id from user_id_mapping based on inner idx
                _temp_dict[str(user_id_mapping[_inner_idx])] = float(_sim_matrix[0][_inner_idx])

            user_sim_dict[str(user_id_mapping[_row])] = _temp_dict
            break

        users_sim_dict_list = []

        ## reconstruct user_sim_dict into a list for MongoDB insertion
        for key, val in user_sim_dict.items():
            _temp_dict = {}
            _temp_dict['userId'] = int(key)
            _temp_dict['sim_user'] = [int(k) for k in val.keys()]
            users_sim_dict_list.append(_temp_dict)

        user_sim_matrix_offline.insert_many(users_sim_dict_list)
        logging.info("find top 5 most similar user for each user action completed.")
    except Exception as e:
        logging.error("find top 5 most similar user for each user action completed failed." + e)

    return user_sim_dict

def load_moviesim(movie_sim_matrix_offline, model, movie_id_mapping):
    """
    compute cosine similarity value for each movies, find top10 similar movies to each movies
    :param movie_sim_matrix_offline: MongoDB collection name
    :param model: Neural CF model
    :param movie_id_mapping:
    :return: dictonary : key->movieId, value->movieId list
    """

    try:
        movie_embeddings = model.layers[3].get_weights()[0].astype(np.float16)
        numrow = movie_embeddings.shape[0]
        movies_sim_dict = {}

        for _row in range(numrow):
            _movieID = movie_id_mapping[_row]
            _temp_dict = {}
            _sim_matrix = np.dot(movie_embeddings[_row, :].reshape(1, 100), movie_embeddings.T)
            top10_movies_inner_index = _sim_matrix[0].argsort()[-11:-1][::-1]

            for _inner_idx in top10_movies_inner_index:
                ## get real id from movie_id_mapping based on inner idx
                _temp_dict[str(movie_id_mapping[_inner_idx])] = _sim_matrix[0][_inner_idx]

            movies_sim_dict[str(movie_id_mapping[_row])] = _temp_dict
            break

        movies_sim_dict_list = []

        for key, val in movies_sim_dict.items():
            _temp_dict = {}
            _temp_dict['movieId'] = int(key)
            _temp_dict['sim_movie'] = [int(k) for k in val.keys()]
            movies_sim_dict_list.append(_temp_dict)

        movie_sim_matrix_offline.insert_many(movies_sim_dict_list)
        logging.info("find top 10 most similar movies for each movie action completed.")
    except Exception as e:
        logging.error("find top 5 most similar movies for each movie action completed failed." + e)

    return movies_sim_dict


