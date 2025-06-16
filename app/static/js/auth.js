document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements
    const loginBtn = document.getElementById('login-btn');
    const signupBtn = document.getElementById('signup-btn');
    const loginModal = document.getElementById('login-modal');
    const signupModal = document.getElementById('signup-modal');
    const closeButtons = document.querySelectorAll('.close-modal');
    const loginForm = document.getElementById('login-form');
    const signupForm = document.getElementById('signup-form');
    const userNav = document.getElementById('user-nav');
    const guestNav = document.getElementById('guest-nav');
    const userGreeting = document.getElementById('user-greeting');
    const logoutBtn = document.getElementById('logout-btn');

    // Function to show modal
    const showModal = (modal) => {
        if (modal) {
            modal.classList.remove('hidden');
            console.log('Showing modal:', modal.id);
        }
    };
    
    // Function to hide modal
    const hideModal = (modal) => {
        if (modal) {
            modal.classList.add('hidden');
            console.log('Hiding modal:', modal.id);
        }
    };

    // Function to hide all modals
    const hideAllModals = () => {
        hideModal(loginModal);
        hideModal(signupModal);
    };

    // Assign events to main buttons
    loginBtn?.addEventListener('click', (e) => { 
        e.preventDefault(); 
        console.log('Login button clicked');
        hideAllModals();
        showModal(loginModal); 
    });
    
    signupBtn?.addEventListener('click', (e) => { 
        e.preventDefault(); 
        console.log('Signup button clicked');
        hideAllModals();
        showModal(signupModal); 
    });

    // Assign events to close modal buttons
    closeButtons.forEach(button => {
        button.addEventListener('click', () => {
            console.log('Close button clicked');
            hideAllModals();
        });
    });

    // Close modal on outside click
    [loginModal, signupModal].forEach(modal => {
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    hideAllModals();
                }
            });
        }
    });

    // Create and add modal switch links
    function addSwitchLinks() {
        if (loginModal && signupModal) {
            const loginFormContainer = loginModal.querySelector('form')?.parentElement;
            const signupFormContainer = signupModal.querySelector('form')?.parentElement;
            
            if (loginFormContainer && signupFormContainer) {
                // Remove old links if they exist
                const oldSwitchLinks = document.querySelectorAll('.modal-switch-link');
                oldSwitchLinks.forEach(link => link.remove());

                // Create link to switch from login to signup
                const switchToSignupElement = document.createElement('p');
                switchToSignupElement.className = 'text-center mt-4 text-gray-400 modal-switch-link';
                switchToSignupElement.innerHTML = 'Don\'t have an account? <a href="#" class="text-green-400 hover:text-green-300">Sign up</a>';
                
                // Create link to switch from signup to login
                const switchToLoginElement = document.createElement('p');
                switchToLoginElement.className = 'text-center mt-4 text-gray-400 modal-switch-link';
                switchToLoginElement.innerHTML = 'Already have an account? <a href="#" class="text-green-400 hover:text-green-300">Log in</a>';

                // Add to container
                loginFormContainer.appendChild(switchToSignupElement);
                signupFormContainer.appendChild(switchToLoginElement);

                // Assign event listeners
                switchToSignupElement.querySelector('a')?.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('Switching to signup');
                    hideModal(loginModal);
                    showModal(signupModal);
                });

                switchToLoginElement.querySelector('a')?.addEventListener('click', (e) => {
                    e.preventDefault();
                    console.log('Switching to login');
                    hideModal(signupModal);
                    showModal(loginModal);
                });
            }
        }
    }

    // Add switch links after DOM loads
    setTimeout(addSwitchLinks, 100);

    // Function to show toast message
    const showToast = (message, isError = true) => {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.className = `fixed bottom-5 right-5 p-4 rounded-lg shadow-lg text-white ${isError ? 'bg-red-600' : 'bg-green-600'}`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    };

    // Handle signup form
    signupForm?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(signupForm);
        const data = Object.fromEntries(formData.entries());

        try {
            const response = await fetch('/api/v1/auth/signup', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Signup failed');
            }

            showToast('Signup successful! Please log in.', false);
            // Reset form
            signupForm.reset();
            // Switch to login modal
            hideModal(signupModal);
            showModal(loginModal);
        } catch (error) {
            showToast(error.message);
        }
    });

    // Handle login form with 2FA logic
    let mfaToken = null;

    loginForm?.addEventListener('submit', async (e) => {
        e.preventDefault();

        const passwordField = document.getElementById('password-field');
        const totpField = document.getElementById('totp-field');
        const submitButton = loginForm.querySelector('button[type="submit"]');

        // --- Step 2: Verify 2FA code ---
        if (mfaToken) {
            const totpCode = document.getElementById('login-totp').value;
            if (!totpCode || totpCode.length !== 6) {
                showToast('Please enter a valid 6-digit code.');
                return;
            }

            try {
                const response = await fetch('/api/v1/auth/login/verify-2fa', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${mfaToken}`
                    },
                    body: JSON.stringify({ code: totpCode })
                });

                const result = await response.json();
                if (!response.ok) throw new Error(result.detail || '2FA verification failed.');

                localStorage.setItem('accessToken', result.access_token);
                showToast('Login successful! Redirecting...', false);
                hideAllModals();
                setTimeout(() => window.location.href = '/dashboard', 1000);

            } catch (error) {
                showToast(error.message);
                // Reset form to try again from the start
                mfaToken = null;
                passwordField?.classList.remove('hidden');
                totpField?.classList.add('hidden');
                if (submitButton) submitButton.textContent = 'Log In';
            }
            return;
        }

        // --- Step 1: Send email and password ---
        const formData = new FormData(loginForm);
        const body = new URLSearchParams();
        body.append('username', formData.get('email'));
        body.append('password', formData.get('password'));

        try {
            const response = await fetch('/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: body
            });

            const result = await response.json();
            if (!response.ok) throw new Error(result.detail || 'Login failed');

            // If 2FA is required
            if (result.mfa_required) {
                mfaToken = result.mfa_token;
                passwordField?.classList.add('hidden');
                totpField?.classList.remove('hidden');
                if (submitButton) submitButton.textContent = 'Verify 2FA Code';
                showToast('Please enter your 2FA code.', false);
            } else {
                // Login successful (no 2FA)
                localStorage.setItem('accessToken', result.access_token);
                showToast('Login successful! Redirecting...', false);
                hideAllModals();
                setTimeout(() => window.location.href = '/dashboard', 1000);
            }

        } catch (error) {
            showToast(error.message);
        }
    });

    // Handle logout
    const handleLogout = () => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('userName');
        localStorage.removeItem('sectify_token');
        localStorage.removeItem('sectify_user_email');
        localStorage.removeItem('sectify_user_name');
        updateNav(null);
        window.location.href = '/';
    };

    logoutBtn?.addEventListener('click', handleLogout);

    // Function to update navbar
    const updateNav = (userName) => {
        if (userName) {
            guestNav?.classList.add('hidden');
            userNav?.classList.remove('hidden');
            if (userGreeting) userGreeting.textContent = `Welcome, ${userName}`;
        } else {
            guestNav?.classList.remove('hidden');
            userNav?.classList.add('hidden');
        }
    };

    // Check login status when page loads
    const checkLoginStatus = () => {
        const token = localStorage.getItem('accessToken');
        const userName = localStorage.getItem('userName');
        if (token && userName) {
            updateNav(userName);
        } else {
            updateNav(null);
        }
    };

    checkLoginStatus();
});
