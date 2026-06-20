import os
import urllib.request
import urllib.parse
import json
import re
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

load_dotenv()

MOCK_COMPANY_INSIGHTS = {
    "삼성전자": {
        "values": "초일류 기술 리더십, 인재 제일, 최고지향, 변화선도, 정도경영, 상생추구",
        "news_topics": [
            "온디바이스 AI 탑재 및 HBM 반도체 메모리 경쟁력 강화 집중",
            "글로벌 경기 둔화 속 반도체 적자 극복 및 차세대 파운드리 2나노 공정 개발",
            "친환경 저전력 가전 출시 및 글로벌 공급망 다변화 대응"
        ],
        "talent_profile": "열정과 창의로 가치를 창출하는 창조인, 도전을 멈추지 않는 혁신인, 소통과 협력의 협동인",
        "recommendations": "반도체 및 하드웨어 전문 기술뿐만 아니라 AI 융합 능력과 글로벌 마인드를 자소서에 적극 어필하세요."
    },
    "네이버": {
        "values": "끊임없는 도전과 기술 혁신, 글로벌 파트너 동반 성장, 기술 민주주의 실현",
        "news_topics": [
            "초거대 AI '하이퍼클로바X' 기반의 B2B 솔루션 및 검색/커머스 전반 서비스 고도화",
            "북미 리커머스 플랫폼 포쉬마크 인수 후 글로벌 웹툰 사업과 시너지 극대화",
            "생성형 AI 안전성 프레임워크 구축 및 규제 대응력 확보"
        ],
        "talent_profile": "스스로 도전하고 성취하는 자기주도적 인재, 협업을 통해 동료와 시너지를 내는 구성원, 사용자 요구를 민감하게 캐치하는 고객 중심 태도",
        "recommendations": "프로젝트에서 마주한 기술적 문제를 깊게 파고들어 주도적으로 해결했던 에피소드를 네이버의 기술 중심 문화와 매칭하세요."
    },
    "카카오": {
        "values": "가장 카카오다운 방식으로 더 나은 세상을 만듦, 기술과 커넥트를 통한 더 편리한 일상 실현",
        "news_topics": [
            "카카오톡 핵심 탭(오픈채팅, 쇼핑) 고도화 및 로컬 광고 활성화",
            "카카오브레인 AI 사업 부문 본사 합병 및 신규 대화형 AI 서비스 런칭 준비",
            "준법경영 시스템 정비 및 투명성 회복 중심의 지배구조 개선 경영"
        ],
        "talent_profile": "스스로 해결 방법을 찾는 주도성, 오픈 마인드로 솔직하게 공유하고 소통하는 태도, 기술 혁신에 주저함이 없는 적극적 지향성",
        "recommendations": "자유롭고 열린 소통 방식 속에서 비효율을 찾고, 스스로 실행력을 발휘해 성과를 거둔 수평적 협업 성공 경험을 강조하세요."
    },
    "토스": {
        "values": "금융을 더 쉽고 간편하게, 기존 공급자 중심 금융 시장의 혁신, 극도의 고객 중심주의 실천",
        "news_topics": [
            "토스뱅크 및 토스증권의 흑자 성장세 안착과 코스피 상장(IPO) 본격 준비",
            "금융 마이데이터 활성화 및 신용대출 비교 대안 평가 모델 고도화",
            "오프라인 단말기 사업(토스플레이스) 결제 인프라 확장 가속화"
        ],
        "talent_profile": "비효율에 맞서 끝없이 집착하고 극복해 내는 실행력, 데이터에 기반한 이성적 판단과 탁월성에 대한 열망, 원팀(One-team)으로서 목표를 위해 동료와 신뢰를 지키는 태도",
        "recommendations": "주어진 업무를 완수하는 것을 넘어, 자율적으로 문제를 발굴하고 폭발적인 속도로 성과를 이루어 낸 경험을 보여주어야 합니다."
    },
    "한국전력공사": {
        "values": "안정적인 고품질 전력 공급으로 국가 경제 발전에 기여, 탄소중립 에너지 선도, 미래 전력망 신성장동력 창출",
        "news_topics": [
            "재무구조 개선을 위한 자산 매각 및 대규모 송배전 설비 운영 효율화 대책 추진",
            "사우디/UAE 등 글로벌 원자력 발전소 추가 수출 협의 및 송전망 신사업 개척",
            "탄소 배출 저감을 위한 신재생에너지 인프라 연동망 개발"
        ],
        "talent_profile": "공공 이익과 사회적 가치를 깊이 공감하는 공헌인, 도전적인 문제 해결을 선도하는 도전인, 신뢰와 존중으로 화합하는 협력인",
        "recommendations": "개인의 이익보다 조직이나 공공의 이익을 먼저 생각하고, 규칙과 약속을 투명하게 지켜 팀워크를 성공으로 이끈 도덕성 경험을 제시하세요."
    },
    "현대자동차": {
        "values": "인류를 향한 진보(Progress for Humanity), 미래 모빌리티 혁신 주도, 무결점 안전과 최상의 품질",
        "news_topics": [
            "SDV(소프트웨어 중심 자동차)로의 하드웨어/소프트웨어 아키텍처 대전환 및 자체 OS 탑재 가속화",
            "미국 전기차 전용 공장 완공 및 하이브리드(HEV) 차종 다변화 전략 추진",
            "자율주행 4단계 고도화 및 도심항공모빌리티(UAM) 미래 시장 개척"
        ],
        "talent_profile": "현실에 안주하지 않고 목표를 상향 조절하는 끝없는 도전 정신, 이해관계자와 유연하게 협력하는 글로벌 마인드, 미래 모빌리티 트렌드에 대응하는 창조적 역량",
        "recommendations": "차량 도메인 기술뿐만 아니라 대규모 데이터 제어, 무결점 소프트웨어 검증 능력 등 SDV 패러다임 변화에 본인이 기여할 수 있는 전문성을 적극 녹이세요."
    }
}

