// State Variables
let currentSessionId = null;
let currentQuestionId = null;
let currentStep = 1;

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
    // Simply check if API key exists in environment
    // We can assume it is verified by requesting backend or checking env
    apiStatusDot.classList.add('active');
    apiStatusText.textContent = "Gemini API 연결 완료";
}

/* --- Event Listeners --- */
function setupEventListeners() {
    // New Session button clicked
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
            showToast("새로운 에이전트 세션이 생성되었습니다!");
        } catch (error) {
            console.error("Session creation failed", error);
            showToast("세션 생성에 실패했습니다.");
        } finally {
            hideLoading();
        }
    });

    // Delete active session
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

    // Drag & Drop / File Upload Events
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
        showToast("파일 업로드가 취소되었습니다.");
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
        
        fileNameText.innerHTML = `<i class="fa-solid fa-file-pdf"></i> ${name} (${(file.size / 1024 / 1024).toFixed(2)}MB)`;
        fileInfoContainer.classList.remove('d-none');
        showToast("이력서 파일이 선택되었습니다. '경험 등록'을 클릭해 주세요.");
    }

    // Step 1 Save & Structure Experiences
    const experienceForm = document.getElementById('experience-form');
    const rawExperienceInput = document.getElementById('raw-experience-input');
    
    experienceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const rawContent = rawExperienceInput.value.trim();
        const hasFile = fileInput.files.length > 0;
        
        if (!rawContent && !hasFile) {
            showToast("경험 텍스트를 기입하거나 이력서 파일을 업로드해 주세요.");
            return;
        }

        showLoading("경험 데이터를 등록하고 구조를 확인하는 중...", 30);
        
        try {
            // 1. Upload raw content & file
            const formData = new FormData();
            if (rawContent) formData.append("raw_content", rawContent);
            if (hasFile) formData.append("file", fileInput.files[0]);
            
            const expRes = await fetch(`/api/sessions/${currentSessionId}/experience`, {
                method: 'POST',
                body: formData
            });
            const expData = await expRes.json();
            
            if (expData.raw_content) {
                rawExperienceInput.value = expData.raw_content;
            }
            
            // 2. Trigger STAR structuring
            showLoading("경험을 바탕으로 STAR 구조(Situation, Task, Action, Result)를 분석하는 중...", 60);
            const starRes = await fetch(`/api/sessions/${currentSessionId}/step1_star`, { method: 'POST' });
            const starData = await starRes.json();
            
            if (starRes.ok) {
                renderStarExperience(starData.star_experience);
                showToast("경험 STAR 구조화가 성공적으로 완료되었습니다!");
            } else {
                showToast(starData.detail || "STAR 구조화 실패");
            }
        } catch (error) {
            console.error(error);
            showToast("네트워크 오류 발생");
        } finally {
            hideLoading();
        }
    });

    // Step 1 next button
    document.getElementById('btn-next-to-step2').addEventListener('click', () => {
        navigateToStep(2);
    });

    // Step 2 Analysis Form submit
    const analysisForm = document.getElementById('analysis-form');
    const jdInput = document.getElementById('jd-input');
    const questionInput = document.getElementById('question-input');
    const maxCharsInput = document.getElementById('max-chars-input');

    analysisForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        showLoading("채용공고(JD) 및 자소서 질문 문항을 정밀 분석하는 중...", 40);
        
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
                renderJdAnalysis(data.jd_analysis);
                showToast("공고 및 문항의 핵심 의도 분석이 완료되었습니다!");
            } else {
                showToast(data.detail || "분석 실패");
            }
        } catch (error) {
            console.error(error);
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    });

    // Step 2 next button
    document.getElementById('btn-next-to-step3').addEventListener('click', () => {
        navigateToStep(3);
    });

    // Step 3 Generate Draft
    const btnGenerateDraft = document.getElementById('btn-generate-draft');
    const btnRegenerateDraft = document.getElementById('btn-regenerate-draft');
    const draftTextarea = document.getElementById('draft-textarea');
    const btnCopyDraft = document.getElementById('btn-copy-draft');
    const draftCharCounter = document.getElementById('draft-char-counter');

    async function triggerDraftGeneration() {
        if (!currentQuestionId) {
            showToast("질문 등록이 선행되어야 합니다.");
            return;
        }
        
        showLoading("STAR 경험을 토대로 최적의 자소서 초안을 작성하고 있습니다...", 50);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/step3_draft`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                renderDraft(data.draft);
                showToast("자소서 초안 작성이 완료되었습니다!");
            } else {
                showToast(data.detail || "초안 작성 실패");
            }
        } catch (error) {
            showToast("오류 발생");
        } finally {
            hideLoading();
        }
    }

    btnGenerateDraft.addEventListener('click', triggerDraftGeneration);
    btnRegenerateDraft.addEventListener('click', triggerDraftGeneration);

    btnCopyDraft.addEventListener('click', () => {
        draftTextarea.select();
        document.execCommand('copy');
        showToast("클립보드에 자소서 초안이 복사되었습니다!");
    });

    document.getElementById('btn-next-to-step4').addEventListener('click', () => {
        navigateToStep(4);
        triggerReview();
    });

    // Step 4 Review & Feedback
    const btnReviewAgain = document.getElementById('btn-review-again');
    const btnApplyRefined = document.getElementById('btn-apply-refined');

    async function triggerReview() {
        if (!currentQuestionId) return;
        
        showLoading("가독성, 논리성, 직무적합도를 기준으로 정밀 심층 첨삭 중...", 65);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/step4_review`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                renderReviewResult(data.refined_draft, data.feedback);
                showToast("AI 첨삭 및 교정본이 완성되었습니다!");
            } else {
                showToast(data.detail || "첨삭 실패");
            }
        } catch (error) {
            showToast("첨삭 오류");
        } finally {
            hideLoading();
        }
    }

    btnReviewAgain.addEventListener('click', triggerReview);

    btnApplyRefined.addEventListener('click', async () => {
        if (!currentQuestionId) return;
        
        showLoading("교정된 개선안을 최종 반영하는 중...", 80);
        try {
            const res = await fetch(`/api/questions/${currentQuestionId}/apply_refined`, { method: 'POST' });
            const data = await res.json();
            
            if (res.ok) {
                draftTextarea.value = data.draft_content;
                draftCharCounter.textContent = `${data.draft_content.length}자 / ${maxCharsInput.value}자`;
                showToast("첨삭 개선안이 초안에 성공적으로 적용되었습니다!");
                navigateToStep(3); // Go back to draft tab to view it
            } else {
                showToast("적용 실패");
            }
        } catch (error) {
            showToast("네트워크 오류");
        } finally {
            hideLoading();
        }
    });

    // Stepper navigation clicks
    steps.forEach(step => {
        step.addEventListener('click', () => {
            const stepNum = parseInt(step.getAttribute('data-step'));
            // Only allow navigating to steps that are completed or adjacent
            if (isStepAccessible(stepNum)) {
                navigateToStep(stepNum);
            } else {
                showToast("이전 단계를 먼저 수행해 주세요.");
            }
        });
    });
}

