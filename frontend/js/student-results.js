// Global state
let currentPage = 1;
const limit = 5;
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    // Check Auth
    if (!localStorage.getItem('teacher_token')) {
        window.location.href = 'index.html';
    }
    
    updateDateTime();
    setInterval(updateDateTime, 60000); // update every min
    
    loadStats();
    loadResults();
    
    // Close modals on ESC
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            closeAnswerModal();
            closeResultModal();
        }
    });
    
    // Close result modal on backdrop click
    document.getElementById('resultModal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeResultModal();
    });
    document.getElementById('answerModal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeAnswerModal();
    });
});

function logout() {
    localStorage.removeItem('teacher_token');
    window.location.href = 'index.html';
}

function updateDateTime() {
    const elDate = document.getElementById('currentDateDisplay');
    const elTime = document.getElementById('currentTimeDisplay');
    if (!elDate || !elTime) return;
    
    const now = new Date();
    elDate.textContent = now.toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });
    elTime.textContent = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

// API Call Helper
async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('teacher_token');
    try {
        const res = await fetch(`/api/teachers${endpoint}`, {
            ...options,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        if (res.status === 401) {
            logout();
            throw new Error('Unauthorized');
        }
        return await res.json();
    } catch (e) {
        console.error("API Error", e);
        throw e;
    }
}

// Stats
async function loadStats() {
    try {
        const data = await fetchAPI('/results/stats');
        document.getElementById('statTotalStudents').textContent = data.total_students || '0';
        document.getElementById('statEvaluatedStudents').textContent = data.evaluated_students || '0';
        document.getElementById('statTotalEvaluations').textContent = data.total_evaluations || '0';
        document.getElementById('statAvgScore').textContent = data.average_score ? `${data.average_score}%` : '0%';
    } catch (e) {
        console.warn("Could not load stats");
    }
}

// Main Results Table
async function loadResults() {
    const tbody = document.getElementById('resultsTableBody');
    
    const search = document.getElementById('searchInput').value;
    const date = document.getElementById('dateFilter').value;
    const sort = document.getElementById('sortOrder').value;
    
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted);">
        <i class='bx bx-loader-alt bx-spin' style="font-size: 24px; color: var(--primary); margin-bottom: 8px;"></i><br>
        Loading results...
    </td></tr>`;
    
    try {
        const query = new URLSearchParams({ page: currentPage, limit, search, date, sort });
        const data = await fetchAPI(`/results?${query}`);
        
        if (data.status === 'success') {
            renderResults(data.results);
            renderPagination(data.total);
        } else {
            showErrorState(data.message || "Failed to load results");
        }
    } catch (e) {
        showErrorState("Unable to load evaluation results.");
    }
}

function renderResults(results) {
    const tbody = document.getElementById('resultsTableBody');
    
    if (!results || results.length === 0) {
        const isFilter = document.getElementById('searchInput').value || document.getElementById('dateFilter').value !== 'all';
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align: center; padding: 60px 20px;">
                    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
                        <i class='bx bx-folder-open' style="font-size: 48px; color: #cbd5e1; margin-bottom: 16px;"></i>
                        <h3 style="font-size: 16px; color: var(--text-dark); margin-bottom: 8px;">No Evaluation Results</h3>
                        <p style="font-size: 14px; color: var(--text-secondary); margin-bottom: 16px;">
                            ${isFilter ? "There are no evaluated student booklets matching your filters." : "No evaluated booklets available."}
                        </p>
                        ${isFilter ? `<button class="btn-secondary" onclick="clearFilters()">Clear Filters</button>` : ''}
                    </div>
                </td>
            </tr>
        `;
        return;
    }
    
    let html = '';
    const startIndex = (currentPage - 1) * limit;
    
    results.forEach((row, index) => {
        const displayIndex = startIndex + index + 1;
        
        let dateStr = "N/A";
        if (row.evaluated_on) {
            const d = new Date(row.evaluated_on);
            dateStr = d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' }) + ", " + 
                      d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        }
        
        const pct = Math.round((row.total_marks / (row.maximum_marks || 1)) * 100);
        
        html += `
            <tr>
                <td>${displayIndex}</td>
                <td style="font-weight: 600;">${escapeHtml(row.student_name)}</td>
                <td>${escapeHtml(row.usn || '-')}</td>
                <td>${row.total_marks} / ${row.maximum_marks}</td>
                <td>
                    <div class="score-display">
                        <div class="progress-track">
                            <div class="progress-fill" style="width: ${pct}%"></div>
                        </div>
                        <span class="score-text">${pct}%</span>
                    </div>
                </td>
                <td>${dateStr}</td>
                <td style="text-align: right;">
                    <button class="btn-secondary" style="padding: 6px 12px; font-size: 13px;" onclick="openResultModal(${row.id})">
                        <i class='bx bx-show'></i> View
                    </button>
                </td>
            </tr>
        `;
    });
    
    tbody.innerHTML = html;
}

