"""
MLB NL West 팀 데이터 수집 스크립트
"""
import json
import time
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from scripts.utils.mlb_api import MLBAPIClient
from scripts.utils.constants import NL_WEST_TEAMS


def collect_team_data(team_id: int, team_info: dict, api_client: MLBAPIClient) -> dict:
    """특정 팀의 전체 데이터 수집"""
    print(f"\nCollecting {team_info['name']}...")

    roster = api_client.get_team_roster(team_id)
    print(f"Found {len(roster)} players")

    pitchers = []
    batters = []
    errors = []

    for idx, player in enumerate(roster, 1):
        player_id = player['id']
        player_name = player['name']

        print(f"[{idx}/{len(roster)}] {player_name}...", end=" ")

        try:
            player_data = api_client.get_complete_player_data(player_id)

            if not player_data:
                print("Failed")
                errors.append(player_name)
                continue

            player_data['team'] = team_info['name']
            player_data['team_id'] = team_id
            player_data['team_short_name'] = team_info['short_name']

            if player_data['is_pitcher']:
                pitchers.append(player_data)
                print("P")
            else:
                batters.append(player_data)
                print("B")

            time.sleep(0.5)

        except Exception as e:
            print(f"Error: {e}")
            errors.append(player_name)
            continue

    print(f"Collected {len(pitchers)} pitchers, {len(batters)} batters")
    if errors:
        print(f"Failed: {', '.join(errors)}")

    return {
        "team_id": team_id,
        "team_name": team_info['name'],
        "short_name": team_info['short_name'],
        "stadium": team_info['stadium'],
        "pitchers": pitchers,
        "batters": batters,
        "total_players": len(pitchers) + len(batters),
        "collection_date": time.strftime("%Y-%m-%d %H:%M:%S")
    }


def save_team_data(team_data: dict, output_dir: Path):
    """팀 데이터를 JSON 파일로 저장"""
    output_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{team_data['short_name']}.json"
    filepath = output_dir / filename

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(team_data, f, indent=2, ensure_ascii=False)

    print(f"Saved to {filepath}")


def main():
    """메인 함수"""
    print("\nMLB NL West Data Collection - 2025 Season\n")

    api_client = MLBAPIClient()
    output_dir = project_root / "data" / "mlb" / "nl_west" / "teams"
    all_teams_data = []

    for team_id, team_info in NL_WEST_TEAMS.items():
        try:
            team_data = collect_team_data(team_id, team_info, api_client)
            save_team_data(team_data, output_dir)
            all_teams_data.append(team_data)
            time.sleep(2)
        except Exception as e:
            print(f"Failed to collect {team_info['name']}: {e}")
            continue

    summary = {
        "collection_date": time.strftime("%Y-%m-%d %H:%M:%S"),
        "season": 2025,
        "total_teams": len(all_teams_data),
        "teams": [
            {
                "name": team['team_name'],
                "pitchers": len(team['pitchers']),
                "batters": len(team['batters']),
                "total": team['total_players']
            }
            for team in all_teams_data
        ]
    }

    summary_path = output_dir / "collection_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\nComplete: {summary['total_teams']} teams, {sum(t['total'] for t in summary['teams'])} players")
    print(f"Saved to: {summary_path}")


if __name__ == "__main__":
    main()
