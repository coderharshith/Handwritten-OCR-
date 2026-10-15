document.addEventListener('DOMContentLoaded', () => {
    
    // Toggle Password Visibility
    window.togglePassword = function(inputId) {
        const input = document.getElementById(inputId);
        const icon = input.nextElementSibling;
        
        if (input.type === 'password') {
            input.type = 'text';
            icon.classList.remove('bx-show');
            icon.classList.add('bx-hide');
        } else {
            input.type = 'password';
            icon.classList.remove('bx-hide');
            icon.classList.add('bx-show');
        }
    };

    // Generic Login Handler
    async function handleLogin(e, type) {
        e.preventDefault();
        
        const form = e.target;
        const submitBtn = form.querySelector('button[type="submit"]');
        const errorDiv = document.getElementById(`${type}-error`);
        
        const originalBtnHTML = submitBtn.innerHTML;
        
        // Form Data
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Basic frontend validation
        if (!data.username || !data.password) {
            showError(errorDiv, "Please fill in all fields.");
            return;
        }
        
        // Loading State
        submitBtn.disabled = true;
        submitBtn.innerHTML = `<i class='bx bx-loader-alt bx-spin'></i> <span>Signing in...</span>`;
        errorDiv.style.display = 'none';
        
        try {
            // Using standard OAuth2 form encoding format for FastAPI OAuth2PasswordRequestForm
            const body = new URLSearchParams();
            body.append('username', data.username);
            body.append('password', data.password);
            
            const response = await fetch(`/api/auth/${type}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: body
            });
            
            if (response.ok) {
                const result = await response.json();
                // Store token and role
                localStorage.setItem(`${type}_token`, result.access_token);
                // Redirect to dashboard
                window.location.href = `/${type}-dashboard.html`;
            } else {
                const errorData = await response.json();
                let errMsg = "Invalid credentials.";
                if (errorData.detail) {
                    // Clean error message
                    errMsg = typeof errorData.detail === 'string' ? errorData.detail : "Login failed. Please try again.";
                }
                showError(errorDiv, errMsg);
            }
        } catch (error) {
            console.error('Login Error:', error);
            showError(errorDiv, "Network error. Please try again.");
        } finally {
            // Restore button state
            submitBtn.disabled = false;
            submitBtn.innerHTML = originalBtnHTML;
        }
    }
    
    function showError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
        element.classList.add('fade-in');
        
        // Remove animation class after it plays so it can play again
        setTimeout(() => {
            element.classList.remove('fade-in');
        }, 600);
    }

    // Attach Event Listeners
    const studentForm = document.getElementById('student-login-form');
    if (studentForm) {
        studentForm.addEventListener('submit', (e) => handleLogin(e, 'student'));
    }
    
    const teacherForm = document.getElementById('teacher-login-form');
    if (teacherForm) {
        teacherForm.addEventListener('submit', (e) => handleLogin(e, 'teacher'));
    }
});