function renderPagination(total) {
    const totalPages = Math.ceil(total / limit) || 1;
    const start = total === 0 ? 0 : ((currentPage - 1) * limit) + 1;
    const end = Math.min(currentPage * limit, total);
    
    document.getElementById('paginationInfo').textContent = `Showing ${start} to ${end} of ${total} results`;
    
    const controls = document.getElementById('paginationControls');
    let html = '';
    
    html += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})"><i class='bx bx-chevron-left'></i></button>`;
    
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            html += `<button class="page-btn" disabled>...</button>`;
        }
    }
    
    html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})"><i class='bx bx-chevron-right'></i></button>`;
    
    controls.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadResults();
}

function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadResults();
    }, 300);
}

function applyFilters() {
    currentPage = 1;
    loadResults();
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('dateFilter').value = 'all';
    document.getElementById('sortOrder').value = 'newest';
    currentPage = 1;
    loadResults();
}

function refreshResults() {
    loadStats();
    loadResults();
}

function showErrorState(msg) {
    document.getElementById('resultsTableBody').innerHTML = `
        <tr><td colspan="7" style="text-align: center; padding: 40px;">
            <i class='bx bx-error-circle' style="font-size: 32px; color: var(--error-main); margin-bottom: 12px;"></i>
            <p style="color: var(--error-main);">${escapeHtml(msg)}</p>
            <button class="btn-secondary" style="margin-top: 12px;" onclick="loadResults()">Retry</button>
        </td></tr>
    `;
}

// Modal Details
let currentStudentId = null;

async function openResultModal(studentId) {
    currentStudentId = studentId;
    document.getElementById('resultModal').classList.add('show');
    document.getElementById('modalQuestionsBody').innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 30px;">Loading details...</td></tr>`;
    
    try {
        const data = await fetchAPI(`/results/${studentId}`);
        if (data.status === 'success') {
            renderResultDetails(data);
        } else {
            showToast("Failed to load details", "error");
            closeResultModal();
        }
    } catch (e) {
        showToast("Error loading details", "error");
        closeResultModal();
    }
}

