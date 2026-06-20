import os
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

auth_key = os.getenv("GOYONG24_API_KEY")
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

print("--- LIST API ---")
list_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210L21.do"
list_params = {
    "authKey": auth_key,
    "callTp": "L",
    "returnType": "XML",
    "startPage": "1",
    "display": "2"
}

res = requests.get(list_url, params=list_params, headers=headers)
print("Status:", res.status_code)
root = ET.fromstring(res.content)
item = root.find('.//dhsOpenEmpInfo')
if item is not None:
    for child in item:
        print(f"Tag: {child.tag}, Text: {child.text}")
else:
    print("No items found.")
    print(res.text[:1000])

print("--- DETAIL API ---")
if item is not None:
    emp_seqno = item.findtext('empSeqno')
    detail_url = "https://www.work24.go.kr/cm/openApi/call/wk/callOpenApiSvcInfo210D21.do"
    detail_params = {
        "authKey": auth_key,
        "callTp": "D",
        "returnType": "XML",
        "empSeqno": emp_seqno
    }
    res_det = requests.get(detail_url, params=detail_params, headers=headers)
    root_det = ET.fromstring(res_det.content)
    # Print first few elements or all tags inside target element
    # Usually Work24 detail elements are directly under the root or in a specific parent
    for child in root_det.iter():
        print(f"Detail Tag: {child.tag}, Text: {str(child.text)[:100] if child.text else ''}")
