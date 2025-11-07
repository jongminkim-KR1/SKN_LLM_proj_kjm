"""
투수/타격 전략 시스템
"""


PITCHING_STRATEGIES = {
    'aggressive': {'name': '적극 승부', 'walk': 0.4, 'strikeout': 1.6, 'hit': 1.3, 'power': 1.4},
    'careful': {'name': '신중하게', 'walk': 1.8, 'strikeout': 0.6, 'hit': 0.6, 'power': 0.5},
    'intentional_walk': {'name': '고의4구', 'walk': 999, 'strikeout': 0, 'hit': 0, 'power': 0}
}

BATTING_STRATEGIES = {
    'power_swing': {'name': '적극 스윙', 'walk': 0.3, 'strikeout': 1.5, 'hit': 1.6, 'power': 2.2},
    'contact_swing': {'name': '컨택 중심', 'walk': 0.7, 'strikeout': 0.5, 'hit': 1.4, 'power': 0.6},
    'patient': {'name': '볼넷 노림', 'walk': 2.5, 'strikeout': 0.7, 'hit': 0.7, 'power': 0.4}
}

STRATEGIES = {**PITCHING_STRATEGIES, **BATTING_STRATEGIES}


def apply_strategy(rates, strategy_name):
    if strategy_name not in STRATEGIES:
        return rates

    strategy = STRATEGIES[strategy_name]
    return {
        'walk': rates['walk'] * strategy['walk'],
        'strikeout': rates['strikeout'] * strategy['strikeout'],
        'hit': rates['hit'] * strategy['hit'],
        'power_modifier': strategy['power']
    }
