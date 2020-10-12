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
            seasons[year] = Season(year, prev_elo)
            prev_elo = seasons[year].elo


class Season:
    def __init__(self, year, prev_elo=None):
        super().__init__()
        self.year = year
        self.prev_elo = prev_elo
        self.tracked_teams = self.get_teams()
        self.elo = self.initialize_elo()
        self.weeks = self.get_stats()

    def initialize_elo(self):
        teams = self.tracked_teams
        if not self.prev_elo:
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
        return week_dict

    def run(self):
        for week in self.weeks:
            self.elo = week.run()


class Week:
    def __init__(self, week, results, prev_elo=0):
        super().__init__()
        self.week = week
        self.results = results
        self.prev_elo = prev_elo

    def run(self):
        elo = self.prev_elo
        return elo
