import requests

print("--- AI JOB RECOMMENDATION SYSTEM INTEGRATION TEST ---")

# Step 1: Create session
session_res = requests.post("http://127.0.0.1:8000/api/sessions", json={
    "company": "임시회사",
    "job_title": "임시직무"
})
print("Session created:", session_res.json())
session_id = session_res.json()["id"]

# Step 2: Save experience (Computer Science / React Developer profile)
exp_res = requests.post(f"http://127.0.0.1:8000/api/sessions/{session_id}/experience", data={
    "raw_content": "저는 컴퓨터공학과를 전공했으며 React와 Spring Boot를 사용한 웹 풀스택 개발 경험이 있습니다. 특히 가상의 크라우드펀딩 플랫폼을 설계하여 페이지 로딩 성능을 30% 개선시켰습니다."
})
print("Experience saved:", exp_res.json()["status"])

# Step 3: Call recommendation endpoint
rec_res = requests.post(f"http://127.0.0.1:8000/api/sessions/{session_id}/recommend-jobs")
print("Recommendation status code:", rec_res.status_code)
data = rec_res.json()
print("Total matching count:", data.get("total_matching_count"))
print("Recommendations:")
for i, rec in enumerate(data.get("recommendations", [])):
    print(f"\n[{i+1}] {rec['company']} - {rec['title']} ({rec['job_type']})")
    print(f"    Reason: {rec['reason']}")
    
# Clean up session
del_res = requests.delete(f"http://127.0.0.1:8000/api/sessions/{session_id}")
print("\nSession deleted for cleanup:", del_res.json()["status"])
