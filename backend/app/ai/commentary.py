"""
실시간 해설 시스템
"""
import random


def generate_commentary(outcome, batter, pitcher, game_state, runs_scored=0):
    is_clutch = game_state.get('runners_in_scoring_position', False)
    inning = game_state.get('inning', 1)
    outs = game_state.get('outs', 0)
    score_diff = abs(game_state.get('home_score', 0) - game_state.get('away_score', 0))

    commentaries = []
    batter_name = batter['name']
    pitcher_name = pitcher['name']

    if outcome == 'homerun':
        commentaries.append(f"{batter_name}의 시원한 홈런!")
        if is_clutch:
            commentaries.append(f"{batter_name}, 득점권에서 대형 홈런!")
        if runs_scored >= 3:
            commentaries.append(f"{batter_name}의 한 방으로 {runs_scored}점! 경기가 뒤집힙니다!")
    elif outcome in ['single', 'double', 'triple']:
        hit_type = {'single': '안타', 'double': '2루타', 'triple': '3루타'}[outcome]
        commentaries.append(f"{batter_name}, 깔끔한 {hit_type}!")
        if is_clutch and runs_scored > 0:
            commentaries.append(f"{batter_name}의 적시타! {runs_scored}점 추가!")
    elif outcome == 'strikeout':
        commentaries.append(f"{pitcher_name}, {batter_name}를 삼진으로 잡아냅니다.")
        if is_clutch and outs >= 2:
            commentaries.append(f"{pitcher_name}, 위기를 벗어났습니다!")
    elif outcome in ['groundout', 'flyout']:
        if outs >= 2 and is_clutch:
            commentaries.append(f"{pitcher_name}, 중요한 아웃!")
        else:
            commentaries.append(f"{batter_name}, 아웃!")
    elif outcome == 'walk':
        commentaries.append(f"{batter_name}, 볼넷으로 출루.")

    if inning >= 8 and score_diff <= 1 and commentaries:
        commentaries[0] += " 긴박한 순간입니다!"

    return random.choice(commentaries) if commentaries else None
