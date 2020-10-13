import pandas as pd
import numpy as np
import cfbd
import math
from functools import reduce


class Poll:
    def __init__(self, start_year, end_year, current_week):
        super().__init__()
        # should add some logic to do this instead, but whatever.
        self.start = start_year
        self.end = end_year
        self.week = current_week

    def simulate(self):
        return

    def run(self):
        self.seasons = {}
        prev_elo = None
        for year in range(self.start, self.end + 1):
            self.seasons[year] = Season(year, prev_elo)
            prev_elo = self.seasons[year].elo

        print("complete")


class Season:
    def __init__(self, year, prev_elo=None):
        super().__init__()
        self.year = year
        self.prev_elo = prev_elo
        self.tracked_teams = self.get_teams()
        self.elo = self.initialize_elo()
        self.get_stats()

    def initialize_elo(self):
        teams = self.tracked_teams
        if self.prev_elo is None:
            elo = 1500
            df = pd.DataFrame(
                [teams, [elo for x in range(len(teams))]], index=["team", "elo"]
            ).transpose()
            return df

        df = self.prev_elo
        df["elo"] = (df["elo"] * 0.05) + 1500
        return df

    def get_teams(self):
        response = cfbd.TeamsApi().get_fbs_teams()
        return [x.to_dict()["school"] for x in response]

    def get_stats(self):
        response = cfbd.GamesApi().get_games(self.year)
        df = pd.DataFrame.from_records([x.to_dict() for x in response])
        weeks = np.unique(df["week"])
        week_dict = {}
        for w in weeks:
            week_dict[w] = Week(w, df[df["week"] == w])
        self.weeks = week_dict


class Week:
    def __init__(self, week, results, prev_elo=0):
        super().__init__()
        self.week = week
        self.results = results
        self.prev_elo = prev_elo
        self.combined = pd.merge(
            self.results, self.prev_elo, left_on="home_team", right_on="team"
        )
        self.combined = pd.merge(
            self.combined, self.prev_elo, left_on="away_team", right_on="team"
        )
        self.games = []
        for _, row in self.combined.iterrows():
            self.games.append(Game(row))


class Game:
    def __init__(self, data):
        self.home = data["home_team"]
        self.away = data["away_team"]
        self.home_score = data["home_points"]
        self.away_score = data["away_points"]


p = Poll(2010, 2020, 6)
p.run()
print(p.seasons[2019].weeks[1])
