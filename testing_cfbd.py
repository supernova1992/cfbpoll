import cfbd
import pandas as pd
import numpy as np

api = cfbd.GamesApi()
games2019 = api.get_games(2019)
g2019 = pd.DataFrame.from_records([g.to_dict() for g in games2019])
g2019 = g2019.loc[g2019["week"] >= 11]

games = api.get_games(2020)

vegas = cfbd.BettingApi()
bets2019 = vegas.get_lines(year=2019)
bets = vegas.get_lines(year=2020)
b2019 = pd.DataFrame.from_records([b.to_dict() for b in bets2019])
b2019 = b2019.loc[b2019["week"] >= 11]

bdf = pd.DataFrame.from_records([b.to_dict() for b in bets])
bdf = pd.concat([b2019, bdf]).reset_index()


rate = cfbd.RatingsApi().get_sp_ratings(year=2020)
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


df = pd.DataFrame.from_records([g.to_dict() for g in games])
df = pd.concat([g2019, df]).reset_index()
df = df.merge(cdf, on="id", how="left").reset_index()
df["home_vegas"] = np.where(
    df["home_vegas"] == 0, df["home_points"] - df["away_points"], df["home_vegas"]
)

df["home_sp"] = df["home_team"].map(sp.set_index("team")["rating"])
df["away_sp"] = df["away_team"].map(sp.set_index("team")["rating"])


df = df[
    (df["home_points"] == df["home_points"])
    & (df["away_points"] == df["away_points"])
    & (pd.notna(df["home_conference"]))
    & (pd.notna(df["away_conference"]))
]
"""
df["home_spread"] = np.where(
    df["neutral_site"] == True,
    df["home_points"] - df["away_points"] - df["home_vegas"],
    (df["home_points"] - df["away_points"] - 2.5 - df["home_vegas"]),
)
"""
df["home_spread"] = np.where(
    df["neutral_site"] == True,
    df["home_points"] - df["away_points"],
    (df["home_points"] - df["away_points"] - 2.5),
)
df["away_spread"] = -df["home_spread"] - (df["home_sp"] * 0.1)


df["home_spread"] = df["home_spread"] - (df["away_sp"] * 0.1)


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
try:
    solutions = np.linalg.solve(np.array(terms), np.array(solutions))
except:
    print("singular matrix")


ratings = list(zip(spreads.keys(), solutions))
srs = pd.DataFrame(ratings, columns=["team", "rating"])
rankings = srs.sort_values("rating", ascending=False).reset_index()[["team", "rating"]]

print(rankings.loc[:24])

