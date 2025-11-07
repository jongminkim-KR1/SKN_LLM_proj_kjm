"""
LLM 기반 코치 전략 조언 시스템
"""


def _format_runners(runners):
    on_base = [str(b) for b in [1, 2, 3] if runners[b] is not None]
    return f"{', '.join(on_base)}루" if on_base else "없음"


def _get_score_situation(game_state):
    return f"원정 {game_state['away_score']} - {game_state['home_score']} 홈"


def _analyze_situation(game_state):
    situations = []
    runners = game_state['runners']

    if runners[2] or runners[3]:
        situations.append("득점권")
    if runners[1] and runners[2] and runners[3]:
        situations.append("만루")

    if game_state['inning'] >= 7:
        score_diff = abs(game_state['home_score'] - game_state['away_score'])
        if score_diff <= 1:
            situations.append("초접전")
        elif score_diff <= 2:
            situations.append("접전")

    if game_state.get('pitcher_fatigue', 0) >= 80:
        situations.append("투수 피로")

    return ", ".join(situations) if situations else "일반 상황"


def _assess_pitcher_condition(game_state):
    fatigue = game_state.get('pitcher_fatigue', 0)
    pitches = game_state.get('pitcher_pitches', 0)

    if fatigue >= 90 or pitches >= 110:
        return "매우 지침 (교체 필요)"
    elif fatigue >= 80 or pitches >= 100:
        return "지침 (교체 고려)"
    elif fatigue >= 60 or pitches >= 80:
        return "피로 누적"
    elif fatigue >= 40 or pitches >= 60:
        return "보통"
    return "양호"


def _get_player_stats(player):
    ratings = player['ratings_20_80']
    fg = player.get('fangraphs_stats', {})

    return {
        'ratings': ratings,
        'wrc_plus': fg.get('wRC+', 100),
        'iso': fg.get('ISO', 0.150),
        'k_pct': fg.get('K%', 0.23) * 100,
        'bb_pct': fg.get('BB%', 0.085) * 100,
        'war': fg.get('WAR', 0.0),
        'ops': fg.get('OPS', 0.750),
        'gb_pct': fg.get('GB%', 0.44) * 100,
        'fip': fg.get('FIP', 4.00),
        'era': fg.get('ERA', 4.00),
        'strike_pct': fg.get('Strike%', 0.65) * 100,
        'hr9': fg.get('HR/9', 1.2)
    }


def generate_pitching_coach_prompt(batter, pitcher, game_state):
    b = _get_player_stats(batter)
    p = _get_player_stats(pitcher)

    prompt = f"""당신은 MLB 투수코치입니다. 간결하게 분석하고 전략을 추천하세요.

[경기 상황] {game_state['inning']}회 {'말' if game_state['is_bottom'] else '초'}, {game_state['outs']}아웃, 주자: {_format_runners(game_state['runners'])}, 점수: {_get_score_situation(game_state)}

[타자: {batter['name']}]
능력: Contact {b['ratings']['contact']}, Power {b['ratings']['power']}, Eye {b['ratings']['eye']}, Overall {b['ratings']['overall']}
핵심 스탯: K% {b['k_pct']:.1f}%, ISO {b['iso']:.3f}, wRC+ {b['wrc_plus']}

[투수: {pitcher['name']}]
능력: Stuff {p['ratings']['stuff']}, Control {p['ratings']['control']}, Overall {p['ratings']['overall']}
핵심 스탯: K% {p['k_pct']:.1f}%, BB% {p['bb_pct']:.1f}%, FIP {p['fip']:.2f}
현재: {game_state.get('pitcher_pitches', 0)}구, 피로도 {game_state.get('pitcher_fatigue', 0):.0f}%

[전략 옵션]
1. 적극 승부 - 정면 승부, 삼진↑ 볼넷↓ 안타위험↑
2. 신중하게 - 존 가장자리, 볼넷↑ 안타↓ 삼진↓
3. 고의4구 - 이 타자 피하기

[요청] 위 데이터를 바탕으로:
1) 상황 분석 (1문장)
2) 추천 전략과 이유 (2-3문장)
형식: [추천] 번호. 전략명 / [이유] ...
"""
    return prompt


def generate_batting_coach_prompt(batter, pitcher, game_state):
    b = _get_player_stats(batter)
    p = _get_player_stats(pitcher)

    prompt = f"""당신은 MLB 타격코치입니다. 간결하게 분석하고 전략을 추천하세요.

[경기 상황] {game_state['inning']}회 {'말' if game_state['is_bottom'] else '초'}, {game_state['outs']}아웃, 주자: {_format_runners(game_state['runners'])}, 점수: {_get_score_situation(game_state)}

[타자: {batter['name']}]
능력: Contact {b['ratings']['contact']}, Power {b['ratings']['power']}, Eye {b['ratings']['eye']}, Overall {b['ratings']['overall']}
핵심 스탯: K% {b['k_pct']:.1f}%, ISO {b['iso']:.3f}, wRC+ {b['wrc_plus']}

[투수: {pitcher['name']}]
능력: Stuff {p['ratings']['stuff']}, Control {p['ratings']['control']}, Overall {p['ratings']['overall']}
핵심 스탯: K% {p['k_pct']:.1f}%, BB% {p['bb_pct']:.1f}%, FIP {p['fip']:.2f}
현재: {game_state.get('pitcher_pitches', 0)}구, 피로도 {game_state.get('pitcher_fatigue', 0):.0f}%

[전략 옵션]
1. 적극 스윙 - 초구부터 공격, 장타↑ 삼진↑ 볼넷↓
2. 컨택 중심 - 확실한 공만, 안타↑ 삼진↓ 장타↓
3. 볼넷 노림 - 볼 골라내기, 볼넷↑ 안타↓

[요청] 위 데이터를 바탕으로:
1) 상황 분석 (1문장)
2) 추천 전략과 이유 (2-3문장)
형식: [추천] 번호. 전략명 / [이유] ...
"""
    return prompt


def generate_strategy_advice_prompt(batter, pitcher, game_state):
    """하위 호환성을 위한 래퍼"""
    return generate_pitching_coach_prompt(batter, pitcher, game_state)
