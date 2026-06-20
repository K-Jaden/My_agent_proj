import os
import requests
import xml.etree.ElementTree as ET
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_work24_agent_pipeline():
    # Read key from .env
    auth_key = os.getenv("GOYONG24_API_KEY")
    if not auth_key:
        print("Error: GOYONG24_API_KEY is not set in .env")
        return
        
    print("==================================================")
    print("[Agent Run] Real-time Open Recruitment Scan")
    print("==================================================\n")

    # Standard User-Agent header to prevent HTTP 500 errors
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    # ---------------------------------------------------------
    # [Step 1] List API (210L21.do)
    # ---------------------------------------------------------
    print("-> [Step 1] Fetching open recruitment list...")
    
    list_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"
    list_params = {
        "authKey": auth_key,
        "callTp": "L",
        "returnType": "XML",
        "startPage": "1",
        "display": "5"  
    }
    
    try:
        res_list = requests.get(list_url, params=list_params, headers=headers, timeout=10)
        res_list.raise_for_status()
        
        root_list = ET.fromstring(res_list.content)
        
        # Check Error Code
        message_cd = root_list.findtext('.//messageCd')
        if message_cd and message_cd != "000" and message_cd != "success":
            print(f"Error Code: {message_cd}, Content: {root_list.findtext('.//message')}")
            return
            
        first_item = root_list.find('.//dhsOpenEmpInfo')
        
        if first_item is None:
            print("Error: No job announcements found in listing XML. Raw output:")
            print(res_list.text[:500])
            return
            
        emp_seqno = first_item.findtext('empSeqno')
        co_nm = first_item.findtext('empBusiNm') or "No Company Name"
        title = first_item.findtext('empWantedTitle') or "No Title"
        
        if not emp_seqno:
            print("Error: empSeqno not found.")
            return

        print(f"List Fetch Successful: Target Company = {co_nm}")
        print(f"   - Title: {title}")
        print(f"   - empSeqno: {emp_seqno}\n")
        
    except Exception as e:
        print(f"Error in Step 1: {e}")
        if 'res_list' in locals():
            print("Raw Response:")
            print(res_list.text[:1000])
        return

    time.sleep(1)

    # ---------------------------------------------------------
    # [Step 2] Detail API (210D21.do)
    # ---------------------------------------------------------
    print(f"-> [Step 2] Fetching job details for empSeqno [{emp_seqno}]...")
    
    detail_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210D21.do"
    detail_params = {
        "authKey": auth_key,
        "callTp": "D",
        "returnType": "XML",
        "empSeqno": emp_seqno
    }
    
    try:
        res_detail = requests.get(detail_url, params=detail_params, headers=headers, timeout=10)
        res_detail.raise_for_status()
        
        root_detail = ET.fromstring(res_detail.content)
        
        msg_code = root_detail.findtext('.//messageCd')
        if msg_code and msg_code != "000" and msg_code != "success" and msg_code != "00":
            print(f"Error: Detail API failed with Code {msg_code}")
            print(f"Reason: {root_detail.findtext('.//message')}")
            return

        print("Detail Fetch Successful!\n")
        
        print("==================================================")
        print("Agent Context Data")
        print("==================================================")
        
        detail_corp_nm = root_detail.findtext('.//corpNm') or co_nm
        detail_title = root_detail.findtext('.//recruitTitle') or title
        
        # Work24 Detail Fields: jobCont, prefCond, etc.
        job_cont = root_detail.findtext('.//jobCont') or "No job details."
        pref_cond = root_detail.findtext('.//prefCond') or "No preferences listed." 
        
        print(f"Company: {detail_corp_nm}")
        print(f"Title: {detail_title}")
        print(f"\n[Preferences]\n{pref_cond}")
        print(f"\n[Job Details]\n{job_cont[:500]}") 
        
        if len(job_cont) > 500:
            print("\n... (truncated)")
            
    except Exception as e:
        print(f"Error in Step 2: {e}")
        if 'res_detail' in locals():
            print("Raw Detail Response:")
            print(res_detail.text[:1000])

if __name__ == "__main__":
    run_work24_agent_pipeline()