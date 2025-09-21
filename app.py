import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

def main():
    # --- 1. 페이지 기본 설정 ---
    st.set_page_config(
        page_title="대한민국 경제활동 데이터 대시보드",
        page_icon="📊",
        layout="wide"
    )

    # --- 새로운 카드 디자인을 위한 CSS ---
    st.markdown("""
    <style>
    .metric-card {
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 25px;
        text-align: center;
        box-shadow: 0 4px 8px 0 rgba(0,0,0,0.1);
        transition: 0.3s;
        height: 160px; /* 카드 높이 고정 */
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .metric-card:hover {
        box-shadow: 0 8px 16px 0 rgba(0,0,0,0.2);
    }
    .metric-title {
        font-size: 18px;
        color: #6c757d; /* 부드러운 회색 */
    }
    .metric-value {
        font-size: 2.5rem; /* 40px */
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)

    st.title("📊 대한민국 경제활동 데이터 대시보드")
    st.write("연도별, 지역별 취업률과 실업률 데이터를 필터링하고 시각화합니다.")

    # --- 2. 데이터 로딩 및 전처리 (캐싱) ---
    @st.cache_data
    def load_and_preprocess_data():
        """
        CSV 데이터를 불러오고, PRD 요구사항에 따라 전처리 및 지표를 계산합니다.
        - FR-01: 데이터 로딩
        - FR-02: '계' -> '전국' 변경, 지역 순서 유지
        - FR-03: 취업률/실업률 계산 (소수점 둘째 자리)
        """
        try:
            df = pd.read_csv('경제활동_통합.csv', encoding='utf-8-sig')
        except FileNotFoundError:
            st.error("'경제활동_통합.csv' 파일을 찾을 수 없습니다. 스크립트와 같은 디렉토리에 있는지 확인해주세요.")
            return None, None

        # FR-02: '계' -> '전국'으로 변경
        df['지역'] = df['지역'].replace('계', '전국')
        
        # FR-02: 지역 순서 유지를 위해 Categorical 타입으로 변환
        original_region_order = df['지역'].drop_duplicates().tolist()
        df['지역'] = pd.Categorical(df['지역'], categories=original_region_order, ordered=True)

        # 년도 컬럼을 카테고리 타입으로 변환하여 메모리 효율성 및 처리 속도 향상
        df['년도'] = df['년도'].astype('category')

        # FR-03: 핵심 지표 계산 (벡터화 연산 및 소수점 둘째 자리 반올림)
        econ_active_pop = df['경제활동인구 (천명)']
        employment_rate = np.divide(df['취업자 (천명)'], econ_active_pop, out=np.zeros_like(econ_active_pop, dtype=float), where=econ_active_pop!=0) * 100
        unemployment_rate = np.divide(df['실업자 (천명)'], econ_active_pop, out=np.zeros_like(econ_active_pop, dtype=float), where=econ_active_pop!=0) * 100

        df['취업률'] = employment_rate.round(2)
        df['실업률'] = unemployment_rate.round(2)

        return df, original_region_order

    df, region_order = load_and_preprocess_data()

    if df is None:
        st.stop()  # 데이터 로딩 실패 시 앱 실행 중지

    # --- 3. 사이드바 필터 ---
    st.sidebar.header("🔎 필터링 옵션")

    # 연도 선택 (다중)
    all_years = sorted(df['년도'].unique(), reverse=True)
    selected_years = st.sidebar.multiselect(
        '연도를 선택하세요 (다중 선택 가능)',
        options=all_years,
        default=[all_years[0]]  # 기본값: 가장 최신 연도
    )

    # 지역 선택 (단일)
    # PRD(FR-02)에 따라 원본 순서를 유지하고 '전국'을 포함합니다.
    selected_region = st.sidebar.selectbox(
        '지역을 선택하세요',
        options=region_order,
        index=0  # 기본값: '전국'
    )

    # 차트 테마 선택
    st.sidebar.header("🎨 차트 테마 설정")
    selected_theme = st.sidebar.selectbox(
        '차트 테마를 선택하세요',
        options=['plotly', 'plotly_white', 'plotly_dark', 'ggplot2', 'seaborn', 'simple_white'],
        index=1  # 기본값: 'plotly_white'
    )


    # --- 4. 데이터 필터링 ---
    if not selected_years:
        st.warning("하나 이상의 연도를 선택해주세요.")
        st.stop()

    # 연도 기준으로 1차 필터링
    filtered_df = df[df['년도'].isin(selected_years)]

    # '전국' 선택 시 모든 지역 데이터를, 특정 지역 선택 시 해당 지역 데이터만 필터링
    if selected_region == '전국':
        # '전국'을 선택하면 모든 지역의 데이터를 보여줌 (시각화/테이블용)
        display_df = filtered_df.copy()
    else:
        # 특정 지역을 선택하면 해당 지역의 데이터만 필터링
        display_df = filtered_df[filtered_df['지역'] == selected_region].copy()

    # --- 5. 핵심 지표 요약 카드 ---
    st.header("📈 핵심 지표 요약")

    # 지표 계산을 위한 데이터프레임 결정
    if selected_region == '전국':
        # '전국' 선택 시, '전국' 행들만 사용하여 국가 전체 지표 계산
        kpi_df = display_df[display_df['지역'] == '전국']
    else:
        # 특정 지역 선택 시, 해당 지역 데이터 사용
        kpi_df = display_df

    if not kpi_df.empty:
        # 선택된 기간의 평균 지표 계산
        avg_employment_rate = kpi_df['취업률'].mean()
        avg_unemployment_rate = kpi_df['실업률'].mean()
        avg_econ_pop = kpi_df['경제활동인구 (천명)'].mean()

        # 카드 레이아웃 생성
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{selected_region} 평균 취업률</div>
                <div class="metric-value">{avg_employment_rate:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{selected_region} 평균 실업률</div>
                <div class="metric-value">{avg_unemployment_rate:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{selected_region} 평균 경제활동인구</div>
                <div class="metric-value">{avg_econ_pop:,.0f} 천명</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("선택된 조건에 해당하는 데이터가 없어 지표를 표시할 수 없습니다.")

    # --- 6. 데이터 테이블 표시 ---
    st.header("📄 필터링된 데이터")
    st.write("") # 카드와 테이블 사이의 간격을 위한 빈 줄
    st.write(f"**선택 조건:** `{', '.join(map(str, selected_years))}년` / `{selected_region}`")

    # 가독성을 위해 숫자 포맷 지정
    st.dataframe(display_df.style.format({
        '경제활동인구 (천명)': '{:,.0f}',
        '취업자 (천명)': '{:,.0f}',
        '실업자 (천명)': '{:,.0f}',
        '취업률': '{:.2f}%',
        '실업률': '{:.2f}%'
    }))

    # --- 7. 데이터 시각화 (FR-07) ---
    st.header("📊 데이터 시각화")

    # 조건 1: 단일 연도 & '전국' 선택 시 -> 지역별 비교 막대 차트
    if len(selected_years) == 1 and selected_region == '전국':
        st.subheader(f"{selected_years[0]}년 지역별 취업률(막대)과 실업률(선) 비교")

        # '전국' 데이터는 제외하고 지역별로 비교
        plot_df = display_df[display_df['지역'] != '전국'].copy()

        # Plotly Graph Objects를 사용하여 주축과 보조축이 있는 차트 생성
        fig = go.Figure()

        # 취업률 (막대, 주축)
        fig.add_trace(go.Bar(
            x=plot_df['지역'],
            y=plot_df['취업률'],
            name='취업률',
            yaxis='y1',
            texttemplate='%{y:.2f}%',
            textposition='auto'
        ))

        # 실업률 (선, 보조축)
        fig.add_trace(go.Scatter(
            x=plot_df['지역'],
            y=plot_df['실업률'],
            name='실업률',
            mode='lines+markers',
            yaxis='y2'
        ))

        # 레이아웃 업데이트
        fig.update_layout(
            title_text=f'{selected_years[0]}년 지역별 취업률 및 실업률',
            xaxis_title='지역',
            yaxis=dict(title='취업률 (%)'),
            yaxis2=dict(title='실업률 (%)', overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template=selected_theme  # 선택된 테마 적용
        )
        st.plotly_chart(fig, use_container_width=True)

    # 조건 2: 다중 연도 & 특정 지역 선택 시 -> 연도별 추이 라인 차트
    elif len(selected_years) > 1 and selected_region != '전국':
        st.subheader(f"{selected_region} 연도별 취업률/실업률 추이 (주축/보조축)")

        plot_df = display_df.sort_values('년도').copy()
        # X축을 숫자 타입으로 변환하여 시간적 연속성을 표현하고, 틱을 제어합니다.
        # 'category' 타입을 유지하면 선택된 연도만 불연속적으로 표시됩니다.
        plot_df['년도'] = pd.to_numeric(plot_df['년도'])

        # Plotly Graph Objects를 사용하여 주축과 보조축이 있는 차트 생성
        fig = go.Figure()

        # 취업률 (주축)
        fig.add_trace(go.Scatter(
            x=plot_df['년도'],
            y=plot_df['취업률'],
            name='취업률',
            mode='lines+markers',
            yaxis='y1'
        ))

        # 실업률 (보조축)
        fig.add_trace(go.Scatter(
            x=plot_df['년도'],
            y=plot_df['실업률'],
            name='실업률',
            mode='lines+markers',
            yaxis='y2'
        ))

        # 레이아웃 업데이트
        fig.update_layout(
            title_text=f'{selected_region} 연도별 취업률/실업률 추이',
            xaxis_title='연도',
            xaxis=dict(
                tickmode='array',
                tickvals=[2021, 2022, 2023, 2024],
                ticktext=['2021', '2022', '2023', '2024']
            ),
            yaxis=dict(title='취업률 (%)'),
            yaxis2=dict(title='실업률 (%)', overlaying='y', side='right'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            template=selected_theme  # 선택된 테마 적용
        )
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("데이터 시각화는 다음 조건 중 하나를 만족할 때 제공됩니다:\n"
                "1. 단일 연도 & '전국' 지역 선택\n"
                "2. 다중 연도 & 특정 지역 선택")


if __name__ == "__main__":
    main()
