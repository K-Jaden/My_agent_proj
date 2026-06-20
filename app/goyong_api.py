import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from app.database import (
    save_cached_recruitments,
    update_recruitment_detail,
    get_cached_recruitments,
    get_cached_recruitment
)

load_dotenv()

MOCK_RECRUITMENTS = [
    {
        "emp_seqno": "mock_samsung",
        "company": "삼성전자",
        "title": "2026년 DX부문 S/W 개발 및 인프라 엔지니어 신입 채용",
        "salary": "회사 내규에 따름 (대졸 초임 업계 최고 수준)",
        "close_date": "2026-07-15",
        "job_type": "정규직 (신입)",
        "job_cont": "- DX부문 S/W 개발 및 인프라 설계\n- C/C++, Java, Python 프로그래밍",
        "pref_cond": "S/W 관련 전공자 및 알고리즘 역량 우수자 우대"
    },
    {
        "emp_seqno": "mock_naver",
        "company": "네이버 (NAVER)",
        "title": "NAVER Cloud Front-End / Back-End 엔지니어 경력 및 신입 채용",
        "salary": "회사 내규에 따름",
        "close_date": "2026-07-20",
        "job_type": "정규직",
        "job_cont": "- NAVER Cloud 플랫폼 및 API 개발\n- React, Vue.js 및 Spring Boot 기반 아키텍처 설계",
        "pref_cond": "클라우드 인프라 이해도 높은 자 및 대용량 트래픽 처리 경험자 우대"
    },
    {
        "emp_seqno": "mock_kakao",
        "company": "카카오 (Kakao)",
        "title": "2026 하반기 기술분야 자기주도형 신입 개발자 공개 채용",
        "salary": "회사 내규에 따름",
        "close_date": "2026-08-05",
        "job_type": "정규직 (신입)",
        "job_cont": "- 카카오 공통 플랫폼 및 신규 서비스 백엔드/프론트엔드 개발",
        "pref_cond": "자료구조, 알고리즘, 네트워크, OS 기초 지식이 탄탄한 인재"
    }
]

def fetch_recruitment_list() -> list:
    """
    Fetches open recruitment listings from GoYong24 (210L21.do) API.
    It scrapes multiple pages to collect all listings and caches them in SQLite.
    If the API call fails, it falls back to existing cached listings, or Mock data if empty.
    """
    auth_key = os.getenv("GOYONG24_API_KEY")
    if not auth_key or auth_key.strip() == "" or auth_key == "your_api_key_here":
        print("[GoYong24 API] GOYONG24_API_KEY is not set. Returning cached or mock listings.")
        cached = get_cached_recruitments()
        return cached if cached else MOCK_RECRUITMENTS

    list_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    scraped_items = []
    page = 1
    display_limit = 100
    
    print(f"[GoYong24 API] Starting scrape from GoYong24 API...")

    try:
        while True:
            list_params = {
                "authKey": auth_key,
                "callTp": "L",
                "returnType": "XML",
                "startPage": str(page),
                "display": str(display_limit)
            }
            
            response = requests.get(list_url, params=list_params, headers=headers, timeout=15)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            
            # Check for GoYong24 error code
            message_cd = root.findtext('.//messageCd')
            if message_cd and message_cd != "000" and message_cd != "success" and message_cd != "00":
                message = root.findtext('.//message') or "Unknown error"
                print(f"[GoYong24 API Error] Code: {message_cd}, Message: {message}")
                break
                
            items = root.findall('.//dhsOpenEmpInfo')
            if not items:
                break
                
            for wanted in items:
                emp_seqno = wanted.findtext("empSeqno", "").strip()
                company = wanted.findtext("empBusiNm", "").strip()
                title = wanted.findtext("empWantedTitle", "").strip()
                job_type = wanted.findtext("empWantedTypeNm", "").strip()
                close_date = wanted.findtext("empWantedEndt", "").strip()
                
                # Format dates nicely (e.g. 20260630 -> 2026-06-30)
                if len(close_date) == 8:
                    close_date = f"{close_date[:4]}-{close_date[4:6]}-{close_date[6:]}"
                
                if emp_seqno and company and title:
                    scraped_items.append({
                        "emp_seqno": emp_seqno,
                        "company": company,
                        "title": title,
                        "salary": "상세정보 참조",
                        "close_date": close_date or "채용 시 마감",
                        "job_type": job_type or "정규직"
                    })
            
            total_str = root.findtext('total')
            total = int(total_str) if total_str and total_str.isdigit() else len(scraped_items)
            
            print(f"[GoYong24 API] Scraped page {page}. Total elements collected so far: {len(scraped_items)}/{total}")
            
            # Break if we have fetched all items, or if we got fewer items than display limit (meaning last page)
            if len(items) < display_limit or len(scraped_items) >= total or page >= 10:
                break
                
            page += 1
            
        if scraped_items:
            # Save scraped listings to cache DB
            save_cached_recruitments(scraped_items)
            print(f"[GoYong24 API] Successfully cached {len(scraped_items)} listings.")
            return get_cached_recruitments()
        else:
            print("[GoYong24 API] Scrape returned 0 items. Returning existing cache.")
            cached = get_cached_recruitments()
            return cached if cached else MOCK_RECRUITMENTS

    except Exception as e:
        print(f"[GoYong24 API Exception] {str(e)}. Returning cached database or mock listings.")
        cached = get_cached_recruitments()
        return cached if cached else MOCK_RECRUITMENTS


