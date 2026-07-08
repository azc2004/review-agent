import streamlit as st
import os
import base64
import json
from PIL import Image
import io
from openai import OpenAI
from dotenv import load_dotenv
import urllib.request
import urllib.parse

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

def search_halfclub_products(keyword):
    """하프클럽 검색 API를 호출하여 상품 목록을 가져옵니다."""
    if not keyword.strip():
        return []
    
    encoded_keyword = urllib.parse.quote(keyword.strip())
    url = f"https://hapix.halfclub.com/searches/prdList/?keyword={encoded_keyword}&device=pc&limit=0,100&sortSeq=12"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if res_data and "data" in res_data and res_data["data"]:
                inner_data = res_data["data"]
                if "result" in inner_data and inner_data["result"]:
                    result = inner_data["result"]
                    if "hits" in result and result["hits"]:
                        hits = result["hits"].get("hits", [])
                        
                        products = []
                        for h in hits:
                            source = h.get("_source", {})
                            if source:
                                # 이미지 URL 파싱
                                prd_img = source.get("prdImg") or ""
                                prd_img_url = ""
                                if prd_img:
                                    if prd_img.startswith("http"):
                                        prd_img_url = prd_img
                                    else:
                                        clean_path = prd_img.lstrip('/')
                                        prd_img_url = f"https://cdn2.halfclub.com/{clean_path}"
                                
                                products.append({
                                    "prdNo": source.get("prdNo"),
                                    "prdNm": source.get("prdNm"),
                                    "brandNm": source.get("brandNm"),
                                    "znCtgrNm": source.get("znCtgrNm", "기타"),
                                    "prdImgUrl": prd_img_url,
                                    "selPrc": source.get("selPrc")
                                })
                        return products
        return []
    except Exception as e:
        print(f"Error searching halfclub products: {e}")
        return []

def get_halfclub_product_detail(prd_no):
    """하프클럽 상품 상세 API를 호출하여 상품 메타정보를 가져옵니다."""
    if not prd_no:
        return None
        
    url = f"https://hapix.halfclub.com/product/products/withoutPrice/{prd_no}?countryCd=001&langCd=001&siteCd=1&deviceCd=001"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if res_data and "data" in res_data and res_data["data"]:
                detail = res_data["data"]
                
                disp_ctgr = detail.get("dispCtgr", {})
                category_list = []
                for key in ["dispCtgrNm1", "dispCtgrNm2", "dispCtgrNm3"]:
                    val = disp_ctgr.get(key)
                    if val:
                        category_list.append(val)
                category_str = " > ".join(category_list) if category_list else "기타"
                
                # 이미지 정보 수집 (대표 이미지 및 추가 이미지 9종)
                image_info = detail.get("productImage", {})
                raw_image_paths = []
                
                if image_info:
                    if image_info.get("basicExtNm"):
                        raw_image_paths.append(image_info.get("basicExtNm"))
                    for i in range(1, 10):
                        key = f"add{i}ExtNm"
                        if image_info.get(key):
                            raw_image_paths.append(image_info.get(key))
                
                # 이미지 풀 URL 빌드
                full_image_urls = []
                for path in raw_image_paths:
                    if path.startswith("http"):
                        full_image_urls.append(path)
                    else:
                        clean_path = path.lstrip('/')
                        full_image_urls.append(f"https://cdn2.halfclub.com/{clean_path}")
                
                return {
                    "prdNo": detail.get("prdNo"),
                    "prdNm": detail.get("prdNm"),
                    "brandNm": detail.get("brandMainNmKr") or "기타",
                    "category": category_str,
                    "images": full_image_urls
                }
        return None
    except Exception as e:
        print(f"Error getting halfclub product detail: {e}")
        return None

