"""
FanGraphs 고급 지표를 기존 데이터에 추가
"""
import json
import sys
import unicodedata
from pathlib import Path
from pybaseball import batting_stats, pitching_stats
import warnings
warnings.filterwarnings('ignore')

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def remove_accents(text):
    """악센트 제거"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join([c for c in nfkd if not unicodedata.combining(c)])


def load_fangraphs_data(season=2024):
    """FanGraphs에서 고급 지표 로드"""
    print(f"Loading FanGraphs {season} data...")

    # 타자 데이터 (qual=1: 최소 1타석)
    batters = batting_stats(season, qual=1)
    print(f"Loaded {len(batters)} batters")

    # 투수 데이터 (qual=1: 최소 1이닝)
    pitchers = pitching_stats(season, qual=1)
    print(f"Loaded {len(pitchers)} pitchers")

    return batters, pitchers


def find_player_in_fangraphs(player_name, fg_data):
    """FanGraphs 데이터에서 선수 찾기 (악센트 처리)"""
    # 악센트 제거
    clean_name = remove_accents(player_name)
    last_name = clean_name.split()[-1]

    # FanGraphs 데이터에도 악센트 제거해서 매칭
    fg_data_copy = fg_data.copy()
    fg_data_copy['CleanName'] = fg_data_copy['Name'].apply(remove_accents)

    # 성(last name)으로 먼저 매칭
    matches = fg_data_copy[fg_data_copy['CleanName'].str.contains(last_name, case=False, na=False)]

    if len(matches) == 0:
        return None
    elif len(matches) == 1:
        return matches.iloc[0]
    else:
        # 여러 매치 - 전체 이름으로 정확히 매칭
        exact = matches[matches['CleanName'].str.lower() == clean_name.lower()]
        if not exact.empty:
            return exact.iloc[0]

        # 정확한 매칭 실패 - 이름이 가장 유사한 것 선택
        for _, row in matches.iterrows():
            if clean_name.lower() in row['CleanName'].lower() or row['CleanName'].lower() in clean_name.lower():
                return row

        return matches.iloc[0]


def enrich_batter(batter, fg_batters):
    """타자에 FanGraphs 지표 추가"""
    fg_player = find_player_in_fangraphs(batter['name'], fg_batters)

    if fg_player is None:
        batter['fangraphs_stats'] = {}
        return

    # 주요 고급 지표 추가
    batter['fangraphs_stats'] = {
        'WAR': float(fg_player.get('WAR', 0)),
        'wRC+': int(fg_player.get('wRC+', 100)),
        'wOBA': float(fg_player.get('wOBA', 0.320)),
        'ISO': float(fg_player.get('ISO', 0.150)),
        'BABIP': float(fg_player.get('BABIP', 0.300)),
        'K%': float(fg_player.get('K%', 20.0)),
        'BB%': float(fg_player.get('BB%', 8.0)),
        'wRC': float(fg_player.get('wRC', 0)),
        'Off': float(fg_player.get('Off', 0)),  # Offensive runs above average
        'Def': float(fg_player.get('Def', 0)),  # Defensive runs above average
        'BsR': float(fg_player.get('BsR', 0))   # Base running runs above average
    }


def enrich_pitcher(pitcher, fg_pitchers):
    """투수에 FanGraphs 지표 추가"""
    fg_player = find_player_in_fangraphs(pitcher['name'], fg_pitchers)

    if fg_player is None:
        pitcher['fangraphs_stats'] = {}
        return

    # 주요 고급 지표 추가
    pitcher['fangraphs_stats'] = {
        'WAR': float(fg_player.get('WAR', 0)),
        'FIP': float(fg_player.get('FIP', 4.00)),
        'xFIP': float(fg_player.get('xFIP', 4.00)),
        'SIERA': float(fg_player.get('SIERA', 4.00)),
        'K/9': float(fg_player.get('K/9', 8.0)),
        'BB/9': float(fg_player.get('BB/9', 3.0)),
        'K%': float(fg_player.get('K%', 20.0)),
        'BB%': float(fg_player.get('BB%', 8.0)),
        'K-BB%': float(fg_player.get('K-BB%', 12.0)),
        'WHIP': float(fg_player.get('WHIP', 1.30)),
        'BABIP': float(fg_player.get('BABIP', 0.300)),
        'LOB%': float(fg_player.get('LOB%', 72.0)),
        'GB%': float(fg_player.get('GB%', 45.0)),  # Ground ball %
        'HR/9': float(fg_player.get('HR/9', 1.0))
    }


def enrich_team_data(team_file, fg_batters, fg_pitchers):
    """팀 데이터에 FanGraphs 지표 추가"""
    with open(team_file, 'r', encoding='utf-8') as f:
        team_data = json.load(f)

    team_name = team_data['team_name']
    print(f"Enriching {team_name}...")

    matched_batters = 0
    for batter in team_data['batters']:
        enrich_batter(batter, fg_batters)
        if batter.get('fangraphs_stats'):
            matched_batters += 1

    matched_pitchers = 0
    for pitcher in team_data['pitchers']:
        enrich_pitcher(pitcher, fg_pitchers)
        if pitcher.get('fangraphs_stats'):
            matched_pitchers += 1

    print(f"  Matched {matched_batters}/{len(team_data['batters'])} batters, "
          f"{matched_pitchers}/{len(team_data['pitchers'])} pitchers")

    with open(team_file, 'w', encoding='utf-8') as f:
        json.dump(team_data, f, indent=2, ensure_ascii=False)


def main():
    print("\nEnriching data with FanGraphs advanced metrics\n")

    # FanGraphs 데이터 로드
    fg_batters, fg_pitchers = load_fangraphs_data(season=2025)

    # 각 팀 데이터 보강
    teams_dir = project_root / "data" / "mlb" / "nl_west" / "teams"

    for team_file in sorted(teams_dir.glob("*.json")):
        if team_file.name == "collection_summary.json":
            continue
        enrich_team_data(team_file, fg_batters, fg_pitchers)

    print("\nEnrichment complete!")


if __name__ == "__main__":
    main()