def fetch_recruitment_detail(emp_seqno: str) -> dict:
    """
    Fetches job details and preference requirements for a specific recruitment (210D21.do)
    and caches them in SQLite. Returns the updated recruitment dictionary.
    """
    # If it is a mock sequence, return mock details immediately
    if emp_seqno.startswith("mock_"):
        for mock in MOCK_RECRUITMENTS:
            if mock["emp_seqno"] == emp_seqno:
                return mock
        return {}

    # Check database first to see if details are already cached
    cached = get_cached_recruitment(emp_seqno)
    if cached and cached.get("job_cont") and cached.get("pref_cond"):
        print(f"[GoYong24 API] Returning cached details for {emp_seqno}")
        return cached

    auth_key = os.getenv("GOYONG24_API_KEY")
    if not auth_key or auth_key.strip() == "" or auth_key == "your_api_key_here":
        print("[GoYong24 API] GOYONG24_API_KEY not found. Cannot fetch detail.")
        return cached or {}

    detail_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210D21.do"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    detail_params = {
        "authKey": auth_key,
        "callTp": "D",
        "returnType": "XML",
        "empSeqno": emp_seqno
    }

    try:
        print(f"[GoYong24 API] Fetching details online for {emp_seqno}...")
        response = requests.get(detail_url, params=detail_params, headers=headers, timeout=15)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        # Check Error Code
        message_cd = root.findtext('.//messageCd')
        if message_cd and message_cd != "000" and message_cd != "success" and message_cd != "00":
            message = root.findtext('.//message') or "Unknown error"
            print(f"[GoYong24 API Detail Error] Code: {message_cd}, Message: {message}")
            return cached or {}

        # Parse recruitment divisions
        roles = []
        for info in root.findall(".//empRecrListInfo"):
            rec_nm = info.findtext("empRecrNm", "").strip()
            job_c = info.findtext("jobCont", "").strip()
            career = info.findtext("empWantedCareerNm", "").strip()
            edu = info.findtext("empWantedEduNm", "").strip()
            cert = info.findtext("sptCertEtc", "").strip()
            
            role_text = f"■ 모집분야: {rec_nm}"
            if career or edu:
                role_text += f" ({career} / {edu})"
            if job_c:
                role_text += f"\n- 직무내용:\n{job_c}"
            if cert:
                role_text += f"\n- 우대/자격요건:\n{cert}"
            roles.append(role_text)

        job_cont_full = "\n\n".join(roles)

        # Parse preferences and common contents
        pref_cond_full = ""
        comm_cont = root.findtext(".//recrCommCont", "").strip()
        etc_cont = root.findtext(".//empnEtcCont", "").strip()
        if comm_cont:
            pref_cond_full += f"■ 공통 자격요건:\n{comm_cont}\n\n"
        if etc_cont:
            pref_cond_full += f"■ 기타 유의사항:\n{etc_cont}"
        pref_cond_full = pref_cond_full.strip()

        # Update cache in SQLite
        update_recruitment_detail(emp_seqno, job_cont_full, pref_cond_full)
        print(f"[GoYong24 API] Successfully cached details for {emp_seqno}.")

        # Retrieve updated record
        return get_cached_recruitment(emp_seqno)

    except Exception as e:
        print(f"[GoYong24 API Detail Exception] {str(e)}")
        return cached or {}
