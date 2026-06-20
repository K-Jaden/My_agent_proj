// State Variables
let currentSessionId = null;
let currentQuestionId = null;
let currentStep = 1;
let currentTurn = 1;

// DOM Elements
const welcomeScreen = document.getElementById('welcome-screen');
const agentPanel = document.getElementById('agent-panel');
const sessionList = document.getElementById('session-list');
const btnNewSession = document.getElementById('btn-new-session');
const newSessionForm = document.getElementById('new-session-form');
const companyInput = document.getElementById('company-input');
const jobInput = document.getElementById('job-input');
const activeSessionTitle = document.getElementById('active-session-title');
const btnDeleteActiveSession = document.getElementById('btn-delete-active-session');
const apiStatusText = document.getElementById('api-status-text');
const apiStatusDot = document.querySelector('.api-key-indicator .indicator-dot');

// Stepper Elements
const steps = document.querySelectorAll('.step');

// Loading Overlay
const loadingOverlay = document.getElementById('loading-overlay');
const loadingText = document.getElementById('loading-text');
const loadingProgress = document.getElementById('loading-progress');

// Toast
const toast = document.getElementById('toast');

/* --- Page Startup --- */
document.addEventListener('DOMContentLoaded', () => {
    loadSessions();
    checkApiStatus();
    setupEventListeners();
    loadRecruitments(); // Load open recruitment postings on start
});

function showToast(message, duration = 3000) {
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => {
        toast.classList.remove('show');
    }, duration);
}

function showLoading(text, progress = 15) {
    loadingText.textContent = text;
    loadingProgress.style.width = `${progress}%`;
    loadingOverlay.classList.remove('d-none');
}

function hideLoading() {
    loadingOverlay.classList.add('d-none');
}

/* --- API Key Check --- */
async function checkApiStatus() {
    apiStatusDot.classList.add('active');
    apiStatusText.textContent = "Gemini & Naver API 준비 완료";
}

