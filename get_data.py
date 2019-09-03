import requests
import pandas as pd
from poll import Matchup
import ast


def get_team_info():
    """Grab the information on all FBS teams"""
    url = 'https://api.collegefootballdata.com/teams/fbs'
    params = {'year':2019}

    r = requests.get(url, params)

    team_data = pd.read_json(r.text)

    team_data.to_csv('team_data.csv')

    vote_data = pd.DataFrame({team:0 for team in team_data['school']}, index=[0])
    vote_data.to_csv('voting_history.csv')


def get_spread(week, home):
    """Get the vegas spread for a defined week's games"""
    vegas = pd.read_csv(f"week{week}spreads.csv")
    spreads = vegas['lines'][vegas['homeTeam'] == home].values[0].replace('[','').replace(']','').replace('{','').replace('}','').split(',')
    spreads = [z.split(': ') for z in spreads]
    spreads = {x.replace("'",""):y.replace("'","") for x,y in spreads}
    return spreads[' formattedSpread']


def get_matchups(week):
    url = 'https://api.collegefootballdata.com/games'
    params = {'year':2019,'week':week}
    r = requests.get(url, params)
    matchups = pd.read_json(r.text)
    m = [Matchup(a, b, c, d, get_spread(week, a), week) for a,b,c,d in zip(matchups['home_team'],matchups['away_team'],matchups['home_points'],matchups['away_points'])]
    return m

z = get_matchups(1)
votes = {x.home:x.home_votes for x in z}
votes2 = {x.away:x.away_votes for x in z}
votes.update(votes2)

print(sorted(votes.items(), key=lambda x: x[1], reverse=True)[:25])

'''
url = 'https://api.collegefootballdata.com/games/teams'
params = {'year':2019,'week':1}

r = requests.get(url, params)

d = r.json()

for item in d[0]['teams'][0]['stats']:
    if item['category'] == 'totalYards':
        print(f"Total yards: {item['stat']}")
'''