def analyze_company_with_llm(company_name: str, search_text: str) -> dict:
    """수집된 네이버 검색 텍스트를 바탕으로 Gemini LLM을 사용하여 기업을 분석합니다."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("[Naver API Analysis] GEMINI_API_KEY가 없어 가상 분석 데이터를 반환합니다.")
        return get_fallback_insight(company_name)
        
    prompt_template = """너는 기업 채용 분석가이자 취업 컨설턴트이다.
아래에 제공된 기업({company_name})에 대한 네이버 뉴스/블로그 검색 요약문들을 종합 분석하여, 자소서 작성에 바로 참고할 수 있는 핵심 리포트를 작성해라.

[요구 분석 항목]
1. **values** (기업의 주요 가치관, 사업 비전 등 핵심 슬로건 2-3가지)
2. **news_topics** (최근 6개월 이내의 가장 핫한 비즈니스 이슈, 관심사, 뉴스 키워드 3가지)
3. **talent_profile** (이 기업이 추구하는 인재상 및 성향적 특징)
4. **recommendations** (이 회사에 자소서를 쓸 때 지원자가 어필하면 좋은 역량 매칭 꿀팁)

출력은 반드시 한국어로 작성하며, 아래의 JSON 형식을 완벽하게 준수하여 JSON 문자열로만 출력해라. 백틱(```json ... ```)을 사용해 감싸라.

{{
  "values": "기업 가치관 요약 문자열",
  "news_topics": [
    "최신 관심사/이슈 1",
    "최신 관심사/이슈 2",
    "최신 관심사/이슈 3"
  ],
  "talent_profile": "인재상 요약 문자열",
  "recommendations": "자소서 작성 시 역량 매칭 권장 가이드라인"
}}