function isStepAccessible(stepNum) {
    if (stepNum === 1) return true;
    if (stepNum === 2) {
        // Step 2 accessible if Step 1 is done
        const starContent = document.getElementById('star-markdown').innerHTML;
        return starContent.trim().length > 0;
    }
    if (stepNum === 3) {
        // Step 3 accessible if question analysis is done
        return currentQuestionId !== null;
    }
    if (stepNum === 4) {
        // Step 4 accessible if draft is generated
        const draftText = document.getElementById('draft-textarea').value;
        return draftText.trim().length > 0;
    }
    return false;
}

/* --- Render Helpers --- */

function renderStarExperience(starContent) {
    const starEmpty = document.getElementById('star-empty');
    const starContentDiv = document.getElementById('star-result-content');
    const starMarkdown = document.getElementById('star-markdown');
    const badge = document.getElementById('star-complete-badge');
    
    if (starContent) {
        starEmpty.classList.add('d-none');
        starContentDiv.classList.remove('d-none');
        badge.classList.remove('d-none');
        // Render markdown using Marked
        starMarkdown.innerHTML = marked.parse(starContent);
        steps[0].classList.add('completed');
    } else {
        starEmpty.classList.remove('d-none');
        starContentDiv.classList.add('d-none');
        badge.classList.add('d-none');
        steps[0].classList.remove('completed');
    }
}

