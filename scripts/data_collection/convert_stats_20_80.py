"""
MLB 스탯을 20-80 스케일 게임 능력치로 변환
"""
import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def clamp(value, min_val=20, max_val=80):
    """값을 20-80 범위로 제한"""
    return max(min_val, min(max_val, int(value)))


def convert_batter_to_20_80(player):
    """타자를 20-80 스케일로 변환"""
    mlb_stats = player.get('stats_2024', {})
    fg_stats = player.get('fangraphs_stats', {})

    # 데이터 부족 체크 - 최소 200타석 필요 (약 50경기)
    pa = int(mlb_stats.get('plateAppearances', 0))
    if pa < 200:
        return {
            "contact": 40, "power": 40, "eye": 40,
            "speed": 40, "defense": 40, "overall": 40
        }

    # FanGraphs %는 소수(0.257)로 들어옴 -> 퍼센트로 변환
    # Contact (컨택) - K%, AVG 기반으로 더 넓은 범위 사용
    k_pct = fg_stats.get('K%', 0.23) * 100  # 소수를 %로 변환
    avg = float(mlb_stats.get('avg', 0.250))

    # K% 기반 (MLB 평균 23% 기준)
    # 범위를 넓혀서 차이를 명확하게
    contact_base = 50 + (23 - k_pct) * 1.5  # K% 1%당 1.5점 차이

    # AVG 보정 (MLB 평균 .250 기준)
    avg_bonus = (avg - 0.250) * 100  # .010당 10점

    contact = contact_base + avg_bonus

    # Power (장타력) - ISO, HR 기반으로 더 강하게 반영
    iso = fg_stats.get('ISO', 0.150)
    hr = int(mlb_stats.get('homeRuns', 0))

    # ISO 기반 (MLB 평균 .150 기준)
    power_base = 50 + (iso - 0.150) * 200  # ISO .001당 0.2점

    # HR 보정 - 홈런 개수는 매우 중요
    if hr >= 50:
        hr_bonus = 20
    elif hr >= 40:
        hr_bonus = 15
    elif hr >= 30:
        hr_bonus = 10
    elif hr >= 25:
        hr_bonus = 7
    elif hr >= 20:
        hr_bonus = 5
    elif hr >= 15:
        hr_bonus = 3
    else:
        hr_bonus = (hr - 10) * 0.3  # 10홈런 이하는 약한 보정

    power = power_base + hr_bonus

    # Eye (선구안) - BB% 기반 (MLB 평균 8.5% 기준)
    bb_pct = fg_stats.get('BB%', 0.085) * 100

    eye = 50 + (bb_pct - 8.5) * 2.5  # BB% 1%당 2.5점 차이

    # Speed (주루) - BsR, SB 기반으로 더 넓은 범위
    bsr = fg_stats.get('BsR', 0.0)
    sb = int(mlb_stats.get('stolenBases', 0))

    # BsR 기반 (평균 0.0 기준)
    speed_base = 50 + bsr * 4  # BsR 1.0당 4점

    # 도루 보정
    sb_bonus = min(sb * 0.4, 20)  # 도루 1개당 0.4점, 최대 20점

    speed = speed_base + sb_bonus

    # Defense (수비) - Def, 포지션 기반
    defense_val = fg_stats.get('Def', 0.0)
    position = player.get('position', 'LF')

    if defense_val >= 10:
        defense = 70
    elif defense_val >= 5:
        defense = 65
    elif defense_val >= 2:
        defense = 60
    elif defense_val >= -2:
        defense = 50
    elif defense_val >= -5:
        defense = 45
    else:
        defense = 40

    # 포지션 난이도 보정
    if position in ['SS', 'CF', 'C']:
        defense += 5
    elif position in ['1B', 'DH', 'TWP']:
        defense -= 3

    # Overall (종합) - 공격형 선수 가중치 증가
    overall = (contact * 0.22 + power * 0.28 + eye * 0.22 +
               speed * 0.18 + defense * 0.10)

    return {
        "contact": clamp(contact),
        "power": clamp(power),
        "eye": clamp(eye),
        "speed": clamp(speed),
        "defense": clamp(defense),
        "overall": clamp(overall)
    }