---
[검색 수집 데이터]
{search_text}
"""
    try:
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        prompt = PromptTemplate.from_template(prompt_template).format(
            company_name=company_name,
            search_text=search_text
        )
        response = llm.invoke(prompt)
        
        # Parse output JSON
        text = response.content.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            json_str = match.group(1).strip()
        else:
            json_str = text
            
        return json.loads(json_str)
    except Exception as e:
        print(f"[Naver API LLM Analysis Exception] {str(e)}. Fallback 데이터로 대체합니다.")
        return get_fallback_insight(company_name)

def get_fallback_insight(company_name: str) -> dict:
    """Mock 목록에 정의된 대기업인 경우 미리 설계된 정보 반환, 그 외의 경우 일반 분석 데이터 반환."""
    # Clean company name for matching
    cleaned = company_name.replace(" ", "").upper()
    for name, insight in MOCK_COMPANY_INSIGHTS.items():
        if name in cleaned or cleaned in name:
            return insight
            
    # Generic fallback
    return {
        "values": f"혁신과 창의를 통한 미래 경쟁력 확보, 고객 지향적 서비스 혁신, 열린 소통",
        "news_topics": [
            f"{company_name}의 디지털 트랜스포메이션 가속화 및 지속가능 성장(ESG) 경영 강화",
            f"글로벌 시장 개척과 원가 절감형 프로세스 개선",
            f"인공지능(AI)과 로봇 등 미래 신기술을 접목한 스마트 비즈니스 다변화"
        ],
        "talent_profile": "도전정신을 가지고 실천하는 주도적 인재, 정직함과 책임을 다하는 신뢰형 구성원, 협력과 상생을 도모하는 화합형 동료",
        "recommendations": f"{company_name}의 지속가능한 미래 사업 전략을 이해하고, 본인의 문제 해결력과 유연한 협업 시너지를 결합해 어필하세요."
    }

def fetch_company_insights(company_name: str) -> dict:
    """네이버 API로 기업 검색 뉴스/블로그를 호출한 후 LLM을 이용해 가치관과 트렌드를 요약합니다."""
    client_id = os.getenv("NAVER_CLIENT_ID")
    client_secret = os.getenv("NAVER_CLIENT_SECRET")
    
    if not client_id or not client_secret or client_id.strip() == "" or client_id == "your_client_id_here":
        print("[Naver API] Client ID/Secret 설정이 없으므로 Mock Fallback 데이터를 반환합니다.")
        return get_fallback_insight(company_name)
        
    try:
        # Search NAVER News
        enc_query = urllib.parse.quote(f"{company_name} 채용 OR {company_name} 공채")
        url_news = f"https://openapi.naver.com/v1/search/news.json?query={enc_query}&display=8"
        
        req_news = urllib.request.Request(url_news)
        req_news.add_header("X-Naver-Client-Id", client_id)
        req_news.add_header("X-Naver-Client-Secret", client_secret)
        
        news_summaries = []
        with urllib.request.urlopen(req_news, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            for item in data.get("items", []):
                title = re.sub(r'<[^>]*>', '', item["title"])
                desc = re.sub(r'<[^>]*>', '', item["description"])
                news_summaries.append(f"뉴스: {title} - {desc}")
                
        # Search NAVER Blogs for talent_profile
        enc_blog_query = urllib.parse.quote(f"{company_name} 인재상 OR {company_name} 사업전략")
        url_blog = f"https://openapi.naver.com/v1/search/blog.json?query={enc_blog_query}&display=5"
        
        req_blog = urllib.request.Request(url_blog)
        req_blog.add_header("X-Naver-Client-Id", client_id)
        req_blog.add_header("X-Naver-Client-Secret", client_secret)
        
        blog_summaries = []
        with urllib.request.urlopen(req_blog, timeout=8) as response:
            data = json.loads(response.read().decode('utf-8'))
            for item in data.get("items", []):
                title = re.sub(r'<[^>]*>', '', item["title"])
                desc = re.sub(r'<[^>]*>', '', item["description"])
                blog_summaries.append(f"블로그: {title} - {desc}")
                
        combined_text = "\n".join(news_summaries + blog_summaries)
        
        if not combined_text.strip():
            print("[Naver API] 검색 결과가 비어있으므로 Fallback 데이터를 제공합니다.")
            return get_fallback_insight(company_name)
            
        # Analyze with LLM
        return analyze_company_with_llm(company_name, combined_text)
        
    except Exception as e:
        print(f"[Naver API Exception] {str(e)}. Fallback 데이터로 즉시 복구합니다.")
        return get_fallback_insight(company_name)