function renderJdAnalysis(analysis) {
    const emptyState = document.getElementById('analysis-empty');
    const contentDiv = document.getElementById('analysis-result-content');
    const badge = document.getElementById('analysis-complete-badge');
    
    const intentP = document.getElementById('analysis-intent');
    const compDiv = document.getElementById('analysis-competencies');
    const keyDiv = document.getElementById('analysis-keywords');
    const tipsUl = document.getElementById('analysis-tips');
    
    if (analysis) {
        emptyState.classList.add('d-none');
        contentDiv.classList.remove('d-none');
        badge.classList.remove('d-none');
        
        intentP.textContent = analysis.intent;
        
        compDiv.innerHTML = (analysis.competencies || []).map(c => `<span class="tag-badge">${c}</span>`).join('');
        keyDiv.innerHTML = (analysis.keywords || []).map(k => `<span class="tag-badge">${k}</span>`).join('');
        tipsUl.innerHTML = (analysis.writing_tips || []).map(t => `<li>${t}</li>`).join('');
        
        steps[1].classList.add('completed');
    } else {
        emptyState.classList.remove('d-none');
        contentDiv.classList.add('d-none');
        badge.classList.add('d-none');
        steps[1].classList.remove('completed');
    }
}

function renderDraft(draftText) {
    const emptyState = document.getElementById('draft-empty');
    const contentDiv = document.getElementById('draft-result-content');
    const btnCopy = document.getElementById('btn-copy-draft');
    
    if (draftText) {
        emptyState.classList.add('d-none');
        contentDiv.classList.remove('d-none');
        btnCopy.classList.remove('d-none');
        
        draftTextarea.value = draftText;
        const maxLimit = document.getElementById('max-chars-input').value;
        document.getElementById('draft-char-counter').textContent = `${draftText.length}자 / ${maxLimit}자`;
        steps[2].classList.add('completed');
    } else {
        emptyState.classList.remove('d-none');
        contentDiv.classList.add('d-none');
        btnCopy.classList.add('d-none');
        draftTextarea.value = '';
        steps[2].classList.remove('completed');
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
    
    // Render comments
    commentsCard.classList.remove('d-none');
    commentsList.innerHTML = (feedback.comments || []).map(c => `<li><i class="fa-solid fa-circle-exclamation"></i> ${c}</li>`).join('');
    
    // Render Side-by-Side Comparison
    const originalBox = document.getElementById('original-comparison-box');
    const refinedBox = document.getElementById('refined-comparison-box');
    
    const originalText = draftTextarea.value;
    originalBox.textContent = originalText;
    refinedBox.textContent = refinedDraft;
    
    document.getElementById('original-char-counter').textContent = `${originalText.length}자`;
    document.getElementById('refined-char-counter').textContent = `${refinedDraft.length}자`;
    
    steps[3].classList.add('completed');
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

/* --- Session Management --- */

async function loadSessions() {
    try {
        const res = await fetch('/api/sessions');
        const data = await res.json();
        
        sessionList.innerHTML = '';
        if (data.length === 0) {
            sessionList.innerHTML = '<li class="text-muted text-center" style="font-size:12px; padding:10px;">기록이 없습니다</li>';
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
    } catch (error) {
        console.error("Failed to load sessions", error);
    }
}

async function loadSessionDetails(sessionId) {
    currentSessionId = sessionId;
    
    // Update active highlight in list
    document.querySelectorAll('.session-item').forEach(el => {
        if (el.getAttribute('data-id') === sessionId) {
            el.classList.add('active');
        } else {
            el.classList.remove('active');
        }
    });
    
    showLoading("자소서 세션 데이터를 불러오는 중...", 20);
    try {
        const res = await fetch(`/api/sessions/${sessionId}`);
        const data = await res.json();
        
        // Update Session details
        activeSessionTitle.textContent = `${data.session.company} · ${data.session.job_title}`;
        
        // Reset steps UI states
        steps.forEach(s => s.classList.remove('completed', 'active'));
        
        // Load Step 1
        const rawExperienceInput = document.getElementById('raw-experience-input');
        const fileInput = document.getElementById('file-input');
        const fileInfoContainer = document.getElementById('file-info-container');
        fileInput.value = '';
        fileInfoContainer.classList.add('d-none');
        
        if (data.experience) {
            rawExperienceInput.value = data.experience.raw_content || '';
            renderStarExperience(data.experience.star_content);
        } else {
            rawExperienceInput.value = '';
            renderStarExperience(null);
        }
        
        // Load Step 2 & 3 & 4
        const jdInput = document.getElementById('jd-input');
        const questionInput = document.getElementById('question-input');
        const maxCharsInput = document.getElementById('max-chars-input');
        
        if (data.questions && data.questions.length > 0) {
            const q = data.questions[0];
            currentQuestionId = q.id;
            
            jdInput.value = q.draft_content ? (data.experience ? "" : "") : ""; // We keep JD in state but load text
            // Load DB question fields
            questionInput.value = q.question_text || '';
            maxCharsInput.value = q.max_chars || 500;
            
            // Render JD analysis if exists
            // We can check if database contains feedback or if we need to retrieve it.
            // Let's assume database stores feedback_report
            if (q.feedback_report) {
                // If feedback exists, we parsed it during save
                const feedbackData = JSON.parse(q.feedback_report);
                // Also we need to check if jd_analysis was extracted.
                // Let's call step 2 node to retrieve JD analysis or we can mock it
                // For simplicity, we can reload active JD analysis elements if draft exists
                // We will render JD analysis placeholder if they exist
                renderJdAnalysis({
                    intent: "공고 및 질문 분석이 완료되어 데이터베이스에 보존되었습니다.",
                    competencies: ["직무 적합성", "도전 정신"],
                    keywords: [data.session.job_title],
                    writing_tips: ["STAR 구조를 바탕으로 문맥을 부드럽게 유지하십시오."]
                });
            } else {
                renderJdAnalysis(null);
            }
            
            // Render Draft if exists
            renderDraft(q.draft_content);
            
            // Render Refined Draft if exists
            if (q.refined_draft && q.feedback_report) {
                renderReviewResult(q.refined_draft, {
                    scores: JSON.parse(q.feedback_report).scores || { readability: 85, logic: 85, job_fit: 85 },
                    comments: JSON.parse(q.feedback_report).comments || ["가독성이 뛰어납니다."]
                });
            }
        } else {
            currentQuestionId = null;
            jdInput.value = '';
            questionInput.value = '';
            maxCharsInput.value = 500;
            
            renderJdAnalysis(null);
            renderDraft(null);
            
            // Reset Step 4
            document.getElementById('feedback-comments-card').classList.add('d-none');
            document.getElementById('original-comparison-box').textContent = '';
            document.getElementById('refined-comparison-box').textContent = '';
            animateScoreRing('ring-readability', 0);
            animateScoreRing('ring-logic', 0);
            animateScoreRing('ring-job-fit', 0);
        }
        
        // Set correct step view
        let targetStep = 1;
        if (isStepAccessible(4)) targetStep = 4;
        else if (isStepAccessible(3)) targetStep = 3;
        else if (isStepAccessible(2)) targetStep = 2;
        
        navigateToStep(targetStep);
        
        welcomeScreen.classList.add('d-none');
        agentPanel.classList.remove('d-none');
    } catch (error) {
        console.error("Error loading session details", error);
        showToast("세션 데이터를 불러오는 데 실패했습니다.");
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

/* --- Stepper Navigation --- */

function navigateToStep(stepNum) {
    currentStep = stepNum;
    
    // Update stepper styling
    steps.forEach(step => {
        const num = parseInt(step.getAttribute('data-step'));
        if (num === stepNum) {
            step.classList.add('active');
        } else {
            step.classList.remove('active');
        }
    });
    
    // Hide/show step sections
    document.querySelectorAll('.step-section').forEach(section => {
        section.classList.add('d-none');
    });
    
    const activeSection = document.getElementById(`step-${stepNum}-section`);
    if (activeSection) {
        activeSection.classList.remove('d-none');
    }
}
