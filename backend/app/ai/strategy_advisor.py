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

    prompt = f"""당신은 MLB 투수코치입니다. 상황과 데이터를 분석하여 위기 상황을 벗어날 수 있는 투구 전략을 추천하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[경기 상황]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• {game_state['inning']}회 {'말' if game_state['is_bottom'] else '초'}
• 아웃카운트: {game_state['outs']}아웃
• 주자: {_format_runners(game_state['runners'])}
• 점수: {_get_score_situation(game_state)}
• 상황: {_analyze_situation(game_state)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[타자 분석: {batter['name']}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ 20-80 스케일 능력치(50=평균, 60=올스타급):
  • Contact: {b['ratings']['contact']}/80 (컨택 능력)
  • Power: {b['ratings']['power']}/80 (장타력)
  • Eye: {b['ratings']['eye']}/80 (선구안)
  • Speed: {b['ratings']['speed']}/80 (주루)
  • Defense: {b['ratings']['defense']}/80 (수비)
  • Overall: {b['ratings']['overall']}/80 (종합)

▶ 2025시즌 주요 지표:
  • wRC+: {b['wrc_plus']} (100=평균, 높을수록 좋은 타자)
  • ISO: {b['iso']:.3f} (장타력, 평균 0.150)
  • K%: {b['k_pct']:.1f}% (삼진율, 높을수록 삼진 확률 높음)
  • BB%: {b['bb_pct']:.1f}% (볼넷율, 높을수록 볼넷으로 출루할 확률 높음)
  • WAR: {b['war']:.1f} (높을수록 좋은 타자, 2~3 WAR는 주전 선수 수준이며, 3~4는 좋은 선수, 4~5는 올스타, 5~6은 슈퍼스타, 6 이상은 MVP 수준)
  • OPS: {b['ops']:.3f} (높을수록 좋은 타자, 리그평균 0.715)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[아군 투수: {pitcher['name']}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ 20-80 스케일 능력치(50=평균, 60=올스타급):
  • Stuff: {p['ratings']['stuff']}/80 (구위, 삼진 능력)
  • Control: {p['ratings']['control']}/80 (제구력)
  • Movement: {p['ratings']['movement']}/80 (무브먼트)
  • Stamina: {p['ratings']['stamina']}/80 (스태미나)
  • Overall: {p['ratings']['overall']}/80 (종합)

▶ 2025시즌 주요 지표:
  • K%: {p['k_pct']:.1f}% (삼진율, 높을수록 투수가 삼진잡을 확률 높음)
  • BB%: {p['bb_pct']:.1f}% (볼넷율, 높을수록 투수가 불리, 높으면 제구가 안좋을 가능성 높음)
  • GB%: {p['gb_pct']:.1f}% (땅볼율)
  • FIP: {p['fip']:.2f} (리그 평균 4.16, 낮을수록 좋은 투수)
  • WAR: {p['war']:.1f} (높을수록 좋은 투수, 2~3 WAR는 주전 선수 수준이며, 3~4는 좋은 선수, 4~5는 올스타, 5~6은 슈퍼스타, 6 이상은 MVP 수준)
  • ERA: {p['era']:.2f} (낮을수록 좋은 투수, 4 이하면 준수한 투수, 3 이하면 우수한 투수, 2 이하면 최고의 투수 수준)
  • Strike%: {p['strike_pct']:.1f}% (높을수록 적극적인 승부를 즐기는 투수)
  • HR/9: {p['hr9']:.2f} (높을수록 홈런 허용할 확률 높음, 리그평균은 1.18)

▶ 현재 상태:
  • 투구수: {game_state.get('pitcher_pitches', 0)}구
  • 피로도: {game_state.get('pitcher_fatigue', 0):.0f}%
  • 상태: {_assess_pitcher_condition(game_state)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[전략 선택지]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 적극 승부
   - 스트라이크 존 공략, 정면 승부
   - 효과: 볼넷↓ 삼진↑ 안타/홈런 위험↑
   - 적합: 타자 K% 높음, 투수 Stuff 좋음, 여유 있는 상황

2. 신중하게
   - 어려운 코스, 존 가장자리 공략
   - 효과: 볼넷↑ 안타 위험↓ 삼진↓
   - 적합: 위험한 타자, 득점권 상황, 실점 불가 상황

3. 고의4구
   - 이 타자를 피하고 다음 타자와 승부
   - 효과: 주자 진루, 더블플레이 기회
   - 적합: 최상위 타자, 1루 비었을 때, 다음 타자가 약할 때

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[요청사항]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
다음 순서로 논리적으로 분석하여 추천하세요:

1. 상황 분석
   - 점수 차이와 이닝 (유리한지, 불리한지)
   - 주자 상황 (득점권인지, 만루인지)
   - 아웃카운트 (여유가 있는지, 위험한지)
   → 결론: 공격적으로 가야 하는지, 신중해야 하는지

2. 타자 분석
   - 강점: 어떤 능력이 뛰어난가? (구체적 수치)
   - 약점: 어떤 능력이 부족한가? (구체적 수치)
   → 결론: 어떤 방식으로 공략 가능한가?

3. 투수 분석
   - 강점: 어떤 능력으로 타자를 제압할 수 있는가?
   - 약점: 어떤 부분을 조심해야 하는가?
   - 현재 상태: 피로도와 투구수
   → 결론: 어떤 전략이 가장 효과적인가?

4. 최종 추천
   [추천 전략] 번호. 전략명
   [선택 이유] 위 분석을 바탕으로 한 명확한 이유 (2-3문장)
   [주의사항] 이 전략의 리스크
"""
    return prompt