function renderResultDetails(data) {
    const s = data.student;
    const name = s.name || s.username || 'Student';
    const usn  = s.usn || s.username || '—';

    // Header initials
    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'ST';
    document.getElementById('modalInitials').textContent = initials;
    document.getElementById('modalStudentName').textContent = name;
    document.getElementById('modalUSN').textContent = usn;
    document.getElementById('modalBranch').textContent = s.branch || 'N/A';
    document.getElementById('modalBookletId').textContent = data.booklet ? data.booklet.id : 'BKT-2026-001';

    let dateStr = 'N/A';
    if (data.evaluated_on) {
        const d = new Date(data.evaluated_on);
        dateStr = d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' }) +
                  ', ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
    document.getElementById('modalEvaluatedOn').textContent = dateStr;

    // Summary cards
    const pct = data.maximum_marks ? Math.round((data.total_marks / data.maximum_marks) * 100) : 0;
    document.getElementById('modalTotalMarks').textContent  = `${data.total_marks} / ${data.maximum_marks}`;
    document.getElementById('modalOverallScore').textContent = `${pct}%`;
    document.getElementById('modalQuestionsCountStr').textContent = data.questions.length > 0 ? `Q1 - Q${data.questions.length}` : '—';
    document.getElementById('modalEvalTime').textContent = data.evaluation_time || '—';

    // Result badge (top right of student info)
    const isPass = pct >= 40;
    const badgeCard = document.getElementById('resultBadgeCard');
    const badgeTxt  = document.getElementById('modalResultBadge');
    const badgeSub  = document.getElementById('modalResultSub');
    const badgeIcon = document.getElementById('modalResultIcon');
    if (badgeTxt) {
        if (isPass) {
            badgeCard.style.cssText += 'background:#f0fdf4;border-color:#bbf7d0;';
            badgeTxt.style.color = '#16a34a';
            badgeTxt.textContent = 'PASS';
            badgeSub.style.color = '#166534';
            badgeSub.textContent = pct >= 75 ? 'Great Performance!' : 'Above Threshold';
            if (badgeIcon) badgeIcon.style.color = '#16a34a';
        } else {
            badgeCard.style.cssText += 'background:#fef2f2;border-color:#fecaca;';
            badgeTxt.style.color = '#dc2626';
            badgeTxt.textContent = 'FAIL';
            badgeSub.style.color = '#991b1b';
            badgeSub.textContent = 'Below Threshold';
            if (badgeIcon) badgeIcon.style.color = '#dc2626';
        }
    }

    // Final result section
    document.getElementById('finalTotalMarks').textContent = `${data.total_marks} / ${data.maximum_marks}`;
    document.getElementById('finalPercentage').textContent = `${pct}%`;
    const elRes = document.getElementById('finalResult');
    elRes.textContent = isPass ? 'PASS' : 'FAIL';
    elRes.style.color = isPass ? '#16a34a' : '#dc2626';
    const elMsg = document.getElementById('finalResultMessage');
    if (elMsg) {
        elMsg.textContent = isPass
            ? `The student has secured ${pct}% which is above the passing threshold.`
            : `The student has secured ${pct}% which is below the passing threshold.`;
    }

    // Question table rows
    let qHtml = '';
    data.questions.forEach(q => {
        const qPct = q.maximum_marks ? Math.round((q.marks_awarded / q.maximum_marks) * 100) : 0;
        const status = calculateQuestionStatus(qPct);

        let statusColor = '#16a34a';
        if (status === 'Good')     statusColor = '#84cc16';
        if (status === 'Partial')  statusColor = '#f59e0b';
        if (status === 'No Marks') statusColor = '#ef4444';

        // Safe answer escaping for onclick
        const safeAnswer = (q.student_answer || '').replace(/'/g, "\\'").replace(/"/g, '\\"').replace(/\n/g, '\\n');
        let ansText = (q.student_answer || 'No answer recorded');
        const ansPreview = escapeHtml(ansText.substring(0, 45));

        const qLabel = `Q${String(q.question_number).padStart(2, '0')}`;

        qHtml += `
            <tr style="border-bottom: 1px solid var(--border);">
                <td style="padding: 12px 0; font-size: 13px; color: var(--text-dark);">${qLabel}</td>
                <td style="padding: 12px 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 0;">
                    <span title="${escapeHtml(q.question_text)}" style="display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; color:var(--text-dark);">${escapeHtml(q.question_text)}</span>
                </td>
                <td style="padding: 12px 10px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 0;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span style="display:block; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px; color:var(--text-secondary); max-width: 85%;">${ansPreview}${ansText.length > 45 ? '...' : ''}</span>
                        <i class='bx bx-show' title="Hover to view full answer" style="color: var(--text-secondary); cursor: pointer; font-size: 16px;" onclick="openAnswerModal('${safeAnswer}')"></i>
                    </div>
                </td>
                <td style="padding: 12px 10px; text-align: center; font-weight: 700; font-size: 13px; color: var(--text-dark);">${q.marks_awarded}</td>
                <td style="padding: 12px 10px; text-align: center; font-size: 13px; color: var(--text-dark);">${q.maximum_marks}</td>
                <td style="padding: 12px 10px; text-align: center; font-weight: 600; font-size: 13px; color: var(--text-dark);">${qPct}%</td>
                <td style="padding: 12px 10px; text-align: left; font-size: 12px; font-weight: 600; color: ${statusColor};">
                    <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${statusColor}; margin-right:6px;"></span>${status}
                </td>
                <td style="padding: 12px 10px; text-align: center;">
                    <button aria-label="View full student answer" onclick="openAnswerModal('${safeAnswer}')" style="background:#fdf2f8; border:none; color:var(--primary); border-radius:6px; padding:4px 10px; cursor:pointer; font-size:11px; font-weight: 600; display:inline-flex; align-items:center; gap:4px; white-space: nowrap;">
                        <i class='bx bx-show' style="font-size: 14px;"></i> View Answer
                    </button>
                </td>
            </tr>
        `;
    });

    document.getElementById('modalQuestionsBody').innerHTML = qHtml || '<tr><td colspan="8" style="text-align:center;padding:30px;color:var(--text-muted);">No questions found.</td></tr>';
}

function calculateQuestionStatus(pct) {
    if (pct >= 90) return 'Excellent';
    if (pct >= 75) return 'Good';
    if (pct >= 40) return 'Partial';
    return 'No Marks';
}

function closeResultModal() {
    document.getElementById('resultModal').classList.remove('show');
    currentStudentId = null;
}

function openAnswerModal(text) {
    document.getElementById('fullAnswerText').textContent = text;
    document.getElementById('answerModal').classList.add('show');
}

function closeAnswerModal() {
    document.getElementById('answerModal').classList.remove('show');
}

async function downloadReport() {
    if (!currentStudentId) return;
    showToast("Generating report...", "success");
    // Placeholder logic for download
    try {
        const res = await fetchAPI(`/results/${currentStudentId}/report`);
        if (res.status === 'error') {
            showToast(res.message, "error");
        }
    } catch(e) {
        showToast("Error generating report.", "error");
    }
}

// Utils
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return unsafe
         .toString()
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
}

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icon = type === 'success' ? 'bx-check-circle' : 'bx-error-circle';
    toast.innerHTML = `<i class='bx ${icon} toast-icon'></i><div class="toast-message">${escapeHtml(message)}</div>`;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}
