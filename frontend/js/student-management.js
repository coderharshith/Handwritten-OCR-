// Global state
let currentPage = 1;
const limit = 7;
let totalStudents = 0;
let searchTimeout = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    updateDateDisplay();
    loadStudents();
    
    // Check auth
    if (!localStorage.getItem('teacher_token')) {
        window.location.href = 'index.html';
    }
});

// Auth
function logout() {
    localStorage.removeItem('teacher_token');
    window.location.href = 'index.html';
}

// Date Display
function updateDateDisplay() {
    const el = document.getElementById('currentDateDisplay');
    if (!el) return;
    const now = new Date();
    const options = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' };
    const dateStr = now.toLocaleDateString('en-US', options);
    const timeStr = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    el.textContent = `${dateStr}, ${timeStr}`;
}

// API Calls
async function fetchAPI(endpoint, options = {}) {
    const token = localStorage.getItem('teacher_token');
    const headers = {
        'Authorization': `Bearer ${token}`
    };
    
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }
    
    try {
        const response = await fetch(`/api/teachers${endpoint}`, {
            ...options,
            headers: {
                ...headers,
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            logout();
            throw new Error('Unauthorized');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Load Data
async function loadStudents() {
    const tbody = document.getElementById('studentsTableBody');
    const mobileContainer = document.getElementById('mobileCardsContainer');
    
    const search = document.getElementById('searchInput').value;
    const status = document.getElementById('statusFilter').value;
    const sort = document.getElementById('sortOrder').value;
    
    // Show loading
    const loadingHtml = `<tr><td colspan="6" style="text-align: center; padding: 30px;">Loading students...</td></tr>`;
    tbody.innerHTML = loadingHtml;
    mobileContainer.innerHTML = `<div style="text-align: center; padding: 20px;">Loading...</div>`;
    
    try {
        const queryParams = new URLSearchParams({
            page: currentPage,
            limit: limit,
            search: search,
            status: status,
            sort: sort
        });
        
        const data = await fetchAPI(`/students?${queryParams}`);
        
        if (data.status === 'success') {
            totalStudents = data.total;
            renderStudents(data.students);
            renderPagination(data.total);
            updateTotalStudents(data.total);
        } else {
            showErrorState(data.message || 'Unable to load students.');
        }
    } catch (error) {
        showErrorState('Unable to load students. Please try again.');
    }
}

function renderStudents(students) {
    const tbody = document.getElementById('studentsTableBody');
    const mobileContainer = document.getElementById('mobileCardsContainer');
    
    if (!students || students.length === 0) {
        const isSearch = document.getElementById('searchInput').value || document.getElementById('statusFilter').value !== 'all';
        const emptyHtml = `
            <tr>
                <td colspan="6">
                    <div class="empty-state">
                        <i class='bx ${isSearch ? "bx-search" : "bx-group"}'></i>
                        <h3>${isSearch ? "No matching students" : "No Authorized Students"}</h3>
                        <p>${isSearch ? "Try changing your search or filters." : "Use the form above to add an authorized student account."}</p>
                        ${isSearch 
                            ? `<button class="btn-secondary" onclick="clearFilters()">Clear Filters</button>`
                            : ``
                        }
                    </div>
                </td>
            </tr>
        `;
        tbody.innerHTML = emptyHtml;
        mobileContainer.innerHTML = emptyHtml;
        return;
    }
    
    let tableHtml = '';
    let mobileHtml = '';
    
    const startIndex = (currentPage - 1) * limit;
    
    students.forEach((student, index) => {
        const displayIndex = startIndex + index + 1;
        const dateStr = new Date(student.created_at).toLocaleString('en-US', {
            day: '2-digit', month: 'short', year: 'numeric',
            hour: '2-digit', minute: '2-digit'
        });
        
        const statusHtml = student.status == 1 
            ? `<span class="status-pill status-active"><div class="status-dot"></div>Active</span>`
            : `<span class="status-pill status-inactive"><div class="status-dot"></div>Inactive</span>`;
            
        const usnDisplay = student.usn || '-';
            
        // Desktop Row
        tableHtml += `
            <tr>
                <td>${displayIndex}</td>
                <td class="td-dark">${escapeHtml(student.full_name || student.username)}</td>
                <td>${escapeHtml(usnDisplay)}</td>
                <td>${dateStr}</td>
                <td>${statusHtml}</td>
                <td>
                    <div class="action-btns">
                        <button class="btn-action btn-edit" onclick='openEditModal(${JSON.stringify(student).replace(/'/g, "&apos;")})'>
                            <i class='bx bx-pencil'></i> Edit
                        </button>
                        <button class="btn-action btn-delete" onclick="openDeleteModal(${student.id}, '${escapeHtml(student.full_name || student.username)}', '${escapeHtml(usnDisplay)}')">
                            <i class='bx bx-trash'></i> Delete
                        </button>
                    </div>
                </td>
            </tr>
        `;
        
        // Mobile Card
        mobileHtml += `
            <div class="mobile-card">
                <div class="mc-header">
                    <div>
                        <div class="mc-user">${escapeHtml(student.full_name || student.username)}</div>
                        <div class="mc-usn">${escapeHtml(usnDisplay)}</div>
                    </div>
                    ${statusHtml}
                </div>
                <div class="mc-body">
                    <div>Added On: ${dateStr}</div>
                </div>
                <div class="mc-actions">
                    <button class="btn-action btn-edit" onclick='openEditModal(${JSON.stringify(student).replace(/'/g, "&apos;")})'>
                        <i class='bx bx-pencil'></i> Edit
                    </button>
                    <button class="btn-action btn-delete" onclick="openDeleteModal(${student.id}, '${escapeHtml(student.full_name || student.username)}', '${escapeHtml(usnDisplay)}')">
                        <i class='bx bx-trash'></i> Delete
                    </button>
                </div>
            </div>
        `;
    });
    
    tbody.innerHTML = tableHtml;
    mobileContainer.innerHTML = mobileHtml;
}

function renderPagination(total) {
    const totalPages = Math.ceil(total / limit) || 1;
    const start = total === 0 ? 0 : ((currentPage - 1) * limit) + 1;
    const end = Math.min(currentPage * limit, total);
    
    document.getElementById('paginationInfo').textContent = `Showing ${start} to ${end} of ${total} students`;
    
    const controls = document.getElementById('paginationControls');
    let html = '';
    
    // Prev
    html += `<button class="page-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})"><i class='bx bx-chevron-left'></i></button>`;
    
    // Page Numbers (simplified logic for compactness)
    for (let i = 1; i <= totalPages; i++) {
        // Only show close pages
        if (i === 1 || i === totalPages || (i >= currentPage - 1 && i <= currentPage + 1)) {
            html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="changePage(${i})">${i}</button>`;
        } else if (i === currentPage - 2 || i === currentPage + 2) {
            html += `<button class="page-btn" disabled>...</button>`;
        }
    }
    
    // Next
    html += `<button class="page-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})"><i class='bx bx-chevron-right'></i></button>`;
    
    controls.innerHTML = html;
}

function changePage(page) {
    currentPage = page;
    loadStudents();
}

// Search & Filter
function debounceSearch() {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        currentPage = 1;
        loadStudents();
    }, 300);
}

function applyFilters() {
    currentPage = 1;
    loadStudents();
}

function clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('statusFilter').value = 'all';
    document.getElementById('sortOrder').value = 'newest';
    currentPage = 1;
    loadStudents();
}

function updateTotalStudents(count) {
    const statEl = document.getElementById('totalStudentsStat');
    const badgeEl = document.getElementById('totalStudentsBadge');
    if (statEl) statEl.textContent = count;
    if (badgeEl) badgeEl.textContent = count;
}

function showErrorState(message) {
    const tbody = document.getElementById('studentsTableBody');
    const mobileContainer = document.getElementById('mobileCardsContainer');
    const errorHtml = `
        <tr>
            <td colspan="6">
                <div class="empty-state">
                    <i class='bx bx-error-circle' style="color: #e11d48;"></i>
                    <h3 style="color: #e11d48;">Error</h3>
                    <p>${escapeHtml(message)}</p>
                    <button class="btn-secondary" onclick="loadStudents()">Retry</button>
                </div>
            </td>
        </tr>
    `;
    tbody.innerHTML = errorHtml;
    mobileContainer.innerHTML = errorHtml;
}

// Modals
function closeModal(id) {
    document.getElementById(id).classList.remove('show');
}

function openEditModal(student) {
    document.getElementById('studentForm').reset();
    document.getElementById('studentId').value = student.id;
    document.getElementById('studentUsername').value = student.full_name || student.username;
    document.getElementById('studentUSN').value = student.usn || '';
    
    document.getElementById('statusGroup').style.display = 'block';
    document.getElementById('studentStatus').value = student.status;
    
    document.getElementById('formModalTitle').textContent = 'Edit Student';
    document.getElementById('formModalSubtitle').textContent = 'Update student details.';
    document.getElementById('formSubmitBtn').textContent = 'Save Changes';
    
    document.getElementById('studentFormModal').classList.add('show');
}

function openDeleteModal(id, username, usn) {
    document.getElementById('deleteStudentId').value = id;
    document.getElementById('deleteUsername').textContent = username;
    document.getElementById('deleteUSN').textContent = usn;
    document.getElementById('deleteModal').classList.add('show');
}

// CRUD Operations
async function addStudentInline(event) {
    event.preventDefault();
    const btn = document.getElementById('inlineSubmitBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = 'Saving...';
    btn.disabled = true;
    
    const payload = {
        full_name: document.getElementById('inlineUsername').value,
        usn: document.getElementById('inlineUSN').value,
        status: 1
    };
    
    try {
        const data = await fetchAPI(`/students`, {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        
        if (data.status === 'success') {
            document.getElementById('inlineAddStudentForm').reset();
            showToast('Student added successfully.', 'success');
            loadStudents();
        } else {
            showToast(data.message || 'Unable to add student.', 'error');
        }
    } catch (error) {
        showToast('Network error occurred.', 'error');
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

async function saveStudent(event) {
    event.preventDefault();
    const btn = document.getElementById('formSubmitBtn');
    const originalText = btn.textContent;
    btn.textContent = 'Saving...';
    btn.disabled = true;
    
    const id = document.getElementById('studentId').value;
    
    const payload = {
        full_name: document.getElementById('studentUsername').value,
        usn: document.getElementById('studentUSN').value,
        status: document.getElementById('studentStatus').value
    };
    
    try {
        const data = await fetchAPI(`/students/${id}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        
        if (data.status === 'success') {
            closeModal('studentFormModal');
            showToast('Student updated successfully.', 'success');
            loadStudents();
        } else {
            showToast(data.message || 'Unable to complete the request.', 'error');
        }
    } catch (error) {
        showToast('Network error occurred.', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

async function confirmDeleteStudent() {
    const id = document.getElementById('deleteStudentId').value;
    const btn = document.querySelector('#deleteModal .btn-primary');
    const originalText = btn.textContent;
    btn.textContent = 'Deleting...';
    btn.disabled = true;
    
    try {
        const data = await fetchAPI(`/students/${id}`, {
            method: 'DELETE'
        });
        
        if (data.status === 'success') {
            closeModal('deleteModal');
            showToast('Student deleted successfully.', 'success');
            
            // Adjust page if deleting last item
            const tbody = document.getElementById('studentsTableBody');
            if (tbody.children.length === 1 && currentPage > 1) {
                currentPage--;
            }
            
            loadStudents();
        } else {
            showToast(data.message || 'Unable to delete student.', 'error');
        }
    } catch (error) {
        showToast('Network error occurred.', 'error');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

// Toasts
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'bx-check-circle' : 'bx-error-circle';
    
    toast.innerHTML = `
        <i class='bx ${icon} toast-icon'></i>
        <div class="toast-message">${escapeHtml(message)}</div>
    `;
    
    container.appendChild(toast);
    
    // Animate in
    setTimeout(() => toast.classList.add('show'), 10);
    
    // Remove after 3s
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
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
