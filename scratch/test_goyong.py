import os
import sys

# Add app to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.database import init_db, get_cached_recruitments
from app.goyong_api import fetch_recruitment_list, fetch_recruitment_detail

print("Initializing DB...")
init_db()

print("\n--- Test fetching recruitment list ---")
lst = fetch_recruitment_list()
print(f"Total listings fetched and returned: {len(lst)}")

if lst:
    first_item = lst[0]
    print(f"First item: {first_item}")
    
    emp_seqno = first_item['emp_seqno']
    print(f"\n--- Test fetching details for emp_seqno: {emp_seqno} ---")
    detail = fetch_recruitment_detail(emp_seqno)
    print("Detail fetched keys:", detail.keys())
    print("Detail Title:", detail.get('title'))
    print("Detail Job Cont (truncated):")
    print(str(detail.get('job_cont'))[:300])
    print("Detail Pref Cond (truncated):")
    print(str(detail.get('pref_cond'))[:300])
else:
    print("No items to test detail fetching.")
