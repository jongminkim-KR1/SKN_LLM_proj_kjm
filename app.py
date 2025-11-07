"""
MLB 매니저 시뮬레이터 - 야구 문자중계 스타일
"""
import streamlit as st
import json
import sys
import os
import random
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
load_dotenv(project_root / "backend" / ".env")

from backend.app.game_engine import GameState, AtBatSimulator
from backend.app.ai import OllamaClient, generate_strategy_advice_prompt, generate_batting_coach_prompt, generate_commentary

st.set_page_config(
    page_title="MLB 매니저 시뮬레이터",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');

    .scoreboard {
        background: #1a1a1a;
        border: 3px solid #ffcc00;
        padding: 0;
        margin-bottom: 1rem;
        font-family: 'IBM Plex Mono', monospace;
        position: sticky;
        top: 0;
        z-index: 100;
    }
    .team-score {
        padding: 0.8rem;
        border-bottom: 1px solid #333;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .team-name {
        color: #fff;
        font-size: 1.1rem;
        font-weight: 600;
    }
    .score-digits {
        font-size: 2rem;
        font-weight: 700;
        color: #00ff00;
        text-shadow: 0 0 10px #00ff00;
    }
    .game-info {
        background: #000;
        border: 2px solid #ffcc00;
        padding: 0.5rem;
        margin: 0.5rem 0;
        color: #00ff00;
        font-family: monospace;
        display: flex;
        justify-content: space-around;
    }
    .matchup-box {
        background: #1a1a2e;
        border: 2px solid #ffcc00;
        padding: 1rem;
        margin: 1rem 0;
    }
    .player-name {
        color: #ffcc00;
        font-size: 1.1rem;
        font-weight: 700;
    }
    .player-stats {
        color: #aaa;
        font-size: 0.9rem;
        margin-top: 0.3rem;
    }
    .play-log {
        background: #0a0a0a;
        border: 2px solid #333;
        padding: 0.5rem;
        max-height: 300px;
        overflow-y: auto;
        font-family: monospace;
    }
    .play-item {
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-left: 3px solid #333;
        color: #ccc;
        background: #111;
    }
    .play-item.hit {
        border-left-color: #00ff00;
        color: #00ff00;
    }
    .play-item.homerun {
        border-left-color: #ff0000;
        color: #ffcc00;
        font-weight: 700;
    }
    .commentary-box {
        background: #1a1a1a;
        border-left: 5px solid #ffcc00;
        padding: 0.8rem;
        margin: 1rem 0;
        color: #fff;
    }
    .chat-message {
        background: #2a2a2a;
        border-radius: 8px;
        padding: 0.8rem;
        margin: 0.5rem 0;
        border-left: 3px solid #555;
    }
    .chat-user {
        color: #ffcc00;
        font-weight: 600;
        font-size: 0.9rem;
        margin-bottom: 0.3rem;
    }
    .chat-text {
        color: #ddd;
        font-size: 0.95rem;
        line-height: 1.4;
    }
</style>
""", unsafe_allow_html=True)


class StreamlitMLBGame:
    def __init__(self):
        self.data_dir = project_root / "data" / "mlb" / "nl_west" / "teams"
        self.teams = {
            'Dodgers': 'dodgers',
            'Padres': 'padres',
            'Diamondbacks': 'diamondbacks',
            'Giants': 'giants',
            'Rockies': 'rockies'
        }

    def load_team(self, team_name):
        team_file = self.data_dir / f"{team_name}.json"
        with open(team_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def get_starters(self, team_data):
        pitchers = team_data['pitchers']
        starters = [p for p in pitchers if p.get('ratings_20_80', {}).get('stamina', 0) >= 55]
        return sorted(starters or pitchers, key=lambda p: p['ratings_20_80']['overall'], reverse=True)

    def get_bullpen(self, team_data):
        pitchers = team_data['pitchers']
        bullpen = [p for p in pitchers if p.get('ratings_20_80', {}).get('stamina', 0) < 55]
        return sorted(bullpen, key=lambda p: p['ratings_20_80']['overall'], reverse=True)


OUTCOME_KR = {
    'single': '안타', 'double': '2루타', 'triple': '3루타',
    'homerun': '홈런', 'walk': '볼넷', 'strikeout': '삼진',
    'groundout': '땅볼아웃', 'flyout': '뜬공아웃'
}

STRATEGY_MAP_BATTING = {
    "적극 스윙 (장타 확률↑, 삼진 확률↑)": "power_swing",
    "컨택 중심 (안타 확률↑, 장타 확률↓)": "contact_swing",
    "볼 고르기 (볼넷 확률↑, 안타 확률↓)": "patient",
    "조언 무시 (일반 타격)": None
}

STRATEGY_MAP_PITCHING = {
    "공격적 투구 (삼진 확률↑, 볼넷 확률↓, 장타 위험↑)": "aggressive",
    "신중한 투구 (볼넷 확률↑, 장타 확률↓, 삼진 확률↓)": "careful",
    "고의4구 (주자 진루)": "intentional_walk",
    "조언 무시 (일반 투구)": None
}

STRATEGY_KR = {
    'power_swing': '[적극 스윙]',
    'contact_swing': '[컨택 중심]',
    'patient': '[볼 고르기]',
    'aggressive': '[공격적 투구]',
    'careful': '[신중한 투구]',
    'intentional_walk': '[고의4구]'
}


def generate_fan_chat(outcome, batter_name, score_diff, inning, is_bottom):
    outcome_text = OUTCOME_KR.get(outcome, outcome)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return get_fallback_chat(outcome, outcome_text)

    try:
        client = OpenAI(api_key=api_key)
        situation = f"{inning}회 {'말' if is_bottom else '초'}, 점수차 {abs(score_diff)}점"
        mood = "우리팀 리드 중" if score_diff > 0 else "상대팀 리드 중" if score_diff < 0 else "동점"

        prompt = f"""
야구 경기 실시간 팬 채팅을 생성하세요.

**경기 상황:**
- {situation}
- {mood}
- 타자: {batter_name}
- 결과: {outcome_text}

**요구사항:**
1. 5-7명의 다양한 팬들이 실시간으로 반응하는 채팅을 생성
2. 각 메시지는 한글로 10-20자 이내로 자연스럽게
3. 다양한 감정과 반응 포함:
   - 홈런/장타: "와!!", "미쳤다", "개쩐다", "ㄹㅇ 레전드", "이걸 넘기네", "투수 뭐하냐..."
   - 안타: "좋아!", "오케이", "나이스", "잘한다", "점수 좀 내보자", "투수 좀 바꿔라 뭐하냐"
   - 삼진/아웃: "아...", "ㅠㅠ", "에휴", "답답하네", "오늘 공 좋다", "좀 쳐라;;", "저게 투수냐"
   - 긴박한 상황: "제발", "가자가자", "우리팀 화이팅", "제발!!!!!!"
4. 각 팬마다 고유한 닉네임 사용 (예: 야구덕후, 1번팬, 치킨먹는중, 퇴근중, 직관러, 학생, 아재팬 등)
5. 이모티콘이나 ㅋㅋ, ㅠㅠ, !! 등 자연스러운 채팅체 사용

**JSON 형식으로만 반환 (설명 없이):**
{{"chats": [{{"user": "닉네임", "message": "채팅내용"}}, ...]}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        result = json.loads(result_text)
        return result.get('chats', [])
    except:
        return get_fallback_chat(outcome, outcome_text)


def get_fallback_chat(outcome, outcome_text):
    fallback = {
        'homerun': [
            {"user": "야구덕후", "message": "홈런이다!!!"},
            {"user": "직관러", "message": "미쳤다 진짜ㅋㅋㅋ"},
            {"user": "치킨먹는중", "message": "개쩐다!!"}
        ],
        'single': [
            {"user": "1번팬", "message": "좋아 안타!"},
            {"user": "학생", "message": "오케이~~"},
            {"user": "퇴근중", "message": "나이스"}
        ],
        'strikeout': [
            {"user": "아재팬", "message": "아... 삼진"},
            {"user": "직장인", "message": "답답하네ㅠㅠ"},
            {"user": "야구팬", "message": "에휴"}
        ],
        'walk': [
            {"user": "분석러", "message": "볼넷 괜찮음"},
            {"user": "응원단", "message": "출루 성공!"}
        ]
    }
    return fallback.get(outcome, [{"user": "야구팬", "message": f"{outcome_text}!"}])


def generate_mound_visit_initial(pitcher_name, catcher_name, situation, pitcher_stats, game_state):
    """OpenAI로 마운드 방문 초기 대화 생성 (투수+포수만, 감독은 사용자 입력)"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "dialogue": [
                {"speaker": "포수", "message": f"{pitcher_name}, 괜찮아? 구위가 좀 떨어진 것 같은데..."},
                {"speaker": "투수", "message": "괜찮습니다. 계속 가겠습니다."}
            ]
        }

    try:
        client = OpenAI(api_key=api_key)

        prompt = f"""
당신은 야구 경기에서 마운드 방문 상황의 대화를 생성하는 작가입니다.

**상황:**
- 투수: {pitcher_name}
- 포수: {catcher_name}
- 현재 상황: {situation}
- 투수 피로도: {pitcher_stats.get('fatigue', 0)}%
- 던진 공 개수: {pitcher_stats.get('pitches', 0)}개
- 실점한 점수: {pitcher_stats.get('runs_allowed', 0)}점
- 이닝: {game_state.get('inning', 1)}회 {'말' if game_state.get('is_bottom') else '초'}
- 아웃카운트: {game_state.get('outs', 0)}아웃
- 주자상황: {game_state.get('runners_desc', '주자 없음')}

**요구사항:**
1. 포수와 투수의 초기 대화만 생성 (2-3개)
2. 포수는 상황 설명 + 실질적 조언
3. 투수는 현재 컨디션과 의지 표현
4. 대화는 한국 프로야구 스타일로 존댓말/반말 섞어서
5. 감독의 판단을 기다리는 상황으로 마무리

**대화 예시:**
- 포수: "감독님, {pitcher_name} 슬라이더 구위가 떨어졌어요. 마지막 이닝 구속도 3km 빠졌습니다."
- 투수: "괜찮습니다! 아직 힘 남았어요. 한 타자만 더 상대하겠습니다."
- 포수: "피로도가 보이긴 해요. 감독님 판단 부탁드립니다."

**JSON 형식으로만 반환:**
{{
  "dialogue": [
    {{"speaker": "포수", "message": "대사"}},
    {{"speaker": "투수", "message": "대사"}},
    ...
  ]
}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=300
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        result = json.loads(result_text)
        return result
    except:
        return {
            "dialogue": [
                {"speaker": "포수", "message": f"감독님, {pitcher_name} 구위가 떨어졌어요."},
                {"speaker": "투수", "message": "괜찮습니다. 계속 가겠습니다."}
            ]
        }


def generate_player_response(user_message, pitcher_name, catcher_name, situation, dialogue_history):
    """사용자(감독) 입력에 대한 투수/포수 반응 생성"""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"speaker": "투수", "message": "알겠습니다, 감독님."}

    try:
        client = OpenAI(api_key=api_key)

        dialogue_context = "\n".join([f"{d['speaker']}: {d['message']}" for d in dialogue_history])

        prompt = f"""
야구 경기 마운드 방문 대화에서 감독의 말에 대한 선수들의 반응을 생성하세요.

**이전 대화:**
{dialogue_context}

**감독의 말:**
{user_message}

**상황:**
- 투수: {pitcher_name}
- 포수: {catcher_name}
- {situation}

**요구사항:**
1. 감독의 말에 대한 투수 또는 포수의 자연스러운 반응 1개 생성
2. 감독이 교체 결정하면 투수는 아쉬워하거나 수긍
3. 감독이 계속 가라고 하면 투수는 의욕적으로
4. 한국 프로야구 스타일 대화

**JSON 형식으로만 반환:**
{{"speaker": "투수/포수", "message": "대사"}}
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=150
        )

        result_text = response.choices[0].message.content.strip()
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        result = json.loads(result_text)
        return result
    except:
        return {"speaker": "투수", "message": "알겠습니다, 감독님."}


def check_mound_visit_trigger(game_state, pitcher_stats):
    """마운드 방문 이벤트 발생 조건 체크"""
    reasons = []

    # 1. 피로도 체크
    if pitcher_stats.get('fatigue', 0) >= 75:
        reasons.append("투수 피로도 높음")

    # 2. 연속 안타/실점
    if pitcher_stats.get('consecutive_hits', 0) >= 3:
        reasons.append("연속 안타 허용")

    # 3. 위기 상황 (주자 득점권 + 아웃카운트 적음)
    if game_state.runners_in_scoring_position and game_state.outs <= 1:
        reasons.append("득점권 위기 상황")

    # 4. 만루
    if all(game_state.runners[base] is not None for base in [1, 2, 3]):
        reasons.append("만루 위기")

    # 5. 경기 종반 리드 중 실점 위기
    if game_state.inning >= 7:
        score_diff = game_state.home_score - game_state.away_score
        if game_state.is_bottom and score_diff > 0 and game_state.runners_in_scoring_position:
            reasons.append("경기 종반 리드 수비 위기")
        elif not game_state.is_bottom and score_diff < 0 and game_state.runners_in_scoring_position:
            reasons.append("경기 종반 추격 상황")

    return reasons


def init_session():
    defaults = {
        'page': 'team_selection',
        'game_manager': StreamlitMLBGame(),
        'at_bat_sim': AtBatSimulator(),
        'llm': OllamaClient(),
        'play_log': [],
        'last_commentary': None,
        'fan_chats': [],
        'show_chat_popup': False,
        'show_mound_visit': False,
        'mound_visit_data': None,
        'pitcher_consecutive_hits': 0,
        'pitcher_runs_allowed': 0
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def team_selection_page():
    st.title("MLB 매니저 시뮬레이터")
    st.markdown("### 팀 선택")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 홈팀 (당신)")
        home_team = st.selectbox("홈팀 선택", list(st.session_state.game_manager.teams.keys()))
    with col2:
        st.markdown("#### 원정팀")
        away_options = [t for t in st.session_state.game_manager.teams.keys() if t != home_team]
        away_team = st.selectbox("원정팀 선택", away_options)

    if st.button("라인업 구성", type="primary", use_container_width=True):
        manager = st.session_state.game_manager
        st.session_state.home_team_name = home_team
        st.session_state.away_team_name = away_team
        st.session_state.home_team_data = manager.load_team(manager.teams[home_team])
        st.session_state.away_team_data = manager.load_team(manager.teams[away_team])
        st.session_state.page = 'lineup_setup'
        st.rerun()


def lineup_setup_page():
    st.title("라인업 구성")

    tab1, tab2 = st.tabs([f"{st.session_state.home_team_name} (홈)", f"{st.session_state.away_team_name} (원정)"])
    with tab1:
        setup_team_lineup(st.session_state.home_team_data, "home")
    with tab2:
        setup_team_lineup(st.session_state.away_team_data, "away")

    if st.button("경기 시작", type="primary", use_container_width=True):
        start_game()


def setup_team_lineup(team_data, team_key):
    st.markdown("### 타순")

    # 모든 타자 표시 (필터링 없음)
    all_batters = sorted(team_data['batters'], key=lambda b: b['ratings_20_80']['overall'], reverse=True)

    if f'{team_key}_lineup' not in st.session_state:
        st.session_state[f'{team_key}_lineup'] = all_batters[:9]

    batter_map = {f"{b['name']} ({b['position']}) - OVR:{b['ratings_20_80']['overall']}": b for b in all_batters}
    new_lineup = []

    for order in range(1, 10):
        already_selected = [f"{b['name']} ({b['position']}) - OVR:{b['ratings_20_80']['overall']}" for b in new_lineup]
        available = [name for name in batter_map.keys() if name not in already_selected]

        col1, col2 = st.columns([1, 9])
        with col1:
            st.markdown(f"**{order}번**")
        with col2:
            selected = st.selectbox(
                f"{order}번", available,
                key=f'{team_key}_batter_{order}',
                label_visibility="collapsed"
            )
            new_lineup.append(batter_map[selected])

    st.session_state[f'{team_key}_lineup'] = new_lineup

    st.markdown("### 선발 투수")
    # 모든 투수 표시 (필터링 없음)
    all_pitchers = sorted(team_data['pitchers'], key=lambda p: p['ratings_20_80']['overall'], reverse=True)
    pitcher_options = {f"{p['name']} - OVR:{p['ratings_20_80']['overall']}": p for p in all_pitchers}
    selected_pitcher = st.selectbox("선발 투수", list(pitcher_options.keys()), key=f'{team_key}_pitcher_select')
    st.session_state[f'{team_key}_pitcher'] = pitcher_options[selected_pitcher]


def start_game():
    st.session_state.game_state = GameState(st.session_state.away_team_name, st.session_state.home_team_name, start_inning=7)

    # 모든 투수를 불펜으로 (선발 제외)
    home_pitchers = st.session_state.home_team_data['pitchers']
    away_pitchers = st.session_state.away_team_data['pitchers']

    st.session_state.home_bullpen = [p for p in home_pitchers if p['name'] != st.session_state.home_pitcher['name']]
    st.session_state.away_bullpen = [p for p in away_pitchers if p['name'] != st.session_state.away_pitcher['name']]

    st.session_state.home_current_pitcher = st.session_state.home_pitcher
    st.session_state.away_current_pitcher = st.session_state.away_pitcher
    st.session_state.home_batter_idx = 0
    st.session_state.away_batter_idx = 0
    st.session_state.page = 'game'
    st.session_state.play_log = []
    st.rerun()


def game_page():
    show_sidebar()
    game = st.session_state.game_state

    if game.inning > 9:
        show_game_over()
        return

    show_scoreboard()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        if game.is_bottom:
            lineup = st.session_state.home_lineup
            batter_idx = st.session_state.home_batter_idx
            pitcher = st.session_state.away_current_pitcher
        else:
            lineup = st.session_state.away_lineup
            batter_idx = st.session_state.away_batter_idx
            pitcher = st.session_state.home_current_pitcher

        batter = lineup[batter_idx]
        show_matchup(batter, pitcher, game)

        col_btn1, col_btn2, col_btn3 = st.columns(3)
        with col_btn1:
            if st.button("AI 코치 조언 받기", use_container_width=True):
                st.session_state.show_strategy_selection = True
                st.rerun()
        with col_btn2:
            if st.button("🗣️ 마운드 방문", use_container_width=True):
                # 수동으로 마운드 방문 트리거
                pitcher_stats = {
                    'fatigue': game.pitcher_fatigue,
                    'pitches': game.pitcher_pitches,
                    'consecutive_hits': st.session_state.get('pitcher_consecutive_hits', 0),
                    'runs_allowed': st.session_state.get('pitcher_runs_allowed', 0)
                }
                catcher_name = "Catcher"
                runners_on = [str(b) for b in [1, 2, 3] if game.runners[b] is not None]
                runners_desc = f"{', '.join(runners_on)}루 주자" if runners_on else "주자 없음"

                initial_dialogue = generate_mound_visit_initial(
                    pitcher['name'],
                    catcher_name,
                    "감독 요청",
                    pitcher_stats,
                    {
                        'inning': game.inning,
                        'is_bottom': game.is_bottom,
                        'outs': game.outs,
                        'runners_desc': runners_desc
                    }
                )

                st.session_state.mound_visit_data = {
                    'pitcher_name': pitcher['name'],
                    'catcher_name': catcher_name,
                    'situation': "감독 요청",
                    'reason': "감독 요청",
                    'dialogue': initial_dialogue.get('dialogue', [])
                }
                st.session_state.show_mound_visit = True
                st.rerun()
        with col_btn3:
            if st.button("투수 교체", use_container_width=True):
                st.session_state.show_pitcher_change = True
                st.rerun()

        if st.session_state.get('show_strategy_selection', False):
            show_strategy_selection(batter, pitcher, game, batter_idx)
        elif st.session_state.get('show_pitcher_change', False):
            show_pitcher_change(game)
        else:
            if st.button("타석 진행 (전략 없음)", type="primary", use_container_width=True):
                simulate_at_bat(batter, pitcher, game, batter_idx, None)
                st.rerun()

        if st.session_state.last_commentary:
            st.markdown(f'<div class="commentary-box">실시간 중계<br>{st.session_state.last_commentary}</div>', unsafe_allow_html=True)

    with col_right:
        show_play_log()
        st.markdown("---")
        if st.button("팬 채팅 보기", use_container_width=True):
            st.session_state.show_chat_popup = True
            st.rerun()

    if st.session_state.show_chat_popup:
        show_fan_chat_popup()

    if st.session_state.get('show_mound_visit', False):
        show_mound_visit_popup()


def show_strategy_selection(batter, pitcher, game, batter_idx):
    st.markdown("---")

    if 'current_advice' not in st.session_state:
        with st.spinner("AI 분석 중..."):
            if game.is_bottom:
                prompt = generate_batting_coach_prompt(batter, pitcher, game.get_state_dict())
                st.session_state.is_batting_turn = True
            else:
                prompt = generate_strategy_advice_prompt(batter, pitcher, game.get_state_dict())
                st.session_state.is_batting_turn = False
            st.session_state.current_advice = st.session_state.llm.generate(prompt)

    st.info(f"**AI 코치 조언**\n\n{st.session_state.current_advice}")
    st.markdown("#### 전략 선택")

    if st.session_state.is_batting_turn:
        strategy = st.radio("타격 전략을 선택하세요", list(STRATEGY_MAP_BATTING.keys()), key="strategy_choice")
        strategy_map = STRATEGY_MAP_BATTING
    else:
        strategy = st.radio("투구 전략을 선택하세요", list(STRATEGY_MAP_PITCHING.keys()), key="strategy_choice")
        strategy_map = STRATEGY_MAP_PITCHING

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("전략 실행", type="primary", use_container_width=True):
            simulate_at_bat(batter, pitcher, game, batter_idx, strategy_map[strategy])
            st.session_state.show_strategy_selection = False
            st.session_state.pop('current_advice', None)
            st.rerun()
    with col_btn2:
        if st.button("취소", use_container_width=True):
            st.session_state.show_strategy_selection = False
            st.session_state.pop('current_advice', None)
            st.rerun()


def show_pitcher_change(game):
    st.markdown("---")
    st.markdown("#### 투수 교체")

    if game.is_bottom:
        current_team = "원정"
        bullpen = st.session_state.away_bullpen
        current_pitcher_key = 'away_current_pitcher'
    else:
        current_team = "홈"
        bullpen = st.session_state.home_bullpen
        current_pitcher_key = 'home_current_pitcher'

    st.info(f"**현재 {current_team}팀 투수:** {st.session_state[current_pitcher_key]['name']}\n투구수: {game.pitcher_pitches} | 피로도: {game.pitcher_fatigue:.0f}%")

    if bullpen:
        pitcher_options = {f"{p['name']} - OVR:{p['ratings_20_80']['overall']} STF:{p['ratings_20_80']['stuff']} CTL:{p['ratings_20_80']['control']}": p for p in bullpen}
        selected = st.selectbox("교체할 투수 선택", list(pitcher_options.keys()), key="pitcher_change_select")

        col_change1, col_change2 = st.columns(2)
        with col_change1:
            if st.button("교체 확정", type="primary", use_container_width=True):
                new_pitcher = pitcher_options[selected]
                st.session_state[current_pitcher_key] = new_pitcher
                bullpen.remove(new_pitcher)
                game.pitcher_pitches = 0
                game.pitcher_fatigue = 0
                st.session_state.play_log.append(f"[투수 교체: {new_pitcher['name']}]")
                st.session_state.show_pitcher_change = False
                st.rerun()
        with col_change2:
            if st.button("취소", use_container_width=True):
                st.session_state.show_pitcher_change = False
                st.rerun()
    else:
        st.warning("교체 가능한 투수가 없습니다.")
        if st.button("닫기", use_container_width=True):
            st.session_state.show_pitcher_change = False
            st.rerun()


def show_fan_chat_popup():
    st.markdown("""
    <style>
    .chat-modal {
        background: #1a1a1a;
        border: 3px solid #ffcc00;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
    }
    .chat-modal-header {
        color: #ffcc00;
        font-size: 1.3rem;
        font-weight: 700;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #ffcc00;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="chat-modal">', unsafe_allow_html=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown('<div class="chat-modal-header">실시간 팬 채팅</div>', unsafe_allow_html=True)
    with col2:
        if st.button("닫기", key="close_chat", type="secondary"):
            st.session_state.show_chat_popup = False
            st.rerun()

    if st.session_state.fan_chats:
        for chat in reversed(st.session_state.fan_chats[-20:]):
            st.markdown(f'''
            <div class="chat-message">
                <div class="chat-user">{chat["user"]}</div>
                <div class="chat-text">{chat["message"]}</div>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("아직 채팅이 없습니다. 경기가 진행되면 팬들의 반응을 볼 수 있습니다!")

    st.markdown('</div>', unsafe_allow_html=True)


def show_mound_visit_popup():
    """마운드 방문 대화 팝업"""
    if not st.session_state.get('mound_visit_data'):
        return

    st.markdown("""
    <style>
    .mound-visit-modal {
        background: linear-gradient(135deg, #1a3a1a 0%, #2a1a1a 100%);
        border: 3px solid #00ff00;
        border-radius: 12px;
        padding: 2rem;
        margin: 1rem 0;
        box-shadow: 0 0 20px rgba(0,255,0,0.3);
    }
    .mound-visit-header {
        color: #00ff00;
        font-size: 1.5rem;
        font-weight: 700;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #00ff00;
        text-align: center;
    }
    .dialogue-box {
        background: rgba(0,0,0,0.5);
        border-left: 4px solid #ffcc00;
        padding: 1rem;
        margin: 0.8rem 0;
        border-radius: 6px;
    }
    .speaker-name {
        color: #ffcc00;
        font-weight: 700;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    .dialogue-text {
        color: #ffffff;
        font-size: 1rem;
        line-height: 1.6;
    }
    </style>
    """, unsafe_allow_html=True)

    data = st.session_state.mound_visit_data

    st.markdown('<div class="mound-visit-modal">', unsafe_allow_html=True)
    st.markdown(f'<div class="mound-visit-header">⚾ 마운드 방문 - {data["reason"]}</div>', unsafe_allow_html=True)

    # 이전 대화 표시
    for dialogue in data.get('dialogue', []):
        st.markdown(f'''
        <div class="dialogue-box">
            <div class="speaker-name">{dialogue["speaker"]}</div>
            <div class="dialogue-text">{dialogue["message"]}</div>
        </div>
        ''', unsafe_allow_html=True)

    # 사용자(감독) 입력
    st.markdown("---")
    col1, col2 = st.columns([4, 1])

    with col1:
        user_input = st.text_input("💬 감독의 말:", key="manager_input", placeholder="투수에게 무엇을 말하시겠습니까?")

    with col2:
        st.write("")
        st.write("")
        if st.button("전송", key="send_manager_msg", type="primary"):
            if user_input:
                # 감독 대사 추가
                data['dialogue'].append({"speaker": "감독 (나)", "message": user_input})

                # AI 응답 생성
                response = generate_player_response(
                    user_input,
                    data['pitcher_name'],
                    data['catcher_name'],
                    data['situation'],
                    data['dialogue']
                )
                data['dialogue'].append(response)

                st.session_state.mound_visit_data = data
                st.rerun()

    # 대화 종료 버튼
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🔄 투수 교체", key="change_pitcher", type="secondary"):
            st.session_state.mound_visit_result = "교체"
            st.session_state.show_mound_visit = False
            st.session_state.mound_visit_data = None
            st.rerun()

    with col2:
        if st.button("✅ 계속 투구", key="continue_pitching", type="primary"):
            st.session_state.mound_visit_result = "계속"
            st.session_state.show_mound_visit = False
            st.session_state.mound_visit_data = None
            st.rerun()

    with col3:
        if st.button("❌ 닫기", key="close_mound_visit"):
            st.session_state.show_mound_visit = False
            st.session_state.mound_visit_data = None
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def show_scoreboard():
    game = st.session_state.game_state

    st.markdown(f'''
    <div class="scoreboard">
        <div class="team-score">
            <span class="team-name">원정 {st.session_state.away_team_name}</span>
            <span class="score-digits">{game.away_score:02d}</span>
        </div>
        <div class="team-score" style="background:#1a1a2e;">
            <span class="team-name">홈 {st.session_state.home_team_name}</span>
            <span class="score-digits">{game.home_score:02d}</span>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    runners = [r for i, r in [(1, "1루"), (2, "2루"), (3, "3루")] if game.runners[i]]

    st.markdown(f'''
    <div class="game-info">
        <span>{game.inning}회{'말' if game.is_bottom else '초'}</span>
        <span>{game.outs} 아웃</span>
        <span>주자: {', '.join(runners) if runners else '없음'}</span>
        <span>투구수: {game.pitcher_pitches}</span>
    </div>
    ''', unsafe_allow_html=True)


def show_matchup(batter, pitcher, game):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div style="color:#ffcc00;font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">타자</div>', unsafe_allow_html=True)

        # 선수 사진
        player_id = batter.get('id')
        if player_id:
            img_url = f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{player_id}/headshot/67/current"
            st.image(img_url, width=150)

        st.markdown(f'<div class="player-name">{batter["name"]} ({batter["position"]})</div>', unsafe_allow_html=True)

        # 실제 성적 표시
        if 'stats_2024' in batter:
            stats = batter['stats_2024']
            st.markdown(f"""
            **2025 시즌 성적**
            - AVG: {stats.get('avg', 'N/A')} | OPS: {stats.get('ops', 'N/A')}
            - HR: {stats.get('homeRuns', 0)} | RBI: {stats.get('rbi', 0)}
            - H: {stats.get('hits', 0)} | R: {stats.get('runs', 0)}
            """)

        # 20-80 등급
        r = batter['ratings_20_80']
        st.markdown(f"**능력치**: OVR {r['overall']} | CON {r['contact']} | PWR {r['power']} | EYE {r['eye']}")

    with col2:
        st.markdown('<div style="color:#ffcc00;font-size:1.1rem;font-weight:700;margin-bottom:0.5rem;">투수</div>', unsafe_allow_html=True)

        # 선수 사진
        player_id = pitcher.get('id')
        if player_id:
            img_url = f"https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/{player_id}/headshot/67/current"
            st.image(img_url, width=150)

        st.markdown(f'<div class="player-name">{pitcher["name"]}</div>', unsafe_allow_html=True)

        # 실제 성적 표시
        if 'stats_2024' in pitcher:
            stats = pitcher['stats_2024']
            st.markdown(f"""
            **2025 시즌 성적**
            - ERA: {stats.get('era', 'N/A')} | WHIP: {stats.get('whip', 'N/A')}
            - W-L: {stats.get('wins', 0)}-{stats.get('losses', 0)} | SO: {stats.get('strikeOuts', 0)}
            - IP: {stats.get('inningsPitched', 'N/A')}
            """)

        # 20-80 등급 및 현재 상태
        p = pitcher['ratings_20_80']
        st.markdown(f"**능력치**: OVR {p['overall']} | STF {p['stuff']} | CTL {p['control']}")
        st.markdown(f"**현재 상태**: 투구수 {game.pitcher_pitches} | 피로도 {game.pitcher_fatigue:.0f}%")


def show_play_log():
    st.markdown("### 실시간 중계")
    st.markdown('<div class="play-log">', unsafe_allow_html=True)

    logs = [log for log in st.session_state.play_log if log.startswith('[')][-5:]

    if logs:
        for log in reversed(logs):
            css = "play-item homerun" if '홈런' in log else "play-item hit" if any(w in log for w in ['안타', '2루타', '3루타']) else "play-item"
            st.markdown(f'<div class="{css}">{log}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="play-item">경기를 시작하세요</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def simulate_at_bat(batter, pitcher, game, batter_idx, strategy):
    outcome, _ = st.session_state.at_bat_sim.simulate(batter, pitcher, game.get_state_dict(), strategy)
    runs = process_outcome(outcome, batter, game)
    game.pitcher_pitches += random.randint(4, 6)

    if strategy:
        st.session_state.play_log.append(f"{STRATEGY_KR.get(strategy, '')} 전략 적용")

    result = OUTCOME_KR.get(outcome, outcome)
    log = f"[{batter['name']}] {result}" + (f" ({runs}점)" if runs > 0 else "")
    st.session_state.play_log.append(log)

    commentary = generate_commentary(outcome, batter, pitcher, game.get_state_dict(), runs)
    st.session_state.last_commentary = commentary

    score_diff = game.home_score - game.away_score
    fan_reactions = generate_fan_chat(outcome, batter['name'], score_diff, game.inning, game.is_bottom)
    st.session_state.fan_chats.extend(fan_reactions)

    if game.is_bottom:
        st.session_state.home_batter_idx = (batter_idx + 1) % 9
    else:
        st.session_state.away_batter_idx = (batter_idx + 1) % 9

    # 투수 통계 업데이트
    if outcome in ['single', 'double', 'triple', 'homerun']:
        st.session_state.pitcher_consecutive_hits += 1
    else:
        st.session_state.pitcher_consecutive_hits = 0

    if runs > 0:
        st.session_state.pitcher_runs_allowed += runs

    # 마운드 방문 트리거 체크 (3아웃 전에만)
    if game.outs < 3:
        pitcher_stats = {
            'fatigue': game.pitcher_fatigue,
            'pitches': game.pitcher_pitches,
            'consecutive_hits': st.session_state.pitcher_consecutive_hits,
            'runs_allowed': st.session_state.pitcher_runs_allowed
        }

        reasons = check_mound_visit_trigger(game, pitcher_stats)

        if reasons:
            # 포수 정보 가져오기
            if game.is_bottom:
                # 홈팀 공격 = 원정팀 수비
                catcher_name = "Catcher"  # 실제로는 라인업에서 가져와야 함
            else:
                # 원정팀 공격 = 홈팀 수비
                catcher_name = "Catcher"

            # 주자 상황 텍스트
            runners_on = [str(b) for b in [1, 2, 3] if game.runners[b] is not None]
            runners_desc = f"{', '.join(runners_on)}루 주자" if runners_on else "주자 없음"

            # 마운드 방문 대화 생성
            situation = ", ".join(reasons)
            initial_dialogue = generate_mound_visit_initial(
                pitcher['name'],
                catcher_name,
                situation,
                pitcher_stats,
                {
                    'inning': game.inning,
                    'is_bottom': game.is_bottom,
                    'outs': game.outs,
                    'runners_desc': runners_desc
                }
            )

            # 세션 상태에 저장
            st.session_state.mound_visit_data = {
                'pitcher_name': pitcher['name'],
                'catcher_name': catcher_name,
                'situation': situation,
                'reason': reasons[0],  # 주요 이유 1개만 표시
                'dialogue': initial_dialogue.get('dialogue', [])
            }
            st.session_state.show_mound_visit = True

    if game.outs >= 3:
        ended_inning = game.inning
        ended_half = '말' if game.is_bottom else '초'
        game.end_half_inning()
        st.session_state.play_log.append(f"[{ended_inning}회 {ended_half} 종료]")
        # 이닝 종료시 투수 통계 리셋
        st.session_state.pitcher_consecutive_hits = 0


def process_outcome(outcome, batter, game):
    runs_scored = 0

    if outcome == 'single':
        runs_scored = game.advance_runners(1)
        game.add_runner(1, batter['name'])
    elif outcome == 'double':
        runs_scored = game.advance_runners(2)
        game.add_runner(2, batter['name'])
    elif outcome == 'triple':
        runs_scored = game.advance_runners(3)
        game.add_runner(3, batter['name'])
    elif outcome == 'homerun':
        runs_scored = game.advance_runners(4) + 1
        game.clear_bases()
    elif outcome == 'walk':
        if game.runners[1]:
            if game.runners[2]:
                if game.runners[3]:
                    runs_scored = 1
                game.runners[3] = game.runners[2]
            game.runners[2] = game.runners[1]
        game.runners[1] = batter['name']
    elif outcome in ['strikeout', 'groundout', 'flyout']:
        game.record_out()
        if outcome == 'flyout' and game.outs < 3 and game.runners[3]:
            runs_scored = 1
            game.runners[3] = None

    if runs_scored > 0:
        game.add_score(runs_scored)

    return runs_scored


def show_sidebar():
    st.sidebar.markdown("### 라인업")

    with st.sidebar.expander(f"{st.session_state.home_team_name} (홈)", expanded=True):
        st.markdown(f"**투수:** {st.session_state.home_current_pitcher['name']}")
        for i, b in enumerate(st.session_state.home_lineup, 1):
            marker = "▶" if i-1 == st.session_state.home_batter_idx else " "
            st.text(f"{marker} {i}. {b['name'][:15]}")

    with st.sidebar.expander(f"{st.session_state.away_team_name} (원정)"):
        st.markdown(f"**투수:** {st.session_state.away_current_pitcher['name']}")
        for i, b in enumerate(st.session_state.away_lineup, 1):
            marker = "▶" if i-1 == st.session_state.away_batter_idx else " "
            st.text(f"{marker} {i}. {b['name'][:15]}")


def show_game_over():
    game = st.session_state.game_state

    st.markdown("## 경기 종료")
    st.markdown(f"### 최종 스코어: {st.session_state.away_team_name} {game.away_score} - {game.home_score} {st.session_state.home_team_name}")

    if game.home_score > game.away_score:
        st.success(f"{st.session_state.home_team_name} 승리!")
    elif game.home_score < game.away_score:
        st.error(f"{st.session_state.away_team_name} 승리")
    else:
        st.info("무승부")

    if st.button("새 게임"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()


def main():
    init_session()

    page_map = {
        'team_selection': team_selection_page,
        'lineup_setup': lineup_setup_page,
        'game': game_page
    }

    page_map[st.session_state.page]()


if __name__ == "__main__":
    main()