def convert_pitcher_to_20_80(player):
    """투수를 20-80 스케일로 변환"""
    mlb_stats = player.get('stats_2024', {})
    fg_stats = player.get('fangraphs_stats', {})

    # 데이터 부족 체크 - 최소 30이닝 필요 (불펜 포함)
    ip = float(mlb_stats.get('inningsPitched', '0'))
    if ip < 30:
        return {
            "stuff": 40, "control": 40, "movement": 40,
            "stamina": 40, "pitchability": 40, "overall": 40
        }

    # Stuff (구위) - K% 기반 (MLB 평균 22% 기준)
    k_pct = fg_stats.get('K%', 0.22) * 100

    stuff = 50 + (k_pct - 22) * 2.5  # K% 1%당 2.5점 차이

    # Control (제구력) - BB% 기반 (MLB 평균 8.5% 기준, 낮을수록 좋음)
    bb_pct = fg_stats.get('BB%', 0.085) * 100

    control = 50 + (8.5 - bb_pct) * 3  # BB% 1% 낮을수록 3점 상승

    # Movement (무브먼트) - GB% 기반 (MLB 평균 44% 기준)
    gb_pct = fg_stats.get('GB%', 0.44) * 100

    movement = 50 + (gb_pct - 44) * 2  # GB% 1%당 2점 차이

    # Stamina (스태미너) - IP 기반
    if ip >= 180:
        stamina = 70
    elif ip >= 160:
        stamina = 65
    elif ip >= 140:
        stamina = 60
    elif ip >= 120:
        stamina = 55
    elif ip >= 100:
        stamina = 50
    elif ip >= 70:
        stamina = 55
    elif ip >= 50:
        stamina = 50
    else:
        stamina = 45

    # Pitchability (투구 센스) - FIP만 사용
    fip = fg_stats.get('FIP', 4.00)

    if fip <= 2.50:
        pitchability = 75
    elif fip <= 3.00:
        pitchability = 70
    elif fip <= 3.50:
        pitchability = 65
    elif fip <= 4.00:
        pitchability = 60
    elif fip <= 4.50:
        pitchability = 55
    elif fip <= 5.00:
        pitchability = 50
    elif fip <= 5.50:
        pitchability = 45
    else:
        pitchability = 40

    # Overall (종합)
    overall = (stuff * 0.30 + control * 0.25 + movement * 0.15 +
               stamina * 0.15 + pitchability * 0.15)

    return {
        "stuff": clamp(stuff),
        "control": clamp(control),
        "movement": clamp(movement),
        "stamina": clamp(stamina),
        "pitchability": clamp(pitchability),
        "overall": clamp(overall)
    }


def convert_team_data(team_file):
    """팀 데이터 변환"""
    with open(team_file, 'r', encoding='utf-8') as f:
        team_data = json.load(f)

    print(f"Converting {team_data['team_name']}...")

    for pitcher in team_data['pitchers']:
        pitcher['ratings_20_80'] = convert_pitcher_to_20_80(pitcher)

    for batter in team_data['batters']:
        batter['ratings_20_80'] = convert_batter_to_20_80(batter)

    with open(team_file, 'w', encoding='utf-8') as f:
        json.dump(team_data, f, indent=2, ensure_ascii=False)

    print(f"  {len(team_data['pitchers'])} pitchers, {len(team_data['batters'])} batters")


def main():
    print("\nConverting to 20-80 Scale\n")

    teams_dir = project_root / "data" / "mlb" / "nl_west" / "teams"

    for team_file in sorted(teams_dir.glob("*.json")):
        if team_file.name == "collection_summary.json":
            continue
        convert_team_data(team_file)

    print("\nConversion complete!")


if __name__ == "__main__":
    main()
