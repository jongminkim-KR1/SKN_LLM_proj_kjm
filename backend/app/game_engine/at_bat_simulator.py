"""
타석 시뮬레이터 - 확률 기반 결과 계산
"""
import random
from typing import Dict, Tuple


class AtBatSimulator:
    def __init__(self):
        self.outcomes = ['single', 'double', 'triple', 'homerun', 'strikeout', 'walk', 'groundout', 'flyout']

    def simulate(self, batter: Dict, pitcher: Dict, game_state: Dict, strategy: str = None) -> Tuple[str, Dict]:
        b_ratings = batter['ratings_20_80']
        p_ratings = pitcher['ratings_20_80']
        outcome = self._determine_outcome(b_ratings, p_ratings, game_state, strategy)
        details = {'batter_name': batter['name'], 'pitcher_name': pitcher['name']}
        return outcome, details

    def _determine_outcome(self, batter: Dict, pitcher: Dict, state: Dict, strategy: str = None) -> str:
        walk_rate = self._calculate_walk_rate(batter, pitcher, state)
        strikeout_rate = self._calculate_strikeout_rate(batter, pitcher, state)
        hit_rate = self._calculate_hit_rate(batter, pitcher, state)

        power_modifier = 1.0
        if strategy:
            from .strategy import apply_strategy
            modified = apply_strategy({'walk': walk_rate, 'strikeout': strikeout_rate, 'hit': hit_rate}, strategy)
            walk_rate = modified['walk']
            strikeout_rate = modified['strikeout']
            hit_rate = modified['hit']
            power_modifier = modified.get('power_modifier', 1.0)

        rand = random.random() * 100

        if rand < walk_rate:
            return 'walk'
        elif rand < walk_rate + strikeout_rate:
            return 'strikeout'
        elif rand < walk_rate + strikeout_rate + hit_rate:
            return self._determine_hit_type(batter['power'], pitcher['movement'], power_modifier)
        else:
            return 'groundout' if random.random() < 0.55 else 'flyout'

    def _calculate_walk_rate(self, batter: Dict, pitcher: Dict, state: Dict) -> float:
        eye_factor = (batter['eye'] - 50) / 50
        control_factor = (pitcher['control'] - 50) / 50
        walk_rate = 8.5 + eye_factor * 4 - control_factor * 3

        if state.get('runners_in_scoring_position'):
            walk_rate += 1.5

        fatigue = state.get('pitcher_fatigue', 0)
        if fatigue > 70:
            walk_rate += 1.5
        if fatigue > 85:
            walk_rate += 2.5

        return max(3, min(18, walk_rate))

    def _calculate_strikeout_rate(self, batter: Dict, pitcher: Dict, state: Dict) -> float:
        contact_factor = (batter['contact'] - 50) / 50
        stuff_factor = (pitcher['stuff'] - 50) / 50
        k_rate = 23.0 - contact_factor * 8 + stuff_factor * 7

        fatigue = state.get('pitcher_fatigue', 0)
        if fatigue > 70:
            k_rate -= 3
        if fatigue > 85:
            k_rate -= 5

        if state.get('same_handedness'):
            k_rate += 2

        return max(10, min(40, k_rate))

    def _calculate_hit_rate(self, batter: Dict, pitcher: Dict, state: Dict) -> float:
        contact_factor = (batter['contact'] - 50) / 50
        stuff_factor = (pitcher['stuff'] - 50) / 50
        hit_rate = 25.0 + contact_factor * 10 - stuff_factor * 8

        fatigue = state.get('pitcher_fatigue', 0)
        if fatigue > 70:
            hit_rate += 3
        if fatigue > 85:
            hit_rate += 5

        if state.get('same_handedness'):
            hit_rate -= 2

        return max(15, min(40, hit_rate))

    def _determine_hit_type(self, power: int, movement: int, power_modifier: float = 1.0) -> str:
        power_factor = (power - 50) / 50
        movement_factor = (movement - 50) / 50

        hr_rate = (14.0 + power_factor * 8 - movement_factor * 4) * power_modifier
        hr_rate = max(2, min(30, hr_rate))

        xbh_rate = 27.0 + power_factor * 12 - movement_factor * 6
        xbh_rate = max(15, min(45, xbh_rate))

        rand = random.random() * 100

        if rand < hr_rate:
            return 'homerun'
        elif rand < hr_rate + xbh_rate:
            return 'double' if random.random() < 0.92 else 'triple'
        return 'single'
