document.addEventListener('DOMContentLoaded', () => {
    // Use a consistent token key with auth.js
    const token = localStorage.getItem('accessToken') || localStorage.getItem('sectify_token');
    const guestNav = document.getElementById('guest-nav');
    const userNav = document.getElementById('user-nav');
    const logoutBtn = document.getElementById('logout-btn');
    const userGreeting = document.getElementById('user-greeting');

    // Consistent logout handler function
    const handleLogout = () => {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('userName');
        // Also clear old tokens if they exist (for backward compatibility)
        localStorage.removeItem('sectify_token');
        localStorage.removeItem('sectify_user_email');
        localStorage.removeItem('sectify_user_name');
        window.location.href = '/';
    };

    // Function to update nav based on login status
    const updateNavigation = async () => {
        if (token) {
            // User is logged in
            if (guestNav) guestNav.classList.add('hidden');
            if (userNav) userNav.classList.remove('hidden');
            
            // Fetch user info if userGreeting exists and userName is missing
            if (userGreeting && !localStorage.getItem('userName')) {
                try {
                    const response = await fetch('/api/v1/users/me', {
                        headers: { 'Authorization': `Bearer ${token}` }
                    });
                    
                    if (response.ok) {
                        const user = await response.json();
                        localStorage.setItem('userName', user.name);
                        userGreeting.textContent = `Welcome, ${user.name}`;
                    } else if (response.status === 401) {
                        // Invalid token, log out
                        handleLogout();
                        return;
                    }
                } catch (error) {
                    console.error('Error fetching user data:', error);
                }
            } else if (userGreeting && localStorage.getItem('userName')) {
                userGreeting.textContent = `Welcome, ${localStorage.getItem('userName')}`;
            }
            
            // Add logout functionality if the button exists on the page
            if (logoutBtn) {
                // Remove existing listeners to avoid duplicates
                logoutBtn.removeEventListener('click', handleLogout);
                logoutBtn.addEventListener('click', handleLogout);
            }
        } else {
            // User is a guest
            if (guestNav) guestNav.classList.remove('hidden');
            if (userNav) userNav.classList.add('hidden');
        }
    };

    updateNavigation();
});