def validate_product_image(api_key, model_name, image_base64, mime_type, product_name, brand, product_images):
    """Vision API를 호출하여 업로드된 이미지와 상품의 공식 이미지들을 비교하여 일치 여부를 판단합니다."""
    client = OpenAI(api_key=api_key)
    
    # 공식 이미지들을 최대 2개로 제한하여 비용 및 입력 토큰 절감
    reference_images = product_images[:2] if product_images else []
    
    prompt = f"""
당신은 업로드된 사진 속의 제품이 사용자가 선택한 상품 정보 및 공식 판매 이미지와 일치하거나 부합하는 카테고리의 상품인지 판별하는 AI 검증기입니다.

[선택한 상품 정보]:
- 상품명: "{product_name}"
- BRAND: "{brand}"

[이미지 구조 안내]:
- 첫 번째 이미지(Base64 인코딩): 사용자가 리뷰에 등록하기 위해 업로드한 실제 사진입니다.
- 두 번째 및 그 이후 이미지(URL 링크): 쇼핑몰에 등록된 해당 상품의 공식 대표/추가 이미지(참조용)입니다.

[검증 기준]:
1. 첫 번째 이미지(사용자 사진) 속 제품이 공식 이미지에 묘사된 제품과 동일한 모델, 브랜드, 디자인, 형태의 상품이 맞는지 시각적으로 직접 대조 및 분석하십시오.
2. 공식 이미지 및 브랜드 특징(로고, 특유 디자인 등)이 사용자의 사진과 불일치하면 거짓(false)으로 판별하십시오. (예: 공식 제품은 반바지인데 사용자 사진은 신발인 경우 false, 공식 브랜드는 나이키인데 사용자 사진 속 로고가 아디다스인 경우 false)
3. 두 대상이 동일한 디자인과 외형을 지니고 있거나, 동일한 종류의 합당한 상품인 경우 참(true)으로 판별하십시오. (단, 색상은 옵션에 따라 다를 수 있으므로 색상이 살짝 다른 것은 브랜드와 디자인 모델이 같다면 일치(true)로 간주할 수 있습니다. 단, 디자인 자체가 아ye 다르면 false입니다.)
4. 사용자의 사진에 제품이 없거나, 식별할 수 없는 경우 거짓(false)으로 판별합니다.

[출력 포맷]:
반드시 다음 JSON 형식으로만 응답하십시오:
{{
  "is_match": true 또는 false,
  "reason": "공식 이미지와 대조한 구체적인 판단 근거(시각적 외형 대조 결과, 로고 일치 여부 등 포함)를 한국어 1~2문장으로 간결하게 설명"
}}
JSON 외의 마크다운 블록(```json 등)이나 설명 텍스트는 절대 포함하지 마십시오.
"""

    # messages content 구성
    content_list = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{image_base64}"
            }
        }
    ]
    
    # 공식 이미지들을 image_url 형태로 순차적으로 content_list에 삽입
    for img_url in reference_images:
        content_list.append({
            "type": "image_url",
            "image_url": {
                "url": img_url
            }
        })

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": content_list
                }
            ],
            response_format={"type": "json_object"},
            max_tokens=250,
            temperature=0.0
        )
        
        result_text = response.choices[0].message.content
        return json.loads(result_text)
    except Exception as e:
        return {
            "is_match": False,
            "reason": f"이미지 대조 검증 중 오류가 발생했습니다: {str(e)}"
        }

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
if "search_keyword" not in st.session_state:
    st.session_state.search_keyword = ""
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None
if "is_direct_input" not in st.session_state:
    st.session_state.is_direct_input = False
if "direct_product_name" not in st.session_state:
    st.session_state.direct_product_name = ""
if "direct_product_brand" not in st.session_state:
    st.session_state.direct_product_brand = ""
if "direct_product_price" not in st.session_state:
    st.session_state.direct_product_price = ""
if "last_validated_key" not in st.session_state:
    st.session_state.last_validated_key = None
if "validation_result" not in st.session_state:
    st.session_state.validation_result = None

