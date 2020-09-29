import pandas as pd

class Matchup:
    def __init__(self, home, away, homescore, awayscore, spread, week, sos):
        self.home = home
        self.away = away
        self.homescore = homescore
        self.awayscore = awayscore
        self.spread = float(spread.split()[-1])
        self.favored_team = ' '.join(spread.split()[:-1]).strip()
        self.away_actual = self.awayscore - self.homescore
        self.home_actual = self.homescore - self.awayscore
        self.home_sos, self.away_sos = [x.values[0] if x.values else -100 for x in sos]

        def get_prev_votes(team):
            vote_history = pd.read_csv('voting_history.csv')
            try:
                return vote_history[team][week-1]
            except KeyError:
                return 0

        self.home_votes = get_prev_votes(self.home)
        self.away_votes = get_prev_votes(self.away)
    
        if self.away_sos < 1:
            self.home_votes += self.homescore*0.1
        else:
            self.home_votes += self.homescore
        if self.home_sos < 10:
            self.away_votes += self.awayscore*0.1
        else:
            self.away_votes += self.awayscore

        self.home_votes += self.spread + self.home_actual + self.away_sos
        self.away_votes += self.spread + self.away_actual + self.home_sos
    
