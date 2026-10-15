document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentPage = 1;
    const limit = 7;
    let searchTimeout = null;
    
    // Auth Check
    const token = localStorage.getItem('teacher_token');
    if (!token) {
        window.location.href = 'index.html';
        return;
    }

    const headers = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };

    // DOM Elements
    const addForm = document.getElementById('addStudentForm');
    const tableBody = document.getElementById('studentsTableBody');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.querySelector('table');
    const totalCount = document.getElementById('totalStudentsCount');
    
    // Filters
    const searchInput = document.getElementById('tableSearch');
    const statusFilter = document.getElementById('statusFilter');
    const sortFilter = document.getElementById('sortFilter');
    const clearFiltersBtn = document.getElementById('clearFiltersBtn');
    
    // Mobile Menu
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const navLinks = document.getElementById('navLinks');
    
    // Modals
    const editModal = document.getElementById('editModal');
    const deleteModal = document.getElementById('deleteModal');
    const editForm = document.getElementById('editStudentForm');
    
    // Initialize
    updateDateTime();
    setInterval(updateDateTime, 60000); // Update every minute
    loadStudents();

    // Event Listeners
    mobileMenuBtn.addEventListener('click', () => navLinks.classList.toggle('show'));
    
    // Form submission
    addForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('newUsername').value.trim();
        const usn = document.getElementById('newUsn').value.trim().toUpperCase();
        
        // Reset errors
        document.getElementById('usernameError').textContent = '';
        document.getElementById('usnError').textContent = '';
        
        try {
            const res = await fetch('http://localhost:8000/api/students', {
                method: 'POST',
                headers,
                body: JSON.stringify({ username, usn })
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast('Student added successfully');
                addForm.reset();
                loadStudents();
            } else {
                if (data.detail.toLowerCase().includes('username')) {
                    document.getElementById('usernameError').textContent = data.detail;
                } else if (data.detail.toLowerCase().includes('usn')) {
                    document.getElementById('usnError').textContent = data.detail;
                } else {
                    showToast(data.detail, true);
                }
            }
        } catch (err) {
            showToast('Failed to add student. Server error.', true);
        }
    });

    // Filters
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentPage = 1;
            loadStudents();
        }, 300);
    });
    
    statusFilter.addEventListener('change', () => { currentPage = 1; loadStudents(); });
    sortFilter.addEventListener('change', () => { currentPage = 1; loadStudents(); });
    
    clearFiltersBtn.addEventListener('click', () => {
        searchInput.value = '';
        statusFilter.value = 'All Students';
        sortFilter.value = 'Newest';
        currentPage = 1;
        loadStudents();
    });

    // Edit Modal
    document.getElementById('closeEditModal').addEventListener('click', () => editModal.classList.remove('active'));
    document.getElementById('cancelEditBtn').addEventListener('click', () => editModal.classList.remove('active'));
    
    document.getElementById('saveEditBtn').addEventListener('click', async () => {
        const id = document.getElementById('editStudentId').value;
        const username = document.getElementById('editUsername').value.trim();
        const usn = document.getElementById('editUsn').value.trim().toUpperCase();
        
        document.getElementById('editUsernameError').textContent = '';
        document.getElementById('editUsnError').textContent = '';
        
        if (username.length < 3) {
            document.getElementById('editUsernameError').textContent = 'Username must be at least 3 characters';
            return;
        }
        
        try {
            const res = await fetch(`http://localhost:8000/api/students/${id}`, {
                method: 'PUT',
                headers,
                body: JSON.stringify({ username, usn })
            });
            const data = await res.json();
            
            if (res.ok) {
                showToast('Student updated successfully');
                editModal.classList.remove('active');
                loadStudents();
            } else {
                if (data.detail.toLowerCase().includes('username')) {
                    document.getElementById('editUsernameError').textContent = data.detail;
                } else if (data.detail.toLowerCase().includes('usn')) {
                    document.getElementById('editUsnError').textContent = data.detail;
                } else {
                    showToast(data.detail, true);
                }
            }
        } catch (err) {
            showToast('Failed to update student.', true);
        }
    });

    // Delete Modal
    document.getElementById('closeDeleteModal').addEventListener('click', () => deleteModal.classList.remove('active'));
    document.getElementById('cancelDeleteBtn').addEventListener('click', () => deleteModal.classList.remove('active'));
    
    document.getElementById('confirmDeleteBtn').addEventListener('click', async () => {
        const id = document.getElementById('deleteStudentId').value;
        try {
            const res = await fetch(`http://localhost:8000/api/students/${id}`, {
                method: 'DELETE',
                headers
            });
            if (res.ok) {
                showToast('Student deleted successfully');
                deleteModal.classList.remove('active');
                loadStudents();
            } else {
                showToast('Failed to delete student.', true);
            }
        } catch (err) {
            showToast('Failed to delete student.', true);
        }
    });

    // Main Functions
    async function loadStudents() {
        const search = encodeURIComponent(searchInput.value.trim());
        const status = encodeURIComponent(statusFilter.value);
        const sort = encodeURIComponent(sortFilter.value);
        
        try {
            const res = await fetch(`http://localhost:8000/api/students?search=${search}&status=${status}&sort=${sort}&page=${currentPage}&limit=${limit}`, {
                headers
            });
            
            if (res.status === 401) {
                localStorage.removeItem('teacher_token');
                window.location.href = 'index.html';
                return;
            }
            
            const data = await res.json();
            renderStudents(data.students);
            renderPagination(data.pagination);
            
            totalCount.textContent = data.pagination.total;
            
        } catch (err) {
            console.error("Error loading students:", err);
            tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:red;">Unable to load students.</td></tr>`;
        }
    }

    function renderStudents(students) {
        tableBody.innerHTML = '';
        
        if (!students || students.length === 0) {
            tableContainer.style.display = 'none';
            emptyState.style.display = 'block';
            return;
        }
        
        tableContainer.style.display = 'table';
        emptyState.style.display = 'none';
        
        students.forEach((s, index) => {
            const rowNumber = ((currentPage - 1) * limit) + index + 1;
            
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${rowNumber}</td>
                <td class="fw-500">${s.username}</td>
                <td>${s.usn}</td>
                <td>${s.created_at_str}</td>
                <td>
                    <div class="status-pill ${s.is_active ? 'active' : 'inactive'}">
                        <div class="dot"></div>
                        ${s.status}
                    </div>
                </td>
                <td class="actions-col">
                    <div class="action-buttons">
                        <button class="btn-action edit" data-id="${s.id}" data-username="${s.username}" data-usn="${s.usn}">
                            <i class='bx bx-pencil'></i> Edit
                        </button>
                        <button class="btn-action delete" data-id="${s.id}" data-username="${s.username}" data-usn="${s.usn}">
                            <i class='bx bx-trash'></i> Delete
                        </button>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Attach action listeners
        document.querySelectorAll('.btn-action.edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget;
                document.getElementById('editStudentId').value = target.dataset.id;
                document.getElementById('editUsername').value = target.dataset.username;
                document.getElementById('editUsn').value = target.dataset.usn;
                document.getElementById('editUsernameError').textContent = '';
                document.getElementById('editUsnError').textContent = '';
                editModal.classList.add('active');
            });
        });
        
        document.querySelectorAll('.btn-action.delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const target = e.currentTarget;
                document.getElementById('deleteStudentId').value = target.dataset.id;
                document.getElementById('deleteUsername').textContent = target.dataset.username;
                document.getElementById('deleteUsn').textContent = target.dataset.usn;
                deleteModal.classList.add('active');
            });
        });
    }

    function renderPagination(pageData) {
        const info = document.getElementById('paginationInfo');
        const controls = document.getElementById('paginationControls');
        
        if (pageData.total === 0) {
            info.textContent = 'Showing 0 students';
            controls.innerHTML = '';
            return;
        }
        
        const start = ((pageData.page - 1) * pageData.limit) + 1;
        const end = Math.min(start + pageData.limit - 1, pageData.total);
        info.textContent = `Showing ${start} to ${end} of ${pageData.total} students`;
        
        let html = '';
        html += `<button class="page-btn" ${pageData.page === 1 ? 'disabled' : ''} data-page="${pageData.page - 1}"><i class='bx bx-chevron-left'></i></button>`;
        
        for (let i = 1; i <= pageData.total_pages; i++) {
            if (pageData.total_pages > 5) {
                if (i === 1 || i === pageData.total_pages || (i >= pageData.page - 1 && i <= pageData.page + 1)) {
                    html += `<button class="page-btn ${i === pageData.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
                } else if (i === pageData.page - 2 || i === pageData.page + 2) {
                    html += `<button class="page-btn" disabled>...</button>`;
                }
            } else {
                html += `<button class="page-btn ${i === pageData.page ? 'active' : ''}" data-page="${i}">${i}</button>`;
            }
        }
        
        html += `<button class="page-btn" ${pageData.page === pageData.total_pages ? 'disabled' : ''} data-page="${pageData.page + 1}"><i class='bx bx-chevron-right'></i></button>`;
        
        controls.innerHTML = html;
        
        controls.querySelectorAll('.page-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const p = parseInt(e.currentTarget.dataset.page);
                if (p && p !== currentPage) {
                    currentPage = p;
                    loadStudents();
                }
            });
        });
    }

    function updateDateTime() {
        const now = new Date();
        const dateOptions = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' };
        const timeOptions = { hour: '2-digit', minute: '2-digit', hour12: true };
        
        document.getElementById('currentDate').textContent = now.toLocaleDateString('en-GB', dateOptions).replace(/,/g, '');
        document.getElementById('currentTime').textContent = now.toLocaleTimeString('en-US', timeOptions);
    }

    function showToast(message, isError = false) {
        const toast = document.getElementById('toast');
        const msg = document.getElementById('toastMessage');
        const icon = toast.querySelector('i');
        
        msg.textContent = message;
        if (isError) {
            toast.style.borderLeftColor = 'var(--color-danger)';
            icon.className = 'bx bx-error-circle';
            icon.style.color = 'var(--color-danger)';
        } else {
            toast.style.borderLeftColor = 'var(--color-success)';
            icon.className = 'bx bx-check-circle';
            icon.style.color = 'var(--color-success)';
        }
        
        toast.classList.add('show');
        setTimeout(() => toast.classList.remove('show'), 3000);
    }
});