with col1:
    st.markdown('<div class="review-card">', unsafe_allow_html=True)
    st.subheader("1. 상품 정보 및 사진 업로드")
    
    # 상품 검색 UI
    search_keyword = st.text_input(
        "리뷰할 상품을 검색해 주세요",
        value=st.session_state.search_keyword,
        placeholder="예: 운동화, 머그컵, 아이패드",
        help="구매하신 상품을 검색하면 리스트가 나타납니다."
    )
    
    # 검색어가 변경된 경우 상태 초기화
    if search_keyword != st.session_state.search_keyword:
        st.session_state.search_keyword = search_keyword
        st.session_state.analysis_result = None
        st.session_state.edited_review = ""
        st.session_state.validation_result = None
        st.session_state.last_validated_key = None
        st.session_state.selected_product = None
        if "review_area" in st.session_state:
            st.session_state.review_area = ""
            
    # 검색어 기준 하프클럽 상품 실시간 검색
    filtered_products = []
    if search_keyword.strip():
        with st.spinner("하프클럽 상품 검색 중..."):
            filtered_products = search_halfclub_products(search_keyword)
        
    # 직접 입력 여부 토글
    is_direct_input = st.checkbox("원하는 상품이 목록에 없어 직접 입력하겠습니다.", value=st.session_state.is_direct_input)
    if is_direct_input != st.session_state.is_direct_input:
        st.session_state.is_direct_input = is_direct_input
        st.session_state.analysis_result = None
        st.session_state.edited_review = ""
        st.session_state.validation_result = None
        st.session_state.last_validated_key = None
        st.session_state.selected_product = None
        if "review_area" in st.session_state:
            st.session_state.review_area = ""
        st.rerun()
        
    product_name_for_validation = ""
    product_brand_for_validation = ""
    
    if is_direct_input:
        direct_name = st.text_input("직접 입력할 상품명", value=st.session_state.direct_product_name, placeholder="예: 구찌 마몬트 카드 케이스")
        direct_brand = st.text_input("직접 입력할 브랜드명", value=st.session_state.direct_product_brand, placeholder="예: 구찌")
        direct_price = st.text_input("직접 입력할 가격 (선택사항)", value=st.session_state.direct_product_price, placeholder="예: 120000")
        
        if (direct_name != st.session_state.direct_product_name 
            or direct_brand != st.session_state.direct_product_brand 
            or direct_price != st.session_state.direct_product_price):
            
            st.session_state.direct_product_name = direct_name
            st.session_state.direct_product_brand = direct_brand
            st.session_state.direct_product_price = direct_price
            st.session_state.analysis_result = None
            st.session_state.edited_review = ""
            st.session_state.validation_result = None
            st.session_state.last_validated_key = None
            if "review_area" in st.session_state:
                st.session_state.review_area = ""
            st.rerun()
            
        product_name_for_validation = direct_name
        product_brand_for_validation = direct_brand
    else:
        # 검색어가 입력된 상태에서만 리스트를 노출한다
        if search_keyword.strip():
            if filtered_products:
                st.markdown("##### 🔍 상품 검색 결과 (사진 클릭 시 새 탭에서 상세 이동)")
                
                # 가독성과 스크롤 최적화를 위해 상위 12개 노출
                display_products = filtered_products[:12]
                
                cols_per_row = 3
                for i in range(0, len(display_products), cols_per_row):
                    row_products = display_products[i:i+cols_per_row]
                    cols = st.columns(cols_per_row)
                    
                    for idx, p in enumerate(row_products):
                        with cols[idx]:
                            # 썸네일 이미지 노출 (클릭 시 새 탭에서 이동하도록 HTML 처리)
                            if p["prdImgUrl"]:
                                st.markdown(
                                    f'<a href="https://www.halfclub.com/product/{p["prdNo"]}" target="_blank" style="text-decoration: none;">'
                                    f'<img src="{p["prdImgUrl"]}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 8px; cursor: pointer;">'
                                    f'</a>',
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    '<div style="width: 100%; aspect-ratio: 1/1; background-color: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 8px; font-size: 0.85rem; color: #a0aec0;">이미지 없음</div>',
                                    unsafe_allow_html=True
                                )
                            
                            # 브랜드명 고정 높이 처리 (줄 틀어짐 방지)
                            st.markdown(
                                f'<div style="height: 20px; overflow: hidden; margin-bottom: 2px;">'
                                f'<span style="font-size: 0.8rem; color: #a0aec0; font-weight: bold;">{p["brandNm"]}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            # 상품명 고정 높이 및 최대 2줄 제한 (줄 틀어짐 방지)
                            st.markdown(
                                f'<div style="height: 42px; overflow: hidden; margin-bottom: 12px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; line-height: 1.3;">'
                                f'<span style="font-size: 0.85rem; color: #e2e8f0;">{p["prdNm"]}</span>'
                                f'</div>',
                                unsafe_allow_html=True
                            )
                            
                            is_selected = (
                                st.session_state.selected_product is not None 
                                and st.session_state.selected_product.get("prdNo") == p["prdNo"]
                            )
                            
                            if is_selected:
                                st.success("✅ 선택됨")
                                st.button("선택됨", key=f"sel_btn_{p['prdNo']}", disabled=True, use_container_width=True)
                            else:
                                if st.button("👉 선택", key=f"sel_btn_{p['prdNo']}", use_container_width=True):
                                    with st.spinner("선택된 상품 상세 정보 불러오는 중..."):
                                        detail_info = get_halfclub_product_detail(p["prdNo"])
                                        
                                    if detail_info:
                                        detail_info["selPrc"] = p.get("selPrc")
                                        st.session_state.selected_product = detail_info
                                    else:
                                        st.session_state.selected_product = {
                                            "prdNo": p["prdNo"],
                                            "prdNm": p["prdNm"],
                                            "brandNm": p["brandNm"] or "기타",
                                            "category": p["znCtgrNm"] or "기타",
                                            "images": [p["prdImgUrl"]] if p["prdImgUrl"] else [],
                                            "selPrc": p.get("selPrc")
                                        }
                                    st.session_state.analysis_result = None
                                    st.session_state.edited_review = ""
                                    st.session_state.validation_result = None
                                    st.session_state.last_validated_key = None
                                    if "review_area" in st.session_state:
                                        st.session_state.review_area = ""
                                    st.rerun()
                                    
                if st.session_state.selected_product:
                    product_name_for_validation = st.session_state.selected_product["prdNm"]
                    product_brand_for_validation = st.session_state.selected_product["brandNm"]
            else:
                st.info("🔍 검색 결과가 없습니다. 검색어를 수정하시거나 '직접 입력'을 선택해 주세요.")
        else:
            st.info("💡 위의 검색창에 리뷰할 상품명(예: 운동화, 아이패드)을 입력해 주세요.")
            
    # col1 래핑 종료
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="review-card">', unsafe_allow_html=True)
    
    uploaded_file = None
    is_valid_image = False
    
    # 상품 선택(또는 직접 입력)이 완료되었을 때만 우측에 정보 카드와 사진 업로드 UI를 렌더링한다
    if product_name_for_validation.strip():
        # --- 선택 상품 정보 카드 렌더링 ---
        thumbnail_url = ""
        category_str = "직접 입력 상품"
        price_str = "가격 정보 없음"
        
        if not st.session_state.is_direct_input and st.session_state.selected_product:
            category_str = st.session_state.selected_product.get("category", "기타")
            p_images = st.session_state.selected_product.get("images", [])
            if p_images:
                thumbnail_url = p_images[0]
                
            raw_price = st.session_state.selected_product.get("selPrc")
            if raw_price is not None:
                try:
                    price_str = f"{int(raw_price):,}원"
                except Exception:
                    price_str = f"{raw_price}원"
        elif st.session_state.is_direct_input and st.session_state.direct_product_price:
            raw_price = st.session_state.direct_product_price
            try:
                clean_price = "".join(filter(str.isdigit, raw_price))
                if clean_price:
                    price_str = f"{int(clean_price):,}원"
                else:
                    price_str = f"{raw_price}"
            except Exception:
                price_str = f"{raw_price}"
                
        # 카드 HTML 빌드 (좌측 리스트의 크기/비율과 완벽 통일: width 100%, 1:1 aspect ratio)
        img_html = ""
        if thumbnail_url:
            prd_no_val = st.session_state.selected_product.get("prdNo", "")
            img_html = (
                f'<a href="https://www.halfclub.com/product/{prd_no_val}" target="_blank" style="text-decoration: none;">'
                f'<img src="{thumbnail_url}" style="width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px; cursor: pointer;">'
                f'</a>'
            )
        else:
            img_html = f'<div style="width: 100%; aspect-ratio: 1/1; background-color: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); margin-bottom: 12px; font-size: 0.85rem; color: #a0aec0;">사진 없음</div>'
            
        st.markdown(
            f'<div style="background-color: rgba(255,255,255,0.03); padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); margin-bottom: 20px; width: 33.33%; min-width: 180px;">'
            f'{img_html}'
            f'<div style="font-size: 0.75rem; color: #a0aec0; font-weight: bold; margin-bottom: 4px;">{product_brand_for_validation.upper()}</div>'
            f'<div style="font-size: 0.85rem; color: #ffffff; font-weight: bold; margin-bottom: 6px; line-height: 1.3;">{product_name_for_validation}</div>'
            f'<div style="font-size: 0.75rem; color: #718096; margin-bottom: 6px;">카테고리: {category_str}</div>'
            f'<div style="font-size: 1.0rem; color: #38a169; font-weight: bold;">{price_str}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        # ----------------------------------
        
        st.subheader("2. 상품 사진 첨부")
        uploaded_file = st.file_uploader(
            f"[{product_brand_for_validation}] {product_name_for_validation} 사진을 첨부해 주세요 (JPG, PNG, WEBP)", 
            type=["png", "jpg", "jpeg", "webp"],
            help="리뷰를 작성할 상품의 실제 사진을 올려주세요. 상품과 다른 이미지 업로드 시 검증 단계에서 차단됩니다."
        )
        
        # 새로운 파일이 업로드되었거나 파일이 제거된 경우 세션 초기화 (캐시 잔상 제거)
        current_file_name = uploaded_file.name if uploaded_file else None
        if current_file_name != st.session_state.last_file_name:
            st.session_state.analysis_result = None
            st.session_state.edited_review = ""
            st.session_state.last_file_name = current_file_name
            st.session_state.validation_result = None
            st.session_state.last_validated_key = None
            if "review_area" in st.session_state:
                st.session_state.review_area = ""
            st.rerun()
            
        if uploaded_file is not None:
            # 캐시 키 생성: (파일명, 상품명, 브랜드, 공식 이미지 리스트 튜플)
            product_images_list = tuple(st.session_state.selected_product.get("images", [])) if st.session_state.selected_product else ()
            cache_key = (
                uploaded_file.name, 
                product_name_for_validation.strip(), 
                product_brand_for_validation.strip(),
                product_images_list
            )
            
            # API 키가 제공되었는지 검증
            if not api_key:
                st.error("🔑 OpenAI API Key가 입력되지 않아 이미지 자동 검증을 수행할 수 없습니다.")
            else:
                # 검증 결과 캐시 확인 및 API 호출
                if st.session_state.last_validated_key != cache_key or st.session_state.validation_result is None:
                    with st.spinner("업로드된 사진이 선택하신 상품과 일치하는지 AI 검증 중..."):
                        try:
                            base64_image = encode_image_to_base64(uploaded_file)
                            mime_type = uploaded_file.type
                            
                            val_result = validate_product_image(
                                api_key=api_key,
                                model_name=model_name,
                                image_base64=base64_image,
                                mime_type=mime_type,
                                product_name=product_name_for_validation.strip(),
                                brand=product_brand_for_validation.strip(),
                                product_images=st.session_state.selected_product.get("images", []) if st.session_state.selected_product else []
                            )
                            st.session_state.validation_result = val_result
                            st.session_state.last_validated_key = cache_key
                        except Exception as e:
                            st.session_state.validation_result = {
                                "is_match": False,
                                "reason": f"검증 API 호출 중 오류가 발생했습니다: {str(e)}"
                            }
                            st.session_state.last_validated_key = cache_key
                
                # 검증 결과 렌더링
                validation = st.session_state.validation_result
                if validation and validation.get("is_match"):
                    st.success(f"✅ 올바른 상품 사진이 확인되었습니다.\n\n**AI 의견:** {validation.get('reason')}")
                    is_valid_image = True
                    # 업로드 이미지 화면에 표시
                    image = Image.open(uploaded_file)
                    st.image(image, caption=f"업로드된 {product_name_for_validation} 이미지", use_container_width=True)
                else:
                    reason = validation.get("reason") if validation else "알 수 없는 오류"
                    st.error(f"❌ **상품 불일치 경고:** 선택하신 상품({product_name_for_validation})과 업로드한 사진의 제품이 일치하지 않습니다.\n\n**AI 의견:** {reason}")
                    st.warning("⚠️ 올바른 상품 사진이 아니므로 리뷰 작성을 진행할 수 없으며, 첨부에서 제외됩니다.")
                    
        st.markdown("---")
        st.subheader("3. AI 상품 리뷰 생성")
    else:
        st.info("💡 좌측에서 상품을 먼저 탐색하고 선택하시면 우측에 사진 첨부 및 리뷰 생성 영역이 나타납니다.")
        uploaded_file = None
        is_valid_image = False
        
    # 생성 버튼 트리거
    generate_btn = st.button("✨ AI 리뷰 초안 만들기", width='stretch', type="primary")
    
    if generate_btn:
        if not api_key:
            st.error("❌ OpenAI API Key가 입력되지 않았습니다. 사이드바에서 입력하거나 .env 파일을 확인해 주세요.")
        elif uploaded_file is None:
            st.error("❌ 리뷰를 생성하려면 먼저 상품 사진을 업로드해 주세요.")
        elif not is_valid_image:
            st.error("❌ 입력한 상품명과 일치하는 올바른 이미지가 첨부되어야 리뷰를 생성할 수 있습니다.")
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
