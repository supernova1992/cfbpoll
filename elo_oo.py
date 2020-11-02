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
            self.seasons[year].update()
            prev_elo = self.seasons[year].new_elo


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
        rate = cfbd.RatingsApi().get_sp_ratings(year=self.year)
        sp = pd.DataFrame.from_records([x.to_dict() for x in rate])
        sp = sp.drop(
            [
                "year",
                "conference",
                "second_order_wins",
                "sos",
                "offense",
                "defense",
                "special_teams",
            ],
            axis=1,
        )
        sp["rating"] = sp["rating"] + abs(min(sp["rating"]))
        df = pd.merge(
            df, sp, left_on="home_team", right_on="team", suffixes=("_home", "_away")
        )
        df = pd.merge(
            df, sp, left_on="away_team", right_on="team", suffixes=("_home", "_away")
        )
        weeks = np.unique(df["week"])
        week_dict = {}
        for w in weeks:
            week_dict[w] = Week(w, df[df["week"] == w], self.elo)
            self.elo = week_dict[w].prev_elo
        self.weeks = week_dict

    def update(self):
        self.week_results = []
        for week in self.weeks.values():
            self.week_results.append(week.update())
        self.home_teams = self.week_results[0]
        self.home_teams = self.home_teams.rename({"elo": 0}, axis="columns")
        for i, w in enumerate(self.week_results[1:]):
            w = w.rename({"elo": i + 1}, axis="columns")
            if i == 0:
                self.home_teams = pd.merge(self.home_teams, w, on="team", how="outer")
            else:
                self.home_teams = pd.merge(self.home_teams, w, on="team", how="outer")
        print(len(self.home_teams))
        for i in range(15):
            if i == 0:
                self.home_teams[i] = self.home_teams[i].fillna(self.home_teams[i + 1])
            else:
                self.home_teams[i] = self.home_teams[i].fillna(self.home_teams[i - 1])
        self.new_elo = self.home_teams.filter(["team", 14], axis=1)
        self.new_elo = self.new_elo.rename({14: "elo"}, axis="columns")


class Week:
    def __init__(self, week, results, prev_elo=None):
        super().__init__()
        self.week = week
        self.results = results
        self.prev_elo = prev_elo
        self.combined = pd.merge(
            self.results,
            self.prev_elo,
            left_on="home_team",
            right_on="team",
            suffixes=("_home", "_away"),
        )
        self.combined = pd.merge(
            self.combined,
            self.prev_elo,
            left_on="away_team",
            right_on="team",
            suffixes=("_home", "_away"),
        )
        self.games = []
        for _, row in self.combined.iterrows():
            self.games.append(Game(row))

    def update(self):
        teams = []
        elo = []
        for game in self.games:
            game.update_elo()
            teams.append(game.home)
            elo.append(game.home_elo)
            teams.append(game.away)
            elo.append(game.away_elo)
        df = pd.DataFrame([teams, elo], index=["team", "elo"]).transpose()
        return df


class Game:
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.home = data["home_team"]
        self.away = data["away_team"]
        self.home_score = data["home_points"]
        self.away_score = data["away_points"]
        self.home_elo = data["elo_home"]
        self.away_elo = data["elo_away"]
        self.home_rating = data["rating_home"]
        self.away_rating = data["rating_away"]

    def update_elo(self):
        k = 20
        scores = {"home": self.home_score, "away": self.away_score}
        elos = {"home": self.home_elo, "away": self.away_elo}
        winner = max(scores.keys(), key=(lambda key: scores[key]))
        loser = min(scores.keys(), key=(lambda key: scores[key]))
        home_expected = 1 / (1 + 10 ** ((self.away_elo - (self.home_elo + 100)) / 400))
        away_expected = 1 / (1 + 10 ** ((self.home_elo - (self.away_elo - 100)) / 400))
        log_part = math.log(abs(self.home_score - self.away_score) + 1)
        subtracted = (
            self.away_elo - self.home_elo
            if winner == "home"
            else self.home_elo - self.away_elo
        )
        multiplied_part = 2.2 / ((subtracted) * 0.001 + 2.2)
        mov_multiplier = log_part * multiplied_part
        home_rating = self.home_rating
        home_rating = float(home_rating) if home_rating > 0 else 1
        away_rating = self.away_rating
        away_rating = float(away_rating) if away_rating > 0 else 1
        new_home_elo = self.home_elo + (
            k * (int(winner == "home") - home_expected) * mov_multiplier
        ) * (0.5 * abs(home_rating - away_rating))
        new_away_elo = self.away_elo + (
            k * (int(winner == "away") - away_expected) * mov_multiplier
        ) * (0.5 * abs(home_rating - away_rating))
        self.delta_home_elo = new_home_elo - self.home_elo
        self.delta_away_elo = new_away_elo - self.away_elo
        self.home_elo = new_home_elo
        self.away_elo = new_away_elo


p = Poll(2019, 2020, 6)
p.run()
out = p.seasons[2020].week_results[5].sort_values("elo", ascending=False)
print(out.head(25))

