import requests
import pandas as pd
from poll import Matchup


def get_team_info():
    """Grab the information on all FBS teams"""
    url = 'https://api.collegefootballdata.com/teams/fbs'
    params = {'year':2019}

    r = requests.get(url, params)

    team_data = pd.read_json(r.text)

    team_data.to_csv('team_data.csv')

    vote_data = pd.DataFrame({team:0 for team in team_data['school']}, index=[0])
    vote_data.to_csv('voting_history.csv')


def get_spread(week):
    """Get the vegas spread for a defined week's games"""
    url = 'https://api.collegefootballdata.com/lines'
    params = {'year':2019,'week':week}
    r = requests.get(url, params)
    vegas = pd.read_json(r.text)
    spreads = [x[0]['spread'] for x in vegas['lines'] if x]
    return spreads


def get_matchups(week):
    url = 'https://api.collegefootballdata.com/games'
    params = {'year':2019,'week':week}
    r = requests.get(url, params)
    matchups = pd.read_json(r.text)
    m = [Matchup(a, b, c, d, e, week) for a,b,c,d,e in zip(matchups['home_team'],matchups['away_team'],matchups['home_points'],matchups['away_points'],get_spread(week))]
    return m

z = get_matchups(1)

print(z[0].spread, z[0].away_actual, z[0].home_actual, z[0].home_votes, z[0].away_votes)