# 자소서.AI (My Self-Introduction Agent)

사용자가 입력한 경험이나 이력서 파일을 기반으로 채용 공고와 문항에 맞춰 자소서를 설계, 작성, 평가, 첨삭해 주는 **올인원 AI 자소서 에이전트** 웹 애플리케이션입니다.

---

## 🛠️ 기술 스택 (Tech Stack)

- **Backend**: FastAPI (Python)
- **Agent Workflow**: LangGraph / LangChain
- **LLM**: Gemini API (`gemini-1.5-flash` / `ChatGoogleGenerativeAI`)
- **Database**: SQLite3
- **Frontend**: Single Page Application (HTML5, JavaScript ES6, Glassmorphism CSS)
- **Dependencies**: `pypdf` (이력서 PDF 파싱용)

---

## 📂 프로젝트 폴더 구조 (Folder Structure)

```
c:\Users\SAMSUNG\Anti\Myagent\My_agent_proj\
├── app/
│   ├── __init__.py
│   ├── main.py            # FastAPI 애플리케이션 메인 엔드포인트
│   ├── database.py        # SQLite 데이터베이스 스키마 및 쿼리 제어
│   ├── agent/             # LangGraph AI 에이전트 핵심 로직
│   │   ├── __init__.py
│   │   ├── state.py       # 에이전트 상태 정의 (AgentState)
│   │   ├── prompts.py     # STAR 구조화, 문항 분석, 초안 작성, 첨삭용 프롬프트
│   │   ├── nodes.py       # Gemini API 호출 노드 함수
│   │   └── graph.py       # LangGraph 워크플로우 구성 및 컴파일
│   ├── templates/         # HTML 뷰 템플릿
│   │   └── index.html     # SPA 웹 인터페이스
│   └── static/            # CSS, JS 정적 파일
│       ├── css/
│       │   └── style.css  # 프리미엄 글래스모피즘 CSS 스타일시트
│       └── js/
│           └── app.js     # 드래그앤드롭 파일 업로드, 비동기 API 통신, SPA 뷰 제어
├── uploads/               # 이력서 임시 파일 업로드 디렉토리
├── .env                   # 환경변수 설정 파일 (GEMINI_API_KEY 입력 필요)
├── .env.template          # 환경변수 템플릿
├── requirements.txt      # 파이썬 라이브러리 의존성 파일
└── README.md
```

---

## 🚀 시작 가이드 (Quick Start)

### 1. 의존성 패키지 설치
터미널을 열고 다음 명령어를 실행하여 필수 라이브러리를 설치합니다.
```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정
프로젝트 루트 폴더에 `.env` 파일을 생성하고 본인의 **Gemini API Key**를 입력합니다.
```env
GEMINI_API_KEY=your_actual_gemini_api_key
PORT=8000
HOST=127.0.0.1
```
> [!NOTE]
> Gemini API Key가 유효해야 AI 에이전트 기능이 정상 동작합니다.

### 3. 애플리케이션 실행
FastAPI 개발 서버를 기동합니다.
```bash
uvicorn app.main:app --reload
```

### 4. 웹 브라우저 접속
서버 기동 후 브라우저에서 다음 주소로 접속합니다.
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 💡 주요 에이전트 워크플로우 (4단계)

1. **Step 1: 경험 정리 및 STAR 구조화**
   - 텍스트를 기입하거나 이력서 파일(PDF, TXT, MD)을 업로드하면 AI가 STAR 구조(Situation, Task, Action, Result) 및 핵심 역량 요약본으로 재구성합니다.
2. **Step 2: 채용공고 & 문항 분석**
   - 가려는 회사/직무 공고 정보와 자소서 질문 문항을 분석하여 본질적인 출제 의도, 필요 역량 키워드, 추천 단어, 작성 팁 리포트를 뽑아냅니다.
3. **Step 3: 맞춤형 초안 자동 작성**
   - 1단계의 STAR 구조화 경험과 2단계의 작성 전략을 바탕으로 글자 수 제한을 엄격히 준수한 매력적인 초안 자소서를 만들어냅니다.
4. **Step 4: AI 수석평가관 심층 첨삭 및 개선안 비교**
   - 가독성, 논리성, 직무적합도 항목의 백분율 점수를 메기고, 구체적인 수정 피드백 코멘트를 줍니다. 오리지널 초안과 완성형 개선안을 **Side-by-Side 뷰**로 확인하여 원클릭으로 개선안을 최종 채택할 수 있습니다.
