/**
 * Navigation and Authentication Management
 * Global script to manage navigation and auth state across all pages
 */

// Object containing all navigation and auth logic
const SectifyNavigation = {
    // Token keys
    TOKEN_KEYS: {
        access: 'accessToken',
        user: 'userName',
        // Legacy keys for backward compatibility
        legacyToken: 'sectify_token',
        legacyEmail: 'sectify_user_email',
        legacyName: 'sectify_user_name'
    },

    // DOM selectors
    selectors: {
        guestNav: '#guest-nav',
        userNav: '#user-nav',
        userGreeting: '#user-greeting',
        logoutBtn: '#logout-btn',
        loginBtn: '#login-btn',
        signupBtn: '#signup-btn',
        loginModal: '#login-modal',
        signupModal: '#signup-modal',
        closeModal: '.close-modal'
    },

    // Initialize navigation
    init() {
        this.checkAuthState();
        this.bindEvents();
        this.updateNavigation();
    },

    // Check current authentication state
    checkAuthState() {
        return localStorage.getItem(this.TOKEN_KEYS.access) || 
               localStorage.getItem(this.TOKEN_KEYS.legacyToken);
    },

    // Get current user name
    getCurrentUser() {
        return localStorage.getItem(this.TOKEN_KEYS.user) || 
               localStorage.getItem(this.TOKEN_KEYS.legacyName);
    },

    // Update navigation based on auth state
    updateNavigation() {
        const token = this.checkAuthState();
        const userName = this.getCurrentUser();
        
        const guestNav = document.querySelector(this.selectors.guestNav);
        const userNav = document.querySelector(this.selectors.userNav);
        const userGreeting = document.querySelector(this.selectors.userGreeting);

        if (token && userName) {
            // User is logged in
            if (guestNav) guestNav.classList.add('hidden');
            if (userNav) userNav.classList.remove('hidden');
            if (userGreeting) userGreeting.textContent = `Welcome, ${userName}`;
        } else {
            // User is guest
            if (guestNav) guestNav.classList.remove('hidden');
            if (userNav) userNav.classList.add('hidden');
        }
    },

    // Handle logout
    logout() {
        // Clear all authentication data
        Object.values(this.TOKEN_KEYS).forEach(key => {
            localStorage.removeItem(key);
        });
        
        // Redirect to home
        window.location.href = '/';
    },

    // Handle login success
    onLoginSuccess(accessToken, userName) {
        localStorage.setItem(this.TOKEN_KEYS.access, accessToken);
        if (userName) {
            localStorage.setItem(this.TOKEN_KEYS.user, userName);
        }
        this.updateNavigation();
    },

    // Fetch user data from API
    async fetchUserData() {
        const token = this.checkAuthState();
        if (!token) return null;

        try {
            const response = await fetch('/api/v1/users/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (response.ok) {
                const user = await response.json();
                localStorage.setItem(this.TOKEN_KEYS.user, user.name);
                this.updateNavigation();
                return user;
            } else if (response.status === 401) {
                // Token invalid, logout
                this.logout();
                return null;
            }
        } catch (error) {
            console.error('Error fetching user data:', error);
        }
        return null;
    },

    // Show toast notification
    showToast(message, isError = true) {
        const toast = document.createElement('div');
        toast.textContent = message;
        toast.className = `fixed bottom-5 right-5 p-4 rounded-lg shadow-lg text-white z-50 ${
            isError ? 'bg-red-600' : 'bg-green-600'
        }`;
        document.body.appendChild(toast);
        setTimeout(() => toast.remove(), 3000);
    },

    // Bind all events
    bindEvents() {
        // Logout button
        const logoutBtn = document.querySelector(this.selectors.logoutBtn);
        if (logoutBtn) {
            logoutBtn.removeEventListener('click', this.logout.bind(this));
            logoutBtn.addEventListener('click', this.logout.bind(this));
        }

        // Modal events (if present)
        this.bindModalEvents();
    },

    // Bind modal events for login/signup
    bindModalEvents() {
        const loginBtn = document.querySelector(this.selectors.loginBtn);
        const signupBtn = document.querySelector(this.selectors.signupBtn);
        const loginModal = document.querySelector(this.selectors.loginModal);
        const signupModal = document.querySelector(this.selectors.signupModal);
        const closeButtons = document.querySelectorAll(this.selectors.closeModal);

        if (loginBtn && loginModal) {
            loginBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showModal(loginModal);
            });
        }

        if (signupBtn && signupModal) {
            signupBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.showModal(signupModal);
            });
        }

        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                if (loginModal) this.hideModal(loginModal);
                if (signupModal) this.hideModal(signupModal);
            });
        });
    },

    // Modal utilities
    showModal(modal) {
        if (modal) modal.classList.remove('hidden');
    },

    hideModal(modal) {
        if (modal) modal.classList.add('hidden');
    },

    // Check if user should have access to protected pages
    requireAuth() {
        const token = this.checkAuthState();
        if (!token) {
            this.showToast('Please log in to access this page.');
            setTimeout(() => window.location.href = '/', 1000);
            return false;
        }
        return true;
    }
};

// Auto-initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    SectifyNavigation.init();
    
    // If user data is missing but token exists, fetch it
    const token = SectifyNavigation.checkAuthState();
    const userName = SectifyNavigation.getCurrentUser();
    
    if (token && !userName) {
        SectifyNavigation.fetchUserData();
    }
});

// Export for use in other scripts
window.SectifyNavigation = SectifyNavigation; 