/* --- Load Recruitments List --- */
async function loadRecruitments() {
    const tbody = document.getElementById('goyong-tbody');
    tbody.innerHTML = '<tr><td colspan="5" class="text-center">공채 목록을 불러오는 중...</td></tr>';
    
    try {
        const res = await fetch('/api/goyong/recruitments');
        const data = await res.json();
        
        tbody.innerHTML = '';
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center">진행 중인 공채 공고가 없습니다.</td></tr>';
            return;
        }
        
        data.forEach(item => {
            const tr = document.createElement('tr');
            tr.setAttribute('data-seqno', item.emp_seqno);
            tr.innerHTML = `
                <td><strong>${item.company}</strong></td>
                <td class="text-accent">${item.title}</td>
                <td>${item.job_type}</td>
                <td>${item.salary}</td>
                <td>${item.close_date}</td>
            `;
            
            tr.addEventListener('click', () => {
                selectRecruitmentRow(item.emp_seqno, item.company, item.title, item.job_type);
            });
            
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error(e);
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-danger">공채 목록 로드 실패 (Mock 데이터로 우회해 주세요)</td></tr>';
    }
}

/* --- Select Recruitment helper --- */
function selectRecruitmentRow(empSeqno, company, title, jobType) {
    const rows = document.querySelectorAll('#goyong-tbody tr');
    rows.forEach(tr => {
        if (tr.getAttribute('data-seqno') === empSeqno) {
            document.querySelectorAll('.goyong-table tbody tr').forEach(el => el.classList.remove('selected'));
            tr.classList.add('selected');
            tr.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
    
    document.getElementById('company-search-input').value = company;
    document.getElementById('job-title-input').value = jobType.includes("개발") || title.includes("S/W") ? "S/W 개발자" : "서비스 기획자";
    document.getElementById('question-input').value = "지원 직무에 대한 본인의 역량과, 우리 기업의 인재상에 어떻게 부합하는지 관련 경험을 토대로 서술해 주십시오.";
    
    showToast(`${company} 공고가 선택되었습니다.`);
    triggerCompanyAnalysis(company, empSeqno);
}

/* --- Load AI Recommended Jobs --- */
async function loadRecommendedJobs(sessionId) {
    const container = document.getElementById('ai-recommendation-container');
    const cardsContainer = document.getElementById('recommendation-cards-container');
    const badge = document.getElementById('matching-count-badge');
    
    if (!sessionId) return;
    
    // Show cardsContainer loading state
    cardsContainer.innerHTML = '<div style="grid-column: 1/-1; text-align: center; font-size: 13px; color: var(--text-secondary); padding: 20px;">AI가 이력서에 어울리는 맞춤 공채 공고를 분석 중입니다...</div>';
    container.classList.remove('d-none');
    
    try {
        const res = await fetch(`/api/sessions/${sessionId}/recommend-jobs`, { method: 'POST' });
        const data = await res.json();
        
        if (res.ok && data.recommendations && data.recommendations.length > 0) {
            badge.textContent = `회원님과 어울리는 공고: ${data.total_matching_count}개`;
            
            cardsContainer.innerHTML = '';
            data.recommendations.forEach(rec => {
                const card = document.createElement('div');
                card.className = 'rec-job-card';
                card.innerHTML = `
                    <div class="rec-job-card-header">
                        <span class="rec-company-tag" title="${rec.company}">${rec.company}</span>
                        <span class="rec-job-type">${rec.job_type}</span>
                    </div>
                    <div class="rec-job-title" title="${rec.title}">${rec.title}</div>
                    <div class="rec-reason">${rec.reason}</div>
                `;
                
                card.addEventListener('click', () => {
                    selectRecruitmentRow(rec.emp_seqno, rec.company, rec.title, rec.job_type);
                });
                
                cardsContainer.appendChild(card);
            });
        } else {
            container.classList.add('d-none');
        }
    } catch (e) {
        console.error("[loadRecommendedJobs Error]", e);
        container.classList.add('d-none');
    }
}

/* --- Trigger NAVER Analysis --- */
async function triggerCompanyAnalysis(companyName, empSeqno = null) {
    const emptyState = document.getElementById('analysis-empty');
    const contentDiv = document.getElementById('analysis-result-content');
    
    showLoading(`${companyName}의 최신 트렌드 및 인재상을 네이버 검색기반 분석 중...`, 40);
    try {
        const formData = new FormData();
        formData.append("company_name", companyName);
        if (empSeqno) {
            formData.append("emp_seqno", empSeqno);
        }
        
        const res = await fetch(`/api/sessions/${currentSessionId}/analyze-company`, {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        
        if (res.ok) {
            renderCompanyInsights(data.company_insights);
            showToast(`${companyName}의 정보 분석이 연동되었습니다!`);
            // Reload session details to fetch and render recruitment details on the sidebar
            if (empSeqno) {
                await loadSessionDetails(currentSessionId);
            }
        } else {
            showToast("기업 정보 수집 실패");
        }
    } catch (e) {
        showToast("네트워크 오류");
    } finally {
        hideLoading();
    }
}

/* --- Event Listeners --- */
function setupEventListeners() {
    // New Session
    btnNewSession.addEventListener('click', () => {
        welcomeScreen.classList.remove('d-none');
        agentPanel.classList.add('d-none');
        currentSessionId = null;
        currentQuestionId = null;
        document.querySelectorAll('.session-item').forEach(el => el.classList.remove('active'));
    });

    // Submit new session
    newSessionForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const company = companyInput.value.trim();
        const job = jobInput.value.trim();
        
        showLoading("새 자소서 작성 세션을 만드는 중...", 20);
        try {
            const res = await fetch('/api/sessions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ company, job_title: job })
            });
            const data = await res.json();
            currentSessionId = data.id;
            
            companyInput.value = '';
            jobInput.value = '';
            
            await loadSessions();
            await loadSessionDetails(currentSessionId);
            
            welcomeScreen.classList.add('d-none');
            agentPanel.classList.remove('d-none');
            showToast("세션 생성 완료! 이력서를 먼저 등록해 주세요.");
        } catch (error) {
            showToast("세션 생성 실패");
        } finally {
            hideLoading();
        }
    });

    // Delete Session
    btnDeleteActiveSession.addEventListener('click', async () => {
        if (!currentSessionId) return;
        if (confirm("정말 이 자소서 작성 세션을 완전히 삭제하시겠습니까? 데이터가 유실됩니다.")) {
            try {
                await fetch(`/api/sessions/${currentSessionId}`, { method: 'DELETE' });
                showToast("세션이 삭제되었습니다.");
                currentSessionId = null;
                currentQuestionId = null;
                await loadSessions();
                welcomeScreen.classList.remove('d-none');
                agentPanel.classList.add('d-none');
            } catch (error) {
                showToast("삭제 실패");
            }
        }
    });

    // File drop
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const fileInfoContainer = document.getElementById('file-info-container');
    const fileNameText = document.getElementById('file-name');
    const btnRemoveFile = document.getElementById('btn-remove-file');

    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    btnRemoveFile.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.value = '';
        fileInfoContainer.classList.add('d-none');
    });

    function handleFileSelection(file) {
        const allowedExtensions = ['.pdf', '.txt', '.md'];
        const name = file.name;
        const ext = name.substring(name.lastIndexOf('.')).toLowerCase();
        
        if (!allowedExtensions.includes(ext)) {
            showToast("지원하지 않는 파일 형식입니다. (.pdf, .txt, .md만 가능)");
            fileInput.value = '';
            return;
        }
        
        fileNameText.innerHTML = `<i class="fa-solid fa-file-invoice"></i> ${name}`;
        fileInfoContainer.classList.remove('d-none');
        showToast("파일이 준비되었습니다.");
    }

    // Save Resume Experience (Step 1)
    const experienceForm = document.getElementById('experience-form');
    const rawExperienceInput = document.getElementById('raw-experience-input');
    
    experienceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const rawContent = rawExperienceInput.value.trim();
        const hasFile = fileInput.files.length > 0;
        
        if (!rawContent && !hasFile) {
            showToast("이력서 본문을 입력하거나 파일을 업로드해 주세요.");
            return;
        }

        showLoading("이력서 정보를 등록하고 저장하는 중...", 50);
        try {
            const formData = new FormData();
            if (rawContent) formData.append("raw_content", rawContent);
            if (hasFile) formData.append("file", fileInput.files[0]);
            
            const res = await fetch(`/api/sessions/${currentSessionId}/experience`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                rawExperienceInput.value = data.raw_content;
                steps[0].classList.add('completed');
                showToast("이력서 정보가 성공적으로 등록되었습니다!");
                navigateToStep(2);
            } else {
                showToast("이력서 등록 실패");
            }
        } catch (error) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    });

    // Custom Naver Analysis button click
    const btnSearchCompany = document.getElementById('btn-search-company');
    btnSearchCompany.addEventListener('click', () => {
        const companyName = document.getElementById('company-search-input').value.trim();
        if (!companyName) {
            showToast("검색할 기업명을 적어주세요.");
            return;
        }
        triggerCompanyAnalysis(companyName);
    });

    // Submit JD & Question (Step 2)
    const analysisForm = document.getElementById('analysis-form');
    const questionInput = document.getElementById('question-input');
    const maxCharsInput = document.getElementById('max-chars-input');

    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        showLoading("채용 문항 및 제한 자수를 분석하는 중...", 40);
        try {
            const formData = new FormData();
            formData.append("question_text", questionInput.value.trim());
            formData.append("max_chars", maxCharsInput.value);
            
            const res = await fetch(`/api/sessions/${currentSessionId}/step2_analyze`, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                currentQuestionId = data.question_id;
                steps[1].classList.add('completed');
                showToast("공고 매칭 분석이 완료되었습니다. AI 면접을 시작합니다!");
                
                // Clear chat bubbles and initiate interview
                document.getElementById('chat-messages-container').innerHTML = '';
                navigateToStep(3);
                
                // Initiate first interview question
                fetchNextInterviewQuestion();
            } else {
                showToast("분석 실패");
            }
        } catch (error) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    });

    // Submit Interview Answer (Step 3)
    const chatInputForm = document.getElementById('chat-input-form');
    const chatAnswerInput = document.getElementById('chat-answer-input');

    chatInputForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const answer = chatAnswerInput.value.trim();
        if (!answer) return;
        
        // Append user chat bubble
        appendChatBubble(answer, 'user');
        chatAnswerInput.value = '';
        chatAnswerInput.disabled = true;
        document.getElementById('btn-submit-answer').disabled = true;
        
        showLoading("답변을 분석하여 다음 유도 질문을 구상하고 있습니다...", 40);
        try {
            const formData = new FormData();
            formData.append("turn_num", currentTurn);
            formData.append("answer", answer);
            
            const res = await fetch(`/api/sessions/${currentSessionId}/interview/submit-answer`, {
                method: 'POST',
                body: formData
            });
            
            if (res.ok) {
                // Fetch next turn
                await fetchNextInterviewQuestion();
            } else {
                showToast("답변 전송에 실패했습니다.");
                chatAnswerInput.disabled = false;
                document.getElementById('btn-submit-answer').disabled = false;
            }
        } catch (e) {
            showToast("네트워크 오류");
            chatAnswerInput.disabled = false;
            document.getElementById('btn-submit-answer').disabled = false;
        } finally {
            hideLoading();
        }
    });

    // Step 4 Generate Draft
    const btnGenerateDraft = document.getElementById('btn-generate-draft');
    const btnRegenerateDraft = document.getElementById('btn-regenerate-draft');
    const draftTextarea = document.getElementById('draft-textarea');
    const btnCopyDraft = document.getElementById('btn-copy-draft');
    const draftCharCounter = document.getElementById('draft-char-counter');

    async function triggerDraftGeneration() {
        if (!currentQuestionId) {
            showToast("질문 세션이 없습니다.");
            return;
        }
        
        showLoading("면접 답변들을 종합하여 가장 매끄럽고 설득력 있는 자소서를 합성하는 중...", 50);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/step3_draft`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                renderDraft(data.draft);
                showToast("AI 자소서가 완성되었습니다!");
            } else {
                showToast(data.detail || "생성 실패. 3번의 답변을 모두 제출하셔야 합니다.");
            }
        } catch (e) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    }

    btnGenerateDraft.addEventListener('click', triggerDraftGeneration);
    btnRegenerateDraft.addEventListener('click', triggerDraftGeneration);

    btnCopyDraft.addEventListener('click', () => {
        draftTextarea.select();
        document.execCommand('copy');
        showToast("클립보드에 자소서가 복사되었습니다!");
    });

    document.getElementById('btn-next-to-step5').addEventListener('click', () => {
        navigateToStep(5);
        triggerReview();
    });

    // Step 5 Review & Feedback
    const btnReviewAgain = document.getElementById('btn-review-again');
    const btnApplyRefined = document.getElementById('btn-apply-refined');

    async function triggerReview() {
        if (!currentQuestionId) return;
        
        showLoading("글자 수 제한 준수 및 가독성/논리성 정밀 첨삭 평가를 진행하는 중...", 65);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/step4_review`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                renderReviewResult(data.refined_draft, data.feedback);
                showToast("첨삭 개선서 발급 완료!");
            } else {
                showToast(data.detail || "첨삭 실패");
            }
        } catch (e) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    }

    btnReviewAgain.addEventListener('click', triggerReview);

    btnApplyRefined.addEventListener('click', async () => {
        if (!currentQuestionId) return;
        
        showLoading("최종 합격 개선안을 작성본에 덮어쓰기 하는 중...", 80);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/apply_refined`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                draftTextarea.value = data.draft_content;
                draftCharCounter.textContent = `${data.draft_content.length}자 / ${maxCharsInput.value}자`;
                showToast("개선안이 초안에 성공적으로 적용되었습니다!");
                navigateToStep(4);
            } else {
                showToast("적용 실패");
            }
        } catch (error) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    });

    // Navigation clicks
    steps.forEach(step => {
        step.addEventListener('click', () => {
            const stepNum = parseInt(step.getAttribute('data-step'));
            if (isStepAccessible(stepNum)) {
                navigateToStep(stepNum);
            } else {
                showToast("이전 필수 단계를 먼저 이행해 주세요.");
            }
        });
    });
}

function isStepAccessible(stepNum) {
    if (stepNum === 1) return true;
    if (stepNum === 2) {
        // Resume registered
        return steps[0].classList.contains('completed') || document.getElementById('raw-experience-input').value.trim().length > 0;
    }
    if (stepNum === 3) {
        // Question analyzed
        return currentQuestionId !== null;
    }
    if (stepNum === 4) {
        // Interview complete (at least 3 turns in DB)
        return currentQuestionId !== null; // Allow viewing compilation page
    }
    if (stepNum === 5) {
        // Draft created
        const draftText = document.getElementById('draft-textarea').value;
        return draftText.trim().length > 0;
    }
    return false;
}

/* --- Interview Chat Manager --- */
async function fetchNextInterviewQuestion() {
    const container = document.getElementById('chat-messages-container');
    const hintContainer = document.getElementById('chat-hint-container');
    const hintText = document.getElementById('chat-hint-text');
    const chatProgress = document.getElementById('chat-progress-text');
    const input = document.getElementById('chat-answer-input');
    const submitBtn = document.getElementById('btn-submit-answer');
    
    try {
        const res = await fetch(`/api/sessions/${currentSessionId}/interview/next`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'completed') {
            appendChatBubble("면접 꼬리 질문 3단계가 모두 마쳤습니다! 이제 아래 버튼을 누르거나 다음 단계로 가 자소서를 완성해 보세요.", 'ai');
            hintContainer.classList.add('d-none');
            chatProgress.textContent = "가이드 면접 종료 (3/3 답변)";
            
            // Allow submission or navigation
            input.disabled = true;
            submitBtn.disabled = true;
            steps[2].classList.add('completed');
            
            setTimeout(() => {
                showToast("질의응답이 끝나 4단계 자소서 완성 페이지로 이동합니다!");
                navigateToStep(4);
            }, 1500);
            return;
        }
        
        currentTurn = data.turn;
        chatProgress.textContent = `면접 질문 ${currentTurn} / 3 진행 중`;
        
        // Append AI question
        appendChatBubble(data.question, 'ai');
        
        // Show hint
        if (data.hint) {
            hintText.textContent = data.hint;
            hintContainer.classList.remove('d-none');
        } else {
            hintContainer.classList.add('d-none');
        }
        
        // Enable input
        input.disabled = false;
        submitBtn.disabled = false;
        input.focus();
        
    } catch (e) {
        showToast("다음 면접 질문 로딩에 실패했습니다.");
    }
}

function appendChatBubble(text, sender) {
    const container = document.getElementById('chat-messages-container');
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble ${sender}`;
    bubble.textContent = text;
    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

/* --- Rendering Helpers --- */

function renderCompanyInsights(insights) {
    const emptyState = document.getElementById('analysis-empty');
    const contentDiv = document.getElementById('analysis-result-content');
    
    if (insights) {
        emptyState.classList.add('d-none');
        contentDiv.classList.remove('d-none');
        
        document.getElementById('company-values-text').textContent = insights.values || "기본 가치관 정보 없음";
        document.getElementById('company-talent-text').textContent = insights.talent_profile || "인재상 정보 없음";
        document.getElementById('company-recommendation-text').textContent = insights.recommendations || "추천 정보 없음";
        
        const newsList = document.getElementById('company-news-list');
        newsList.innerHTML = (insights.news_topics || []).map(topic => `<li>${topic}</li>`).join('');
    } else {
        emptyState.classList.remove('d-none');
        contentDiv.classList.add('d-none');
    }
}

function renderDraft(draftText) {
    const emptyState = document.getElementById('draft-empty');
    const contentDiv = document.getElementById('draft-result-content');
    
    if (draftText) {
        emptyState.classList.add('d-none');
        contentDiv.classList.remove('d-none');
        
        draftTextarea.value = draftText;
        const maxLimit = document.getElementById('max-chars-input').value;
        document.getElementById('draft-char-counter').textContent = `${draftText.length}자 / ${maxLimit}자`;
        steps[3].classList.add('completed');
    } else {
        emptyState.classList.remove('d-none');
        contentDiv.classList.add('d-none');
        draftTextarea.value = '';
        steps[3].classList.remove('completed');
    }
}

function renderReviewResult(refinedDraft, feedback) {
    const commentsCard = document.getElementById('feedback-comments-card');
    const commentsList = document.getElementById('feedback-comments-list');
    
    // Render scores
    const scores = feedback.scores || { readability: 70, logic: 70, job_fit: 70 };
    animateScoreRing('ring-readability', scores.readability);
    animateScoreRing('ring-logic', scores.logic);
    animateScoreRing('ring-job-fit', scores.job_fit);
    
    // Comments
    commentsCard.classList.remove('d-none');
    commentsList.innerHTML = (feedback.comments || []).map(c => `<li><i class="fa-solid fa-circle-exclamation"></i> ${c}</li>`).join('');
    
    // Comparison
    const originalBox = document.getElementById('original-comparison-box');
    const refinedBox = document.getElementById('refined-comparison-box');
    
    const originalText = draftTextarea.value;
    originalBox.textContent = originalText;
    refinedBox.textContent = refinedDraft;
    
    document.getElementById('original-char-counter').textContent = `${originalText.length}자`;
    document.getElementById('refined-char-counter').textContent = `${refinedDraft.length}자`;
    
    steps[4].classList.add('completed');
}

function animateScoreRing(elementId, targetScore) {
    const el = document.getElementById(elementId);
    let score = 0;
    const interval = setInterval(() => {
        if (score >= targetScore) {
            clearInterval(interval);
            el.textContent = `${targetScore}점`;
        } else {
            score++;
            el.textContent = `${score}점`;
        }
    }, 15);
}

/* --- Session Life Cycle --- */

async function loadSessions() {
    try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        
        sessionList.innerHTML = '';
        if (data.length === 0) {
            sessionList.innerHTML = '<li class="text-muted text-center" style="font-size:12px; padding:10px;">작성 기록이 없습니다</li>';
            return;
        }
        
        data.forEach(sess => {
            const li = document.createElement('li');
            li.className = `session-item ${sess.id === currentSessionId ? 'active' : ''}`;
            li.setAttribute('data-id', sess.id);
            
            li.innerHTML = `
                <div class="session-item-info">
                    <span class="session-item-company">${sess.company}</span>
                    <span class="session-item-job">${sess.job_title}</span>
                </div>
                <button class="btn-delete-session" onclick="event.stopPropagation(); deleteSession('${sess.id}')">
                    <i class="fa-solid fa-trash"></i>
                </button>
            `;
            
            li.addEventListener('click', () => {
                loadSessionDetails(sess.id);
            });
            
            sessionList.appendChild(li);
        });
    } catch (e) {
        console.error(e);
    }
}

async function loadSessionDetails(sessionId) {
    currentSessionId = sessionId;
    
    document.querySelectorAll('.session-item').forEach(el => {
        if (el.getAttribute('data-id') === sessionId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
    
    showLoading("에이전트 세션의 작성 과정을 로딩 중...", 20);
    try {
        const res = await fetch(`/api/sessions/${sessionId}`);
        const data = await res.json();
        
        activeSessionTitle.textContent = `${data.session.company} · ${data.session.job_title}`;
        
        // Reset steppers
        steps.forEach(s => s.classList.remove('completed', 'active'));
        
        // Load Step 1
        const rawExperienceInput = document.getElementById('raw-experience-input');
        if (data.experience) {
            rawExperienceInput.value = data.experience.raw_content || '';
            steps[0].classList.add('completed');
        } else {
            rawExperienceInput.value = '';
        }
        
        // Render Naver Insights
        if (data.company_insights) {
            renderCompanyInsights(data.company_insights);
            document.getElementById('company-search-input').value = data.session.company;
            document.getElementById('job-title-input').value = data.session.job_title;
        } else {
            renderCompanyInsights(null);
            document.getElementById('company-search-input').value = '';
            document.getElementById('job-title-input').value = '';
        }
        
        // Load Step 2 questions
        const questionInput = document.getElementById('question-input');
        const maxCharsInput = document.getElementById('max-chars-input');
        
        // Reset chat container
        const chatMessagesContainer = document.getElementById('chat-messages-container');
        chatMessagesContainer.innerHTML = '';
        
        if (data.questions && data.questions.length > 0) {
            const q = data.questions[0];
            currentQuestionId = q.id;
            
            questionInput.value = q.question_text || '';
            maxCharsInput.value = q.max_chars || 500;
            steps[1].classList.add('completed');
            
            // Draw Chat Logs from DB
            if (data.interview_logs && data.interview_logs.length > 0) {
                data.interview_logs.forEach(log => {
                    if (log.ai_question) appendChatBubble(log.ai_question, 'ai');
                    if (log.user_answer) appendChatBubble(log.user_answer, 'user');
                });
                
                const answeredLogs = data.interview_logs.filter(l => l.user_answer);
                if (answeredLogs.length === 3) {
                    steps[2].classList.add('completed');
                }
            }
            
            // Render compiled draft
            renderDraft(q.draft_content);
            
            // Render review feedback
            if (q.refined_draft && q.feedback_report) {
                renderReviewResult(q.refined_draft, {
                    scores: JSON.parse(q.feedback_report).scores || { readability: 85, logic: 85, job_fit: 85 },
                    comments: JSON.parse(q.feedback_report).comments || ["가독성이 뛰어납니다."]
                });
            }
        } else {
            currentQuestionId = null;
            questionInput.value = '';
            maxCharsInput.value = 500;
            renderDraft(null);
        }
        
        // Left guide update
        document.getElementById('chat-company-title').textContent = `${data.session.company} 요약 리포트`;
        const summaryBody = document.getElementById('chat-company-summary-body');
        
        let htmlContent = '';
        if (data.company_insights) {
            htmlContent += `
                <div class="mb-3">
                    <strong class="text-accent" style="font-size:12px;">인재상</strong>
                    <p style="font-size:12.5px; margin-top:4px; line-height:1.5; white-space: pre-line;">${data.company_insights.talent_profile}</p>
                </div>
                <div class="mb-3">
                    <strong class="text-accent" style="font-size:12px;">합격 꿀팁</strong>
                    <p style="font-size:12.5px; margin-top:4px; line-height:1.5; white-space: pre-line;">${data.company_insights.recommendations}</p>
                </div>
            `;
        }
        
        if (data.recruitment_detail) {
            if (data.recruitment_detail.job_cont) {
                htmlContent += `
                    <div class="mb-3" style="border-top: 1px solid var(--border-color); padding-top: 10px;">
                        <strong class="text-accent" style="font-size:12px;">상세 직무내용</strong>
                        <p style="font-size:12px; margin-top:4px; line-height:1.5; white-space: pre-line; max-height: 150px; overflow-y: auto;">${data.recruitment_detail.job_cont}</p>
                    </div>
                `;
            }
            if (data.recruitment_detail.pref_cond) {
                htmlContent += `
                    <div class="mb-3">
                        <strong class="text-accent" style="font-size:12px;">우대/자격요건</strong>
                        <p style="font-size:12px; margin-top:4px; line-height:1.5; white-space: pre-line; max-height: 150px; overflow-y: auto;">${data.recruitment_detail.pref_cond}</p>
                    </div>
                `;
            }
        }
        
        if (!htmlContent) {
            htmlContent = '<p class="text-muted" style="font-size:12px;">연동된 기업분석 정보가 없습니다.</p>';
        }
        
        summaryBody.innerHTML = htmlContent;
        
        // Navigation auto step
        let targetStep = 1;
        if (isStepAccessible(5)) targetStep = 5;
        else if (isStepAccessible(4)) targetStep = 4;
        else if (isStepAccessible(3)) targetStep = 3;
        else if (isStepAccessible(2)) targetStep = 2;
        
        navigateToStep(targetStep);
        
        // If we landed on chat step, fetch next if not complete
        if (targetStep === 3) {
            const logs = data.interview_logs || [];
            const answeredCount = logs.filter(l => l.user_answer).length;
            if (answeredCount < 3) {
                fetchNextInterviewQuestion();
            } else {
                appendChatBubble("면접 꼬리 질문 3단계가 모두 마쳤습니다! 아래 버튼을 누르거나 다음 단계로 가 자소서를 완성해 보세요.", 'ai');
                document.getElementById('chat-progress-text').textContent = "가이드 면접 종료 (3/3 답변)";
                document.getElementById('chat-answer-input').disabled = true;
                document.getElementById('btn-submit-answer').disabled = true;
            }
        }
        
        welcomeScreen.classList.add('d-none');
        agentPanel.classList.remove('d-none');
    } catch (e) {
        console.error(e);
        showToast("세션 데이터 로드 실패");
    } finally {
        hideLoading();
    }
}

async function deleteSession(sessionId) {
    if (confirm("정말 이 세션을 완전히 삭제하시겠습니까?")) {
        try {
            await fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' });
            showToast("세션이 삭제되었습니다.");
            if (currentSessionId === sessionId) {
                currentSessionId = null;
                currentQuestionId = null;
                welcomeScreen.classList.remove('d-none');
                agentPanel.classList.add('d-none');
            }
            loadSessions();
        } catch (error) {
            showToast("삭제 실패");
        }
    }
}

/* --- Navigation --- */
function navigateToStep(stepNum) {
    currentStep = stepNum;
    
    steps.forEach(step => {
        const num = parseInt(step.getAttribute('data-step'));
        if (num === stepNum) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
    
    document.querySelectorAll('.step-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    const activeSection = document.getElementById(`step-${stepNum}-section`);
    if (activeSection) {
        activeSection.classList.remove('d-none');
    }
    
    // If navigating to step 2, load recommended jobs
    if (stepNum === 2) {
        loadRecommendedJobs(currentSessionId);
    }
    
    // If navigating to step 3, auto check question state
    if (stepNum === 3) {
        // If chat is empty, fetch next
        const msgContainer = document.getElementById('chat-messages-container');
        if (msgContainer.children.length === 0) {
            fetchNextInterviewQuestion();
        }
    }
}
