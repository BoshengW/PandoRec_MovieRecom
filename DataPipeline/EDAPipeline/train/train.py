# filter out unncessary warnings
import warnings
warnings.filterwarnings('ignore')

import json
# To store\load the data
import pandas as pd
import numpy as np

from keras.layers import Input, Embedding, Reshape, Dot, Concatenate, Dense, Dropout
from keras.models import Model

from sklearn.metrics import mean_squared_error

path = "../data/ml-25m/ratings.csv"

def train_dataset_generation(path):

    df = pd.read_csv(path)

    ## get dataset index

    full_movies = df.movieId.index.tolist()
    full_users = df.userId.index.tolist()

    df_full_dataset = df.drop('timestamp', axis=1).sample(frac=1).reset_index(drop=True)

    ## Test dataset size
    n = 400000

    ## split train-test dataset
    df_train_full = df_full_dataset[:-n]
    df_test_full = df_full_dataset[-n:]

    ## inner ID convert: convert real ID into inner training ID
    user_id_mapping_full = {id: i for i, id in enumerate(df_full_dataset['userId'].unique())}
    movie_id_mapping_full = {id: i for i, id in enumerate(df_full_dataset['movieId'].unique())}

    # use dataframe map function to map users & movies to mapped ids based on above mapping
    train_user_data_full = df_train_full['userId'].map(user_id_mapping_full)
    train_movie_data_full = df_train_full['movieId'].map(movie_id_mapping_full)

    # do the same for test data
    test_user_data_full = df_test_full['userId'].map(user_id_mapping_full)
    test_movie_data_full = df_test_full['movieId'].map(movie_id_mapping_full)

    # package all process data
    train_test_dict = {
        "train_test_df": [df_train_full, df_test_full],
        "train": [train_movie_data_full, train_user_data_full],
        "test": [test_movie_data_full, test_user_data_full],
        "ID_Mapping": [movie_id_mapping_full, user_id_mapping_full]
    }


    return train_test_dict

def model_build(user_embed, movie_embed, movie_id_mapping, user_id_mapping):
    # setup NN parameters
    user_embed_dim = user_embed
    movie_embed_dim = movie_embed
    userid_input_shape = 1
    movieid_input_shape = 1

    user_id_mapping_full = user_id_mapping
    movie_id_mapping_full = movie_id_mapping

    # user and movie input layers
    user_id_input = Input(shape=(userid_input_shape,), name='user')
    movie_id_input = Input(shape=(movieid_input_shape,), name='movie')

    # Create embeddings layers for users and movies

    # user embedding
    user_embedding = Embedding(output_dim=user_embed_dim,
                               input_dim=len(user_id_mapping_full),
                               input_length=userid_input_shape,
                               name='user_embedding')(user_id_input)

    # movie embedding
    movie_embedding = Embedding(output_dim=movie_embed_dim,
                                input_dim=len(movie_id_mapping_full),
                                input_length=movieid_input_shape,
                                name='movie_embedding')(movie_id_input)

    # Reshape both user and movie embedding layers
    user_vectors = Reshape([user_embed_dim])(user_embedding)
    movie_vectors = Reshape([movie_embed_dim])(movie_embedding)

    # Concatenate all layers into one
    hybrid_layer = Concatenate()([user_vectors, movie_vectors])

    # add in dense and output layers
    dense = Dense(512, activation='relu')(hybrid_layer)
    dense = Dropout(0.2)(dense)
    output = Dense(1)(dense)

    model = Model(inputs=[user_id_input, movie_id_input], outputs=output)
    model.compile(loss='mse', optimizer='adam')

    print(model.summary())

    return model

def train_model(train_movie_data_full, train_user_data_full, df_train_full, model):
    # fit the model
    batch_size = 1024
    epochs = 10

    # feed train data inside
    X = [train_user_data_full, train_movie_data_full]
    y = df_train_full['rating']
    model.fit(X, y,
              batch_size=batch_size,
              epochs=epochs,  ## Change the epochs to find better improved model.
              validation_split=0.1,
              shuffle=True)

    return model


def eval_model(test_movie_data_full, test_user_data_full, df_test_full, model):
    # Test model by making predictions on test data
    y_pred_full = model.predict([test_user_data_full, test_movie_data_full]).ravel()
    # clip upper and lower ratings
    y_pred_full = list(map(lambda x: 1.0 if x < 1 else 5.0 if x > 5.0 else x, y_pred_full))
    # get true labels
    y_true_full = df_test_full['rating'].values

    #  Compute RMSE
    mse = np.sqrt(mean_squared_error(y_pred=y_pred_full, y_true=y_true_full))
    print('\n\nTesting Result With DL Matrix-Factorization: {:.4f} RMSE'.format(mse))

    return


if __name__=="__main__":
    train_test_dict = train_dataset_generation(path)

    ## extract train test dataset
    movie_id_mapping_full, user_id_mapping_full = train_test_dict["ID_Mapping"]
    train_movie_data_full, train_user_data_full = train_test_dict["train"]
    test_movie_data_full, test_user_data_full = train_test_dict["test"]
    df_train_full, df_test_full = train_test_dict["train_test_df"]

    ## generate model
    model = model_build(100, 100, movie_id_mapping_full, user_id_mapping_full)

    ## train model
    model = train_model(train_movie_data_full, train_user_data_full, df_train_full, model)

    ## evaluate model by test dataset
    eval_model(test_movie_data_full, test_user_data_full,df_test_full, model)

    ## save model
    model.save("../models/neural_cf")

    ## save Movie&User ID mapping for future prediction

    with open('../data/json/user_id_map.json', 'w+') as f:
        json.dump(user_id_mapping_full, f)

    with open('../data/json/movie_id_map.json', 'w+') as f:
        json.dump(movie_id_mapping_full, f)
    f.close()

    print("Model and ID_mapping saved successfully")
