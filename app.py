import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import requests
import json
from datetime import datetime, timedelta

# -------------------------------------------------------------
# 1. 페이지 기본 설정 및 스타일
# -------------------------------------------------------------
st.set_page_config(
    page_title="자기계발 관심도 트렌드 대시보드",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# 2. 데이터 수집 함수 (API 연동 및 더미 데이터 생성)
# -------------------------------------------------------------
@st.cache_data
def fetch_naver_datalab(client_id, client_secret, start_date, end_date, keyword_groups):
    """네이버 데이터랩 검색어 트렌드 API 호출 함수"""
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
        "Content-Type": "application/json"
    }

    body = {
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "timeUnit": "date",
        "keywordGroups": keyword_groups
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(body))
        if response.status_code == 200:
            result = response.json()
            dfs = []
            for item in result.get("results", []):
                group_name = item["title"]
                df_item = pd.DataFrame(item["data"])
                df_item = df_item.rename(columns={"period": "date", "ratio": group_name})
                df_item["date"] = pd.to_datetime(df_item["date"])
                df_item.set_index("date", inplace=True)
                dfs.append(df_item)

            if dfs:
                merged_df = pd.concat(dfs, axis=1).fillna(0).reset_index()
                return merged_df
            return None
        else:
            st.error(f"API 오류: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"요청 중 예외 발생: {e}")
        return None

def generate_sample_data(start_date, end_date):
    """API 키가 없을 때 화면 확인을 위한 시뮬레이션 샘플 데이터"""
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df = pd.DataFrame({"date": dates})

    day_of_year = df["date"].dt.dayofyear

    workout_base = 30 + 60 * np.exp(-((day_of_year - 10) / 25) ** 2) + 20 * np.exp(-((day_of_year - 190) / 40) ** 2)
    lang_base = 35 + 50 * np.exp(-((day_of_year - 15) / 20) ** 2) + 35 * np.exp(-((day_of_year - 200) / 35) ** 2)
    read_base = 25 + 40 * np.exp(-((day_of_year - 20) / 30) ** 2) + 25 * np.exp(-((day_of_year - 90) / 30) ** 2)

    noise = np.random.normal(0, 3, len(df))
    df["운동"] = np.clip(workout_base + noise, 5, 100)
    df["어학"] = np.clip(lang_base + noise, 5, 100)
    df["독서/자격증"] = np.clip(read_base + noise, 5, 100)

    return df

# -------------------------------------------------------------
# 3. 사이드바 컨트롤 패널
# -------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 분석 설정")

    st.subheader("1. API 인증 정보")
    client_id = st.text_input("Naver Client ID", placeholder="미입력 시 샘플 데이터 작동", type="password")
    client_secret = st.text_input("Naver Client Secret", placeholder="미입력 시 샘플 데이터 작동", type="password")

    st.divider()

    st.subheader("2. 조회 기간 설정")
    default_start = datetime(2023, 1, 1)
    default_end = datetime(2025, 12, 31)
    date_range = st.date_input("조회 기간 (시작일과 종료일을 모두 선택하세요)", [default_start, default_end])

    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        st.warning("종료 날짜를 마저 선택해주세요.")
        st.stop()

    st.divider()

    st.subheader("3. 분석 카테고리 선택")
    categories = st.multiselect(
        "비교 대상",
        options=["운동", "어학", "독서/자격증"],
        default=["운동", "어학", "독서/자격증"]
    )

    refresh_button = st.button("데이터 조회 / 새로고침", use_container_width=True)

# -------------------------------------------------------------
# 4. 데이터 로드 로직
# -------------------------------------------------------------
keyword_groups_meta = [
    {"title": "운동", "keywords": ["헬스장", "홈트", "운동", "필라테스", "다이어트"]},
    {"title": "어학", "keywords": ["영어회화", "토익", "전화영어", "어학연수", "일본어"]},
    {"title": "독서/자격증", "keywords": ["독서", "자기계발서", "자격증", "기사시험", "컴활"]}
]

selected_groups = [g for g in keyword_groups_meta if g["title"] in categories]

df = None
is_sample = True

if client_id and client_secret and selected_groups:
    with st.spinner("네이버 데이터랩 API 통신 중..."):
        df = fetch_naver_datalab(client_id, client_secret, start_date, end_date, selected_groups)
    if df is not None:
        is_sample = False

if df is None:
    df = generate_sample_data(start_date, end_date)
    is_sample = True

# -------------------------------------------------------------
# 5. 메인 레이아웃 구성
# -------------------------------------------------------------
st.title("🎯 '작심삼일' 증명: 자기계발 관심도 시계열 분석")
st.markdown("""
매년 1월 새해 결심(운동·어학·독서)으로 급증하는 대중의 관심이 시간 경과에 따라 어떻게 변화하는지 네이버 검색 트렌드 데이터를 통해 추적합니다.
""")

if is_sample:
    st.info("💡 안내: 현재 시뮬레이션 샘플 데이터로 렌더링 중입니다. 사이드바에 Naver OpenAPI 키를 입력하면 실시간 데이터로 전환됩니다.")

if len(categories) == 0:
    st.warning("⚠️ 사이드바에서 비교할 카테고리를 최소 1개 이상 선택해 주세요.")
elif df is not None and not df.empty:
    target_col = categories[0]

    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year

    jan_avg = df[df["month"] == 1][target_col].mean()
    feb_mar_avg = df[df["month"].isin([2, 3])][target_col].mean()
    drop_rate = ((feb_mar_avg - jan_avg) / jan_avg) * 100 if jan_avg > 0 else 0

    monthly_avg = df.groupby("month")[target_col].mean()
    lowest_month = monthly_avg.idxmin()
    peak_month = monthly_avg.idxmax()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("기준 지표 (1순위)", target_col)
    col2.metric("1월 평균 지수", f"{jan_avg:.1f} pt")
    col3.metric("2~3월 관심도 감소율", f"{drop_rate:.1f}%", delta=f"{drop_rate:.1f}%", delta_color="inverse")
    col4.metric("연중 최저 관심 시기", f"{lowest_month}월", delta=f"피크는 {peak_month}월")

    st.divider()

    tab1, tab2, tab3 = st.tabs(["📉 작심삼일 시계열 추이", "📅 월별 주기 & 히트맵", "💼 비즈니스 & 개인 가이드"])

    with tab1:
        st.subheader("일별 검색량 추이 및 1월 집중 구간")
        valid_cols = [c for c in categories if c in df.columns]
        fig_line = px.line(
            df,
            x="date",
            y=valid_cols,
            labels={"value": "상대 검색 지수 (0~100)", "date": "일자", "variable": "카테고리"},
            template="plotly_white"
        )

        years = df["year"].unique()
        for y in years:
            jan_start = f"{y}-01-01"
            jan_end = f"{y}-01-31"
            fig_line.add_vrect(
                x0=jan_start, x1=jan_end,
                fillcolor="rgba(255, 75, 75, 0.12)",
                layer="below", line_width=0,
                annotation_text=f"{y}년 1월 피크", annotation_position="top left"
            )

        fig_line.update_layout(
            height=450,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with tab2:
        col_chart1, col_chart2 = st.columns(2)
        valid_cols = [c for c in categories if c in df.columns]

        with col_chart1:
            st.subheader("1~12월 평균 관심도 비교")
            monthly_summary = df.groupby("month")[valid_cols].mean().reset_index()

            fig_bar = px.bar(
                monthly_summary,
                x="month",
                y=valid_cols,
                barmode="group",
                labels={"month": "월 (Month)", "value": "평균 검색 지수"},
                template="plotly_white"
            )
            fig_bar.update_layout(xaxis=dict(tickmode="linear", tick0=1, dtick=1), height=400)
            st.plotly_chart(fig_bar, use_container_width=True)

        with col_chart2:
            st.subheader(f"연도별 x 월별 히트맵 ({target_col})")
            heatmap_data = df.pivot_table(index="year", columns="month", values=target_col, aggfunc="mean")

            fig_heatmap = px.imshow(
                heatmap_data,
                labels=dict(x="월", y="연도", color="검색 지수"),
                x=list(range(1, 13)),
                color_continuous_scale="Reds",
                template="plotly_white"
            )
            fig_heatmap.update_layout(height=400)
            st.plotly_chart(fig_heatmap, use_container_width=True)

    with tab3:
        st.subheader("데이터 기반 실천 가이드 & 마케팅 인사이트")
        col_insight1, col_insight2 = st.columns(2)

        with col_insight1:
            st.markdown("#### 🏃 개인 사용자 (습관 지속 전략)")
            st.markdown(f"""
            - **1월 결심 거품 경계**: 1월 첫 2주는 관심도가 연중 최고조에 달하지만, 2월에 진입하면서 평균 {abs(drop_rate):.1f}% 하락합니다.
            - **2월 '고비 구간' 넘기기**: 2월에 의지력이 약해지는 것은 개인의 나태함이 아닌 보편적인 통계적 현상입니다.
            - **미세 습관 설계**: 1월에 세운 거대한 목표를 2월 초에 1/3 수준으로 축소하여 지속성을 유지하는 것이 핵심입니다.
            """)

        with col_insight2:
            st.markdown("#### 📢 관련 업계 (피트니스·어학 마케팅 전략)")
            st.markdown("""
            - **신규 유치 골든타임 (12월 말 ~ 1월 중순)**: 새해 결심 심리가 최고조일 때 '얼리버드 연간권', '시작 패키지' 집중 집행.
            - **이탈 방지 프로모션 (2월 중순 ~ 3월 초)**: 관심이 급감하고 출석률이 떨어지는 시점에 '출석 챌린지', '친구 동반 리텐션 이벤트' 전환.
            - **여름 시즌 2차 피크 (6~7월)**: 방학 및 노출 시즌에 대비한 단기 집중 코스 프로모션 진행 적기.
            """)

    st.divider()
    st.subheader("📥 원본 데이터 확인 및 다운로드")
    st.dataframe(df.head(10), use_container_width=True)
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="CSV 파일 다운로드",
        data=csv,
        file_name="self_development_trend_data.csv",
        mime="text/csv"
    )
else:
    st.warning("선택된 카테고리가 없거나 데이터를 불러올 수 없습니다.")
