"""
게임 상태 관리
"""
from typing import Dict


class GameState:
    def __init__(self, away_team: str, home_team: str, start_inning: int = 7):
        self.home_team = home_team
        self.away_team = away_team
        self.home_score = 0
        self.away_score = 0
        self.inning = start_inning
        self.is_bottom = False
        self.outs = 0
        self.balls = 0
        self.strikes = 0
        self.runners = {1: None, 2: None, 3: None}
        self.home_pitcher_pitches = 0
        self.away_pitcher_pitches = 0
        self.pitcher_hits_allowed = 0
        self.play_log = []

    @property
    def current_team(self) -> str:
        return self.home_team if self.is_bottom else self.away_team

    @property
    def pitcher_pitches(self) -> int:
        return self.away_pitcher_pitches if self.is_bottom else self.home_pitcher_pitches

    @pitcher_pitches.setter
    def pitcher_pitches(self, value: int):
        if self.is_bottom:
            self.away_pitcher_pitches = value
        else:
            self.home_pitcher_pitches = value

    @property
    def pitcher_fatigue(self) -> int:
        return min(100, (self.pitcher_pitches / 120) * 100)

    @property
    def runners_in_scoring_position(self) -> bool:
        return self.runners[2] is not None or self.runners[3] is not None

    def add_runner(self, base: int, player_name: str):
        self.runners[base] = player_name

    def clear_bases(self):
        self.runners = {1: None, 2: None, 3: None}

    def advance_runners(self, bases: int) -> int:
        runs_scored = 0
        for base in [3, 2, 1]:
            if self.runners[base] is not None:
                new_base = base + bases
                if new_base >= 4:
                    runs_scored += 1
                    self.runners[base] = None
                else:
                    self.runners[new_base] = self.runners[base]
                    self.runners[base] = None
        return runs_scored

    def record_out(self) -> bool:
        self.outs += 1
        return self.outs >= 3

    def end_half_inning(self):
        self.outs = 0
        self.clear_bases()
        if self.is_bottom:
            self.inning += 1
            self.is_bottom = False
        else:
            self.is_bottom = True

    def add_score(self, runs: int):
        if self.is_bottom:
            self.home_score += runs
        else:
            self.away_score += runs

    def is_game_over(self) -> bool:
        if self.inning >= 9 and self.is_bottom and self.home_score > self.away_score:
            return True
        if self.inning > 9 and self.home_score != self.away_score:
            return True
        return False

    def get_state_dict(self) -> Dict:
        return {
            'inning': self.inning,
            'is_bottom': self.is_bottom,
            'outs': self.outs,
            'home_score': self.home_score,
            'away_score': self.away_score,
            'runners': self.runners.copy(),
            'pitcher_pitches': self.pitcher_pitches,
            'pitcher_fatigue': self.pitcher_fatigue,
            'runners_in_scoring_position': self.runners_in_scoring_position
        }

    def get_summary(self) -> str:
        inning_str = f"{self.inning}회 {'말' if self.is_bottom else '초'}"
        score_str = f"{self.away_team} {self.away_score} - {self.home_score} {self.home_team}"
        outs_str = f"{self.outs}아웃"
        on_base = [str(b) for b in [1, 2, 3] if self.runners[b] is not None]
        runners_str = f"{', '.join(on_base)}루 주자" if on_base else "주자 없음"
        return f"{inning_str} | {score_str} | {outs_str} | {runners_str}"