def generate_batting_coach_prompt(batter, pitcher, game_state):
    b = _get_player_stats(batter)
    p = _get_player_stats(pitcher)

    prompt = f"""당신은 MLB 타격코치입니다. 상황과 데이터를 분석하여 우리팀의 득점을 위한 타격 전략을 추천하세요.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[경기 상황]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• {game_state['inning']}회 {'말' if game_state['is_bottom'] else '초'}
• 아웃카운트: {game_state['outs']}아웃
• 주자: {_format_runners(game_state['runners'])}
• 점수: {_get_score_situation(game_state)}
• 상황: {_analyze_situation(game_state)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[아군 타자: {batter['name']}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ 20-80 스케일 능력치:
  • Contact: {b['ratings']['contact']}/80 (컨택 능력)
  • Power: {b['ratings']['power']}/80 (장타력)
  • Eye: {b['ratings']['eye']}/80 (선구안)
  • Overall: {b['ratings']['overall']}/80 (종합)

▶ 2025시즌 주요 지표:
  • wRC+: {b['wrc_plus']} (100=평균, 높을수록 좋은 타자)
  • ISO: {b['iso']:.3f} (장타력, 평균 0.150)
  • K%: {b['k_pct']:.1f}% (삼진율, 높을수록 삼진 확률 높음)
  • BB%: {b['bb_pct']:.1f}% (볼넷율, 높을수록 볼넷으로 출루할 확률 높음)
  • WAR: {b['war']:.1f} (높을수록 좋은 타자, 2~3 WAR는 주전 선수 수준이며, 3~4는 좋은 선수, 4~5는 올스타, 5~6은 슈퍼스타, 6 이상은 MVP 수준)
  • OPS: {b['ops']:.3f} (높을수록 좋은 타자, 리그평균 0.715)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[상대 투수: {pitcher['name']}]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
▶ 20-80 스케일 능력치:
  • Stuff: {p['ratings']['stuff']}/80 (구위, 삼진 능력)
  • Control: {p['ratings']['control']}/80 (제구력)
  • Overall: {p['ratings']['overall']}/80 (종합)

▶ 2025시즌 주요 지표:
  • K%: {p['k_pct']:.1f}% (삼진율, 높을수록 투수가 삼진잡을 확률 높음)
  • BB%: {p['bb_pct']:.1f}% (볼넷율, 높을수록 투수가 불리, 높으면 제구가 안좋을 가능성 높음)
  • GB%: {p['gb_pct']:.1f}% (땅볼율)
  • FIP: {p['fip']:.2f} (리그 평균 4.16, 낮을수록 좋은 투수)
  • WAR: {p['war']:.1f} (높을수록 좋은 투수, 2~3 WAR는 주전 선수 수준이며, 3~4는 좋은 선수, 4~5는 올스타, 5~6은 슈퍼스타, 6 이상은 MVP 수준)
  • ERA: {p['era']:.2f} (낮을수록 좋은 투수, 4 이하면 준수한 투수, 3 이하면 우수한 투수, 2 이하면 최고의 투수 수준)
  • Strike%: {p['strike_pct']:.1f}% (높을수록 적극적인 승부를 즐기는 투수)
  • HR/9: {p['hr9']:.2f} (높을수록 홈런 허용할 확률 높음, 리그평균은 1.18)

▶ 투수 상태:
  • 투구수: {game_state.get('pitcher_pitches', 0)}구
  • 피로도: {game_state.get('pitcher_fatigue', 0):.0f}%
  • 상태: {_assess_pitcher_condition(game_state)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[타격 전략 선택지]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 적극 스윙
   - 초구부터 공격적으로 스윙
   - 효과: 안타/장타 기회↑, 삼진 위험↑, 볼넷↓
   - 적합: 타자 Power 높음, 투수 피로, 득점 필요

2. 컨택 중심
   - 확실히 맞출 수 있는 공만 스윙
   - 효과: 안타 확률↑, 삼진↓, 장타↓
   - 적합: 타자 Contact 높음, 주자 있음, 최소 1점 필요

3. 볼넷 노림
   - 스트라이크존 가장자리는 보내기
   - 효과: 볼넷↑, 안타/장타↓
   - 적합: 타자 Eye 높음, 투수 Control 나쁨, 다음 타자 강함

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[요청사항]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
다음 순서로 논리적으로 분석하여 추천하세요:

1. 상황 분석
   - 점수 차이와 이닝 (득점이 필요한지, 동점/역전인지)
   - 주자 상황 (주자가 있는지, 득점권인지)
   - 아웃카운트 (기회가 많은지, 적은지)
   → 결론: 장타를 노려야 하는지, 확실하게 출루해야 하는지

2. 아군 타자 분석
   - 강점: 어떤 능력이 뛰어난가? (구체적 수치)
   - 약점: 어떤 능력이 부족한가? (구체적 수치)
   → 결론: 어떤 방식의 타격이 가장 효과적인가?

3. 상대 투수 분석
   - 약점: 어떤 부분을 공략할 수 있는가?
   - 강점: 어떤 부분을 조심해야 하는가?
   - 현재 상태: 피로도와 투구수
   → 결론: 어떻게 접근하는 것이 유리한가?

4. 최종 추천
   [추천 전략] 번호. 전략명
   [선택 이유] 위 분석을 바탕으로 한 명확한 이유 (2-3문장)
   [주의사항] 이 전략의 리스크
"""
    return prompt


def generate_strategy_advice_prompt(batter, pitcher, game_state):
    """하위 호환성을 위한 래퍼"""
    return generate_pitching_coach_prompt(batter, pitcher, game_state)
