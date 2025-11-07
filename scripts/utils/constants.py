"""
상수 정의
"""

# MLB API 설정
MLB_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
MLB_SEASON = 2025

# NL West 팀 ID
NL_WEST_TEAMS = {
    119: {
        "name": "Los Angeles Dodgers",
        "short_name": "dodgers",
        "stadium": "Dodger Stadium"
    },
    135: {
        "name": "San Diego Padres",
        "short_name": "padres",
        "stadium": "Petco Park"
    },
    109: {
        "name": "Arizona Diamondbacks",
        "short_name": "diamondbacks",
        "stadium": "Chase Field"
    },
    137: {
        "name": "San Francisco Giants",
        "short_name": "giants",
        "stadium": "Oracle Park"
    },
    115: {
        "name": "Colorado Rockies",
        "short_name": "rockies",
        "stadium": "Coors Field"
    }
}

# 포지션 코드
POSITION_CODES = {
    "P": "Pitcher",
    "C": "Catcher",
    "1B": "First Base",
    "2B": "Second Base",
    "3B": "Third Base",
    "SS": "Shortstop",
    "LF": "Left Field",
    "CF": "Center Field",
    "RF": "Right Field",
    "DH": "Designated Hitter"
}

# 선수 등급 기준
PLAYER_TIER_THRESHOLDS = {
    "superstar": {
        "min_war": 5.0,  # WAR 5.0 이상
        "min_ops": 0.900,  # 타자 OPS 0.900 이상
        "max_era": 3.00    # 투수 ERA 3.00 이하
    },
    "starter": {
        "min_war": 2.0,
        "min_ops": 0.750,
        "max_era": 4.00
    }
    # 나머지는 bench
}

# 게임 능력치 변환 계수
STAT_CONVERSION = {
    "batter": {
        "contact": {
            "base": "avg",
            "scale": 400,
            "offset": 50,
            "baseline": 0.200
        },
        "power": {
            "hr_weight": 1.5,
            "slg_weight": 80
        },
        "eye": {
            "base": "obp",
            "scale": 400,
            "offset": 30,
            "baseline": 0.250
        },
        "speed": {
            "base": "sb",
            "scale": 2.5,
            "offset": 40
        }
    },
    "pitcher": {
        "velocity": {
            "base": "k9",
            "scale": 8,
            "offset": 20
        },
        "control": {
            "base": "bb9",
            "inverse": True,
            "scale": 12,
            "max": 100
        },
        "stuff": {
            "base": "k9",
            "scale": 8,
            "offset": 20
        }
    }
}

