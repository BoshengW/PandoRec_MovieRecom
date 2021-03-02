import pandas as pd
import numpy as np
import re
import json

## extract year by regex
def extract_year(row):
    get_year = re.findall(r'\(\d{4}\)', row)
    if not get_year:
        return 'unknown'
    return get_year[0][1:-1]

## remove release year in title
def simplify_title(row):
    row = re.sub(r'\(\d{4}\)','', row) ## hardcode remove ('year-of-release')
    return row

def one_hot(row):
    """
    This func used for pandas apply lambda function,
    which is for convert catalog A|B|C|D|... into catalog columns A, B, C,D
    :param row:
    :return:
    """
    list_of_movieTags = row.genres.split('|')
    for tag in list_of_movieTags:
        row[tag] = 1
    return row

def save_json(filepath, target):
    """
    General save dict into json function
    :param filepath: detination path
    :param target: target dictionary
    :return: boolean -> success or not
    """
    try:
        with open(filepath, "r") as f:
            json.dump(target,f)
        return True
    except Exception as e:
        print(e)
        return False

