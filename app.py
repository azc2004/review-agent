import streamlit as st
import os
import base64
import json
from PIL import Image
import io
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 페이지 설정
st.set_page_config(
    page_title="Review AI - 스마트 상품평 생성기",
    page_icon="📸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 스타일링 (Premium Glassmorphism & Modern Design)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    /* 폰트 설정 */
    html, body, [class*="css"] {
        font-family: 'Outfit', 'Noto Sans KR', sans-serif;
    }
    
    /* 카드 디자인 */
    .review-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
    }
    
    /* 뱃지 디자인 */
    .keyword-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        padding: 6px 14px;
        margin: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.2s ease;
    }
    .keyword-badge:hover {
        transform: translateY(-2px);
    }
    
    /* 그라데이션 타이틀 */
    .gradient-title {
        background: linear-gradient(to right, #ff7e5f, #feb47b);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.8rem;
        font-weight: 800;
        margin-bottom: 5px;
    }
    
    /* 서브타이틀 */
    .subtitle {
        color: #a0aec0;
        font-size: 1.1rem;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------

def encode_image_to_base64(uploaded_file):
    """업로드된 이미지 파일을 base64 문자열로 변환합니다."""
    bytes_data = uploaded_file.getvalue()
    return base64.b64encode(bytes_data).decode('utf-8')

def generate_review(api_key, model_name, image_base64, mime_type, style, topics, rating):
    """OpenAI API를 사용하여 이미지 기반 리뷰 초안을 생성합니다."""
    client = OpenAI(api_key=api_key)
    
    # 프롬프트 구성
    style_guide = {
        "정중한 존댓말": "정중하고 예의 바른 격식체(~입니다, ~합니다)를 사용하십시오.",
        "친근한 반말": "친근한 반말체(~야, ~했어, ~인 듯)를 사용하여 블로그나 SNS에 올리는 느낌으로 작성하십시오.",
        "솔직담백한 한달 후기": "실제 한 달 동안 사용해 본 경험자의 시선으로, 장단점을 매우 솔직하고 상세하게 작성하십시오.",
        "블로그 체험단 스타일": "이모티콘을 적절히 섞어 활기차고 풍부한 묘사로 상품의 장점을 돋보이게 작성하십시오."
    }
    
    # 별점에 따른 긍정/부정/보통 감정 가이드라인 설정
    if rating == 5:
        sentiment_guide = (
            "이 리뷰는 매우 긍정적이고 대만족(별점 5/5점)한 상품평입니다. "
            "상품의 장점, 훌륭한 부분, 강력 추천하는 이유만을 가득 담아 극찬하는 톤으로 작성하십시오. "
            "절대로 부정적인 코멘트, 아쉬운 점, 단점, 배송 불만 등을 조금이라도 포함하지 마십시오."
        )
    elif rating == 4:
        sentiment_guide = (
            "이 리뷰는 긍정적이고 만족(별점 4/5점)한 상품평입니다. "
            "대체로 상품의 장점과 유용한 점들을 부각하여 만족스러운 톤으로 작성하되, "
            "신뢰도를 높이기 위해 일상적이고 사소한 아쉬운 점(예: 배송 상자가 조금 찌그러짐, 색상이 모니터 화면보다 아주 살짝 어두움 등)을 단 한 줄만 가볍게 덧붙이십시오."
        )
    elif rating == 3:
        sentiment_guide = (
            "이 리뷰는 보통/중립적(별점 3/5점)인 평범한 상품평입니다. "
            "상품에 대한 과장된 칭찬이나 일방적인 비난 없이, 마음에 들었던 점(장점)과 아쉬웠던 점(단점/개선사항)을 솔직하고 객관적으로 균형 있게 각각 절반씩 구성하여 작성하십시오."
        )
    else:  # 1 or 2 stars
        sentiment_guide = (
            f"이 리뷰는 매우 실망스럽고 부정적(별점 {rating}/5점)인 상품평입니다. "
            "상품의 결정적인 단점, 불만 사항, 품질 문제, 기대에 미치지 못한 원인 등을 중점적으로 묘사하여 비판적인 톤으로 작성하십시오. "
            "재구매 의사가 없거나 비추천하는 내용을 담되, 지나치게 감정적이거나 비하하는 욕설 대신 객관적인 팩트(예: 마감이 조잡함, 사진과 실물이 너무 다름, 기능 고장 등)에 근거하여 아쉬운 점을 상세히 고발하는 느낌으로 서술하십시오."
        )

    if topics:
        topic_instruction = f"오직 사용자가 선택한 강조 항목인 '{', '.join(topics)}'에 대한 내용만을 주제로 다루어 작성하십시오. 선택되지 않은 다른 요소나 측면(예: 선택되지 않은 가성비, 배송 상태, 조립 편의성, 사이즈 등)은 철저히 배제하고 리뷰 본문에 일절 언급하지 마십시오."
    else:
        topic_instruction = "상품의 전반적인 특징에 대해 언급하여 작성하십시오."
    
    prompt = f"""
당신은 대한민국 대표 쇼핑몰의 전문 상품평 리뷰 작성 도우미입니다.
업로드된 이미지를 세밀하게 분석하고 지정된 옵션에 맞추어 실제 구매자가 쓴 듯한 자연스러운 상품 리뷰 초안을 생성하십시오.

[작성 지침]
1. **리뷰 스타일**: {style_guide.get(style, style)}
2. **분석 및 강조 항목 제한**: {topic_instruction}
3. **별점 및 감정 지침**: {sentiment_guide}

[출력 포맷]
반드시 다음 JSON 스키마를 완벽히 준수하는 JSON 객체로만 응답하십시오:
{{
  "keywords": ["상품의핵심특징1", "추천태그2", "키워드3"],
  "review_draft": "이곳에 실제 리뷰 내용 텍스트를 작성하십시오. 줄바꿈(\\n)을 포함해 가독성 있게 작성하십시오."
}}
JSON 외의 마크다운 블록(```json 등)이나 설명 텍스트는 절대 포함하지 마십시오.
"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=1000,
            temperature=0.7
        )
        
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    
    except json.JSONDecodeError:
        # JSON 파싱 실패 대비 폴백
        return {
            "keywords": ["리뷰 생성 완료", "분석 성공"],
            "review_draft": result_text if 'result_text' in locals() else "리뷰 생성 결과를 파싱하는 데 실패했습니다."
        }
    except Exception as e:
        raise RuntimeError(f"OpenAI API 호출 중 오류가 발생했습니다: {str(e)}")

# ----------------- UI / Sidebar -----------------

st.sidebar.markdown("### ⚙️ 설정 구성")

# API Key 우선순위: 1. Streamlit Secrets (Streamlit Cloud 용) 2. 환경 변수 (.env) 3. 사이드바 입력
api_key = None

try:
    if "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    pass

if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

if api_key:
    st.sidebar.success("🔑 OpenAI API Key가 자동으로 로드되었습니다.")
else:
    api_key = st.sidebar.text_input("🔑 OpenAI API Key 입력", type="password", help="OpenAI API 키를 입력해 주세요.")
    if not api_key:
        st.sidebar.warning("API Key가 필요합니다. 설정하지 않으면 동작하지 않습니다.")

# 모델 선택
model_name = st.sidebar.selectbox(
    "🤖 AI 모델 선택",
    ["gpt-4o", "gpt-4o-mini"],
    index=1,
    help="gpt-4o-mini가 비용이 저렴하고 빠르지만, gpt-4o가 이미지 분석 품질이 높습니다."
)

# 리뷰 옵션 설정
st.sidebar.markdown("---")
st.sidebar.markdown("### ✍️ 리뷰 스타일 지정")

review_style = st.sidebar.radio(
    "리뷰 어조/스타일",
    ["정중한 존댓말", "친근한 반말", "솔직담백한 한달 후기", "블로그 체험단 스타일"],
    index=0
)

review_topics = st.sidebar.multiselect(
    "강조할 핵심 키워드 (다중 선택)",
    ["디자인 및 색상", "재질 및 촉감", "가성비/가격", "배송 상태 및 포장", "조립/사용 편의성", "사이즈 및 핏"],
    default=["디자인 및 색상", "재질 및 촉감"]
)

review_rating = st.sidebar.selectbox(
    "⭐ 상품 별점 (최대 5개)",
    options=[5, 4, 3, 2, 1],
    index=0,
    format_func=lambda x: "⭐" * x + f" ({x}점)",
    help="선택한 별점에 맞춰 긍정/중립/부정 리뷰 초안이 작성됩니다."
)

# ----------------- Main Layout -----------------

st.markdown('<div class="gradient-title">Review AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">📸 사진만 업로드하면 Vision LLM이 분석해 맞춤형 상품평 초안을 만들어 드립니다.</div>', unsafe_allow_html=True)

# 레이아웃 나누기 (좌: 업로더 & 이미지, 우: 분석 결과)
col1, col2 = st.columns([1, 1], gap="large")

# 세션 상태 변수 초기화
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "edited_review" not in st.session_state:
    st.session_state.edited_review = ""
if "last_file_name" not in st.session_state:
    st.session_state.last_file_name = None

with col1:
    st.markdown('<div class="review-card">', unsafe_allow_html=True)
    st.subheader("1. 상품 사진 업로드")
    
    uploaded_file = st.file_uploader(
        "이미지 파일을 선택해 주세요 (JPG, PNG, JPEG, WEBP)", 
        type=["png", "jpg", "jpeg", "webp"],
        help="리뷰할 상품의 사진을 업로드해 주세요."
    )
    
    # 새로운 파일이 업로드되었거나 파일이 제거된 경우 세션 초기화 (캐시 잔상 제거)
    current_file_name = uploaded_file.name if uploaded_file else None
    if current_file_name != st.session_state.last_file_name:
        st.session_state.analysis_result = None
        st.session_state.edited_review = ""
        st.session_state.last_file_name = current_file_name
        if "review_area" in st.session_state:
            st.session_state.review_area = ""
        st.rerun()
        
        
    if uploaded_file is not None:
        # 업로드 이미지 화면에 표시
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 상품 이미지", width='stretch')
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="review-card">', unsafe_allow_html=True)
    st.subheader("2. AI 상품 리뷰 생성")
    
    # 생성 버튼 트리거
    generate_btn = st.button("✨ AI 리뷰 초안 만들기", width='stretch', type="primary")
    
    if generate_btn:
        if not api_key:
            st.error("❌ OpenAI API Key가 입력되지 않았습니다. 사이드바에서 입력하거나 .env 파일을 확인해 주세요.")
        elif uploaded_file is None:
            st.error("❌ 리뷰를 생성하려면 먼저 상품 사진을 업로드해 주세요.")
        else:
            # 버튼 클릭 시 기존 리뷰 초안 초기화
            st.session_state.analysis_result = None
            st.session_state.edited_review = ""
            if "review_area" in st.session_state:
                st.session_state.review_area = ""
                
            with st.spinner("AI가 이미지를 정밀 분석하여 리뷰 초안을 작성 중입니다..."):
                try:
                    # 이미지 인코딩 및 API 호출
                    base64_image = encode_image_to_base64(uploaded_file)
                    mime_type = uploaded_file.type
                    
                    # API 호출
                    result = generate_review(
                        api_key=api_key,
                        model_name=model_name,
                        image_base64=base64_image,
                        mime_type=mime_type,
                        style=review_style,
                        topics=review_topics,
                        rating=review_rating
                    )
                    
                    # 세션 상태 저장
                    st.session_state.analysis_result = result
                    st.session_state.edited_review = result.get("review_draft", "")
                    st.session_state.review_area = result.get("review_draft", "")
                    
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
                    
    # 결과 출력부
    if st.session_state.analysis_result:
        # 1. 키워드 태그 렌더링
        st.markdown("##### 🏷️ 추출된 상품 키워드")
        keywords = st.session_state.analysis_result.get("keywords", [])
        badge_html = ""
        for kw in keywords:
            badge_html += f'<span class="keyword-badge">#{kw}</span>'
        st.markdown(badge_html, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        # 2. 리뷰 수정 텍스트 영역
        st.markdown("##### 📝 편집 가능한 리뷰 초안")
        edited_text = st.text_area(
            "이곳에서 리뷰를 마음에 들게 수정한 후 아래 등록 버튼을 눌러주세요.",
            value=st.session_state.edited_review,
            height=250,
            key="review_area"
        )
        # 텍스트 영역 실시간 변경사항 저장
        st.session_state.edited_review = edited_text
        
        # 3. 최종 등록 시뮬레이션 (히든 처리)
        # st.markdown("---")
        # submit_btn = st.button("🚀 최종 리뷰 등록하기", width='stretch')
        # 
        # if submit_btn:
        #     st.success("🎉 리뷰가 성공적으로 등록되었습니다! 소중한 평가 감사드립니다.")
        #     st.balloons()
        #     
        #     # 초기화 버튼
        #     if st.button("새 리뷰 작성하기"):
        #         st.session_state.analysis_result = None
        #         st.session_state.edited_review = ""
        #         if "review_area" in st.session_state:
        #             st.session_state.review_area = ""
        #         st.rerun()
    else:
        st.info("💡 사진을 업로드하고 'AI 리뷰 초안 만들기' 버튼을 누르면 이 영역에 분석 결과가 표시됩니다.")
        
    st.markdown('</div>', unsafe_allow_html=True)

# ----------------- Footer -----------------
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #718096; font-size: 0.85rem;'>"
    "© 2026 Review AI Prototype. Powered by Streamlit & OpenAI GPT-4o"
    "</div>",
    unsafe_allow_html=True
)
