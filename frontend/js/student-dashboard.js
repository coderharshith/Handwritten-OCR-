// Student Dashboard Logic

document.addEventListener('DOMContentLoaded', () => {
    // Check if logged in as student
    const token = localStorage.getItem('student_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }
    
    loadMyResults();

    // Close modals on ESC
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeAnswerModal();
    });
    
    // Close answer modal on backdrop click
    document.getElementById('answerModal').addEventListener('click', e => {
        if (e.target === e.currentTarget) closeAnswerModal();
    });
});

function logout() {
    localStorage.removeItem('student_token');
    window.location.href = 'index.html';
}

async function loadMyResults() {
    const token = localStorage.getItem('student_token');
    
    try {
        const response = await fetch('/api/students/my-results', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.status === 401) {
            logout();
            return;
        }
        
        const data = await response.json();
        
        if (data.status === 'success') {
            renderDashboard(data);
        } else {
            showEmptyState(data.message || 'Unable to load results.');
        }
    } catch (error) {
        console.error('API Error:', error);
        showEmptyState('Unable to connect to the server. Please try again.', error.stack);
    }
}

function escapeHtml(unsafe) {
    if (!unsafe) return '';
    return (unsafe || '').toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function renderDashboard(data) {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('contentWrapper').style.display = 'block';
    
    // Header initials & name
    const s = data.student_info;
    const name = s.name || s.username || 'Student';
    const usn  = s.usn || s.username || '—';
    
    document.getElementById('studentProfileName').textContent = name;
    
    const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'ST';
    document.getElementById('modalInitials').textContent = initials;
    document.getElementById('modalStudentName').textContent = name;
    document.getElementById('modalUSN').textContent = usn;
    // Assuming branch isn't in student_info directly, we leave a placeholder or default if undefined.
    document.getElementById('modalBranch').textContent = s.branch || 'Computer Science & Engineering';

    // Booklet
    document.getElementById('modalBookletId').textContent = 'BKT-2026-001'; // Can make dynamic later

    let dateStr = '—';
    if (data.summary.evaluated_on) {
        const d = new Date(data.summary.evaluated_on);
        dateStr = d.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' }) +
                  ', ' + d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    }
    document.getElementById('modalEvaluatedOn').textContent = dateStr;

    // Summary cards
    const totalMarks = data.summary.total_marks || 0;
    const maxMarks = data.summary.maximum_marks || 0;
    const pct = maxMarks ? Math.round((totalMarks / maxMarks) * 100) : 0;
    
    document.getElementById('modalTotalMarks').textContent  = `${totalMarks} / ${maxMarks}`;
    document.getElementById('modalOverallScore').textContent = `${pct}%`;
    document.getElementById('modalQuestionsCountStr').textContent = data.questions && data.questions.length > 0 ? `Q1 - Q${data.questions.length}` : '—';
    document.getElementById('modalEvalTime').textContent = data.summary.evaluation_time || '2m 36s'; // Fallback

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
    document.getElementById('finalTotalMarks').textContent = `${totalMarks} / ${maxMarks}`;
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

    if (data.questions && data.questions.length > 0) {
        renderQuestions(data.questions);
    } else {
        showEmptyResults();
    }
}

function calculateQuestionStatus(pct) {
    if (pct >= 90) return 'Excellent';
    if (pct >= 75) return 'Good';
    if (pct >= 40) return 'Partial';
    return 'No Marks';
}

function renderQuestions(questions) {
    const container = document.getElementById('questionsContainer');
    let qHtml = '';
    
    questions.forEach(q => {
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
    
    container.innerHTML = qHtml;
}

function openAnswerModal(answerText) {
    document.getElementById('fullAnswerText').textContent = answerText;
    document.getElementById('answerModal').style.display = 'flex';
}

function closeAnswerModal() {
    document.getElementById('answerModal').style.display = 'none';
}

function showEmptyState(msg, errStack = '') {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('contentWrapper').style.display = 'block';
    
    // Instead of replacing the tbody, let's just create a div outside the table
    // or just put it in a safe place.
    const tableWrap = document.querySelector('.q-table-wrap');
    if (tableWrap) tableWrap.style.display = 'none';
    
    // Also inject a debug div at the top of contentWrapper
    const errDiv = document.createElement('div');
    errDiv.innerHTML = `
        <div class="empty-state" style="padding: 40px; background: #fef2f2; border-radius: 8px; margin-bottom: 20px;">
            <i class='bx bx-error-circle' style="color: #e11d48; font-size: 32px;"></i>
            <h3 style="color: #e11d48;">Error loading results</h3>
            <p style="color: #991b1b; white-space: pre-wrap; font-family: monospace; text-align: left;">${escapeHtml(msg)}\n\n${escapeHtml(errStack)}</p>
        </div>
    `;
    document.getElementById('contentWrapper').prepend(errDiv);
}

function showEmptyResults() {
    document.getElementById('questionsContainer').innerHTML = `
        <div class="empty-state">
            <i class='bx bx-file-blank'></i>
            <h3>No results found</h3>
            <p>Your booklets have not been evaluated yet. Please check back later.</p>
        </div>
    `;
}

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
