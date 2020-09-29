import cfbd
import pandas as pd
import numpy as np

api = cfbd.GamesApi()

games = api.get_games(2020)

vegas = cfbd.BettingApi()

bets = vegas.get_lines(year=2020)

bdf = pd.DataFrame.from_records([b.to_dict() for b in bets])

lines = [x for x in bdf["lines"]]
ids = [x for x in bdf["id"]]

cons = []
for l in lines:
    if not any(d["provider"] == "consensus" for d in l):
        cons.append("na")
    else:
        for i in l:
            if i["provider"] == "consensus":
                cons.append(i["spread"])


cdf = (
    pd.DataFrame(
        [
            ids,
            [x if x not in [None, "na"] else 0 for x in cons],
            [-x if x not in [None, "na"] else 0 for x in cons],
        ],
        index=["id", "home_vegas", "away_vegas"],
    )
    .transpose()
    .astype("float")
)

# teams only get the fraction of the spread that they beat. i.e. if tamu is predicted to win by 40 but only wins by 20 then they get 0.5*(winning point score) and vice versa for the losing team

df = pd.DataFrame.from_records([g.to_dict() for g in games])

df = df.merge(cdf, on="id", how="left").reset_index()

df = df[
    (df["home_points"] == df["home_points"])
    & (df["away_points"] == df["away_points"])
    & (pd.notna(df["home_conference"]))
    & (pd.notna(df["away_conference"]))
]
df["home_spread"] = np.where(
    df["neutral_site"] == True,
    df["home_points"] - df["away_points"],
    (df["home_points"] - df["away_points"] - 2.5 + df["home_vegas"] * 0.25),
)
df["away_spread"] = -df["home_spread"]

teams = pd.concat(
    [
        df[["home_team", "home_spread", "away_team"]].rename(
            columns={
                "home_team": "team",
                "home_spread": "spread",
                "away_team": "opponent",
            }
        ),
        df[["away_team", "away_spread", "home_team"]].rename(
            columns={
                "away_team": "team",
                "away_spread": "spread",
                "home_team": "opponent",
            }
        ),
    ]
)

spreads = teams.groupby("team").spread.mean()
print(spreads.head())

terms = []
solutions = []

for team in spreads.keys():
    row = []
    opps = list(teams[teams["team"] == team]["opponent"])

    for opp in spreads.keys():
        if opp == team:
            row.append(1)
        elif opp in opps:
            row.append(-1.0 / len(opps))
        else:
            row.append(0)

    terms.append(row)

    solutions.append(spreads[team])

# print(terms, solutions)

# solutions = np.linalg.solve(np.array(terms), np.array(solutions))

ratings = list(zip(spreads.keys(), solutions))
srs = pd.DataFrame(ratings, columns=["team", "rating"])
rankings = srs.sort_values("rating", ascending=False).reset_index()[["team", "rating"]]

print(rankings.loc[:24])

