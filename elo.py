from re import match
import pandas as pd
import numpy as np
import cfbd
import math
from functools import reduce
from datetime import datetime
import random
import seaborn as sns
import matplotlib.pyplot as plt

now = datetime.now()


def elo_calc(results, ratings, k=30):

    # get teams into a list
    teams = [x for x in results["home_team"]]
    for x in results["away_team"]:
        teams.append(x)
    teams = np.unique(teams)

    # initialize elo points
    elo_df = pd.DataFrame(
        [teams, [1500 for x in range(len(teams))]], index=["Team", "Elo"]
    ).transpose()

    # update elo based on results
    home_change = []
    away_change = []
    p5list = ["ACC", "Big 12", "SEC", "Big Ten", "Pac-12", "FBS Independents"]
    prev_season = 0
    for index, row in results.reset_index().iterrows():
        # get information from results dataframe
        home = row["home_team"]
        home_score = float(row["home_points"])
        away = row["away_team"]
        away_score = float(row["away_points"])
        # get elo for each team and find expected winner
        if row["season"] != prev_season:
            # elo_df["Elo"] = 1500 + (0.35 * elo_df["Elo"])
            elo_df["Elo"] = 0.75 * elo_df["Elo"]
            print(f"Simulating {row['season']} season...")
        home_elo = float(elo_df.loc[elo_df["Team"] == home]["Elo"])
        away_elo = float(elo_df.loc[elo_df["Team"] == away]["Elo"])
        elos = {"home": float(home_elo), "away": float(away_elo)}
        # expected = max(elos.keys(), key=(lambda key: elos[key]))
        # determine actual winner based on score
        scores = {"home": home_score, "away": away_score}
        winner = max(scores.keys(), key=(lambda key: scores[key]))
        loser = min(scores.keys(), key=(lambda key: scores[key]))
        home_expected = 1 / (1 + 10 ** ((away_elo - (home_elo + 100)) / 400))
        away_expected = 1 / (1 + 10 ** ((home_elo - (away_elo - 100)) / 400))
        log_part = math.log(abs(home_score - away_score) + 1)
        subtracted = away_elo - home_elo if winner == "home" else home_elo - away_elo
        multiplied_part = 2.2 / ((subtracted) * 0.001 + 2.2)

        mov_multiplier = log_part * multiplied_part
        home_rating = ratings.loc[ratings["team"] == home][row["season"]]
        home_rating = float(home_rating) if len(home_rating.index) > 0 else 1
        away_rating = ratings.loc[ratings["team"] == away][row["season"]]
        away_rating = float(away_rating) if len(away_rating.index) > 0 else 1
        h_p5 = True if row["home_conference"] in p5list else False
        a_p5 = True if row["away_conference"] in p5list else False
        if winner == "away" and not a_p5 and h_p5:
            p5_mult = 2
        elif winner == "home" and not a_p5 and h_p5:
            p5_mult = 0.2
        else:
            p5_mult = 1
        """
        hr_mult = (
            1 * math.log(abs(away_rating) + 1)
            if winner == "home"
            else abs(0.5 * (1 - math.log(abs(away_rating) + 1)))
        )
        ar_mult = (
            1 * math.log(abs(home_rating) + 1)
            if winner == "away"
            else abs(1 * (1 - math.log(abs(home_rating) + 1)))
        )
        """
        hr_mult = 1 + (away_rating / 100)
        ar_mult = 1 + (home_rating / 100)
        new_home_elo = home_elo + (
            k
            * (int(winner == "home") - home_expected)
            * mov_multiplier
            * hr_mult
            * p5_mult
        )

        new_away_elo = away_elo + (
            k
            * (int(winner == "away") - away_expected)
            * mov_multiplier
            * ar_mult
            * p5_mult
        )

        elo_df.loc[elo_df["Team"] == home, "Elo"] = new_home_elo
        elo_df.loc[elo_df["Team"] == away, "Elo"] = new_away_elo
        d_elo_home = new_home_elo - home_elo
        d_elo_away = new_away_elo - away_elo
        home_change.append(d_elo_home)
        away_change.append(d_elo_away)
        prev_season = row["season"]

    results["home_delta_elo"] = home_change
    results["away_delta_elo"] = away_change

    return elo_df, results


