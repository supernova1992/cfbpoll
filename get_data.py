import requests
import pandas as pd

#url = 'https://api.collegefootballdata.com/teams/fbs'
params = {'year':2019}

#r = requests.get(url, params)

#team_data = pd.read_json(r.text)

#give team score based on vegas spread

url = 'https://api.collegefootballdata.com/lines'

r = requests.get(url, params)

spreads = pd.read_json(r.text)

