# PandoRec Recommendation System
#### - Bosheng Wu

[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://github.com/BoshengW/PandoRec_MovieRecom)

## Folder Structure
- /Angular: folder for Angular Frontend source code
- /Flask: folder for flask backend application
- /DataPipeline: folder for data pipeline loading and model training

## Installation
#### Angular (Version 7.3.5)
Procedures for setting up Angular Application:

1. move into /Angular folder 
2. run command to install all dependency: 
    ```sh
    npm install
    ```
3. after installation run command to run the application:
    ```sh
    ng serve
    ```


#### Flask 
Procedures for setting up Flask application

1. Create a virtual Env for Flask Application
    ```sh
    virtualenv <env-name>
    ```
2. After setting a virtual env, activate the environment
    ```sh
    <env-foldername>\Scripts\activate
    ```
3. Install dependency package in virtual env, use "requirement.txt" in Flask folder
    ```sh
    pip install -r requirement.txt
    ```
4. In the Flask application, we use our Neural-CF model and some cached json files. Remember modify path of these files in Flask/restapi/recomsys/views.py before you run the application.
    - Neural-CF saved inside: PandoRec_MovieRecom/DataPipeline/EDAPipeline/models/
    - Cached Json save inside:
    PandoRec_MovieRecom/DataPipeline/EDAPipeline/data/json/
5. set up your MongoDB URI
    - Create .env file and set your MongoDB connection;
        ```sh
        MONGODB_URI="<your mongoDB URI>"
        ``` 
6. run the flask application, move to Flask/restapi and run command:
    ```sh
    flask run
    ```
    
#### Data Pipeline
- Create another virtualenv like above, and install all dependencies use "requirement.txt" inside /DataPipeline folder
###### 1. Training Model - Neural-CF model
- Model-Train source code is saved inside EDAPipeline/train/train.py, to train and save model into your local, move to this folder and run command:
    ```sh
    python train.py
    ```
- Training usually take 12 hrs, finally the trained model will save in EDAPipeline/models/

###### 2. Data Pipeline - Load MovieLens-25M raw data inside MongoDB
- Config your MongoDB URI in EDAPipeline/data_pipeline/config, create a .env file and add:
    ```sh
    MONGODB_URI="<your mongoDB URI>"
    ```
- Install MovieLens25M dataset in this link: https://files.grouplens.org/datasets/movielens/ml-25m.zip
- Extract MovieLens25M.zip and save all files into DataPipeline/EDAPipeline/data/ml-25m
- Make sure, trained model is saved in your local /model folder, then run command:
    ```sh
    python datapipeline.py
    ```
- Note: some computations in this pipeline has huge processing effort, so totally, this pipeline will cost >40 hrs to compelete.
####
####
#### --> Now, Everything has set up. Enjoy your journey in PandoRec System!!!


   