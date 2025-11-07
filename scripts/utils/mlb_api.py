"""
MLB API 헬퍼 함수
"""
import requests
from typing import Dict, List, Optional
from .constants import MLB_API_BASE_URL, MLB_SEASON


class MLBAPIClient:
    """MLB Stats API 클라이언트"""

    def __init__(self, base_url: str = MLB_API_BASE_URL, season: int = MLB_SEASON):
        self.base_url = base_url
        self.season = season

    def get_team_roster(self, team_id: int) -> List[Dict]:
        """
        팀 로스터 가져오기

        Args:
            team_id: MLB 팀 ID

        Returns:
            선수 리스트
        """
        url = f"{self.base_url}/teams/{team_id}/roster"
        params = {
            "rosterType": "active",
            "season": self.season
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            roster = []
            for player in data.get('roster', []):
                roster.append({
                    "id": player['person']['id'],
                    "name": player['person']['fullName'],
                    "position": player['position']['abbreviation'],
                    "jerseyNumber": player.get('jerseyNumber', 'N/A')
                })

            return roster
        except Exception as e:
            print(f"Error fetching roster for team {team_id}: {e}")
            return []

    def get_player_info(self, player_id: int) -> Optional[Dict]:
        """
        선수 기본 정보 가져오기

        Args:
            player_id: MLB 선수 ID

        Returns:
            선수 기본 정보
        """
        url = f"{self.base_url}/people/{player_id}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('people'):
                return None

            player = data['people'][0]
            return {
                "id": player_id,
                "name": player['fullName'],
                "position": player.get('primaryPosition', {}).get('abbreviation', 'N/A'),
                "bat_side": player.get('batSide', {}).get('code', 'R'),
                "pitch_hand": player.get('pitchHand', {}).get('code', 'R'),
                "birth_date": player.get('birthDate', ''),
                "height": player.get('height', ''),
                "weight": player.get('weight', ''),
                "is_pitcher": player.get('primaryPosition', {}).get('abbreviation') == 'P'
            }
        except Exception as e:
            print(f"Error fetching player info for {player_id}: {e}")
            return None

    def get_player_stats(self, player_id: int, is_pitcher: bool = False) -> Optional[Dict]:
        """
        선수 시즌 스탯 가져오기

        Args:
            player_id: MLB 선수 ID
            is_pitcher: 투수 여부

        Returns:
            시즌 스탯
        """
        url = f"{self.base_url}/people/{player_id}/stats"
        stat_group = 'pitching' if is_pitcher else 'hitting'

        params = {
            'stats': 'season',
            'season': self.season,
            'group': stat_group
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if not data.get('stats') or len(data['stats']) == 0:
                return None

            splits = data['stats'][0].get('splits', [])
            if not splits:
                return None

            return splits[0]['stat']
        except Exception as e:
            print(f"Error fetching stats for player {player_id}: {e}")
            return None

    def get_complete_player_data(self, player_id: int) -> Optional[Dict]:
        """
        선수의 모든 정보 한번에 가져오기

        Args:
            player_id: MLB 선수 ID

        Returns:
            완전한 선수 데이터
        """
        # 기본 정보
        player_info = self.get_player_info(player_id)
        if not player_info:
            return None

        # 스탯
        stats = self.get_player_stats(player_id, player_info['is_pitcher'])

        return {
            **player_info,
            "stats_2024": stats if stats else {}
        }