def generate_rankings(start, end, currentwk):
    years = range(start, end + 1)
    api = cfbd.GamesApi()

    game_holder = []
    rating_holder = []
    for year in years:
        gamesx = api.get_games(year)
        gamesx2 = pd.DataFrame.from_records([g.to_dict() for g in gamesx])
        game_holder.append(gamesx2)
        rate = cfbd.RatingsApi().get_sp_ratings(year=year)
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
        sp = sp.rename(columns={"rating": year})
        sp = sp.fillna(-40)
        sp[year] = sp[year] + abs(min(sp[year]))
        rating_holder.append(sp)

    ratings = reduce(lambda x, y: pd.merge(x, y, on="team"), rating_holder)

    games = pd.concat(game_holder).reset_index()
    games = games[
        (games["home_points"] == games["home_points"])
        & (games["away_points"] == games["away_points"])
        & (pd.notna(games["home_conference"]))
        & (pd.notna(games["away_conference"]))
    ]
    elo, results = elo_calc(games, ratings)
    elo = elo.sort_values("Elo", ascending=False)
    # print(elo.head(25))
    # print(elo.loc[elo["Team"] == "Texas A&M"])
    week_5 = results.loc[(results["week"] == currentwk) & (results["season"] == end)]

    print(week_5[["home_team", "away_team", "home_delta_elo", "away_delta_elo"]])

    # remove teams that haven't played in 2020
    g2020 = api.get_games(end)
    g2020 = pd.DataFrame.from_records([x.to_dict() for x in g2020])
    week_pred = g2020.copy(deep=True)
    g2020 = g2020[
        (g2020["home_points"] == g2020["home_points"])
        & (g2020["away_points"] == g2020["away_points"])
        & (pd.notna(g2020["home_conference"]))
        & (pd.notna(g2020["away_conference"]))
    ]
    teams = [x for x in g2020["home_team"]]
    for x in g2020["away_team"]:
        teams.append(x)

    teams = np.unique(teams)

    elo2 = elo[elo["Team"].isin(teams)].copy(deep=True)
    elo2 = elo2.dropna()
    elo2["rank"] = range(len(elo2["Team"]))
    elo2["rank"] = elo2["rank"] + 1
    print(elo2.head(25))
    print(elo2["Elo"].astype(float).describe(include="all"))

    return elo, week_pred


# next week predictions
def predict(elo, week_pred, current_week):
    matchups = week_pred[week_pred["week"] == current_week + 1]
    matchups = matchups[
        (pd.notna(matchups["home_conference"]))
        & (pd.notna(matchups["away_conference"]))
    ]
    predictions = []
    for index, game in matchups.iterrows():
        home = game["home_team"]
        away = game["away_team"]
        home_elo = elo[elo["Team"] == home]["Elo"]
        home_elo = float(home_elo)
        away_elo = float(elo[elo["Team"] == away]["Elo"])
        g_dict = {home: home_elo, away: away_elo}
        p_winner = max(g_dict.keys(), key=(lambda key: g_dict[key]))
        p_loser = min(g_dict.keys(), key=(lambda key: g_dict[key]))
        delta_elo = abs(home_elo - away_elo)
        p_delta_elo = home_elo - away_elo
        home_win_pct = 1 / ((10 ** (-p_delta_elo / 400)) + 1)
        predictions.append([p_winner, p_loser, delta_elo, home_win_pct, home])

    prediction_df = pd.DataFrame(
        predictions, columns=["Winner", "Loser", "DeltaElo", "HomeWinPCT", "HomeTeam"]
    )
    print(prediction_df)
    return prediction_df


def simgame(homewinpct):
    roll = random.randint(1, 100) / 100
    if roll > homewinpct:
        home_win = 0
    else:
        home_win = 1
    return home_win


def simulate(predictions, num_epochs):
    results = []
    error = []
    for index, matchup in predictions.iterrows():
        holder = []
        for _ in range(num_epochs):
            holder.append(simgame(matchup["HomeWinPCT"]))
        m = sum(holder) / len(holder)
        e = np.std(holder)
        results.append(m)
        error.append(e)
    predictions["montecarlo"] = results
    predictions["error"] = error
    print(predictions)


elo, week = generate_rankings(2015, 2020, 15)
predictions = predict(elo, week, 15)
simulate(predictions, 5000)
print(f"Time to complete: {datetime.now()-now}")

