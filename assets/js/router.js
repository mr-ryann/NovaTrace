// Router configuration
const routes = {
    '/': 'landing.html',
    '/home': 'home.html',
    '/tool': 'tool.html',
    '/new-case': 'new-case.html',
    '/folder-upload': 'folder-upload.html',
    '/existing-cases': 'existing-cases.html',
    '/completed-cases': 'completed-cases.html'
};

// Check authentication status
function checkAuth() {
    return localStorage.getItem('isLoggedIn') === 'true';
}

// Navigation function
function navigate(path) {
    const file = routes[path] || routes['/'];
    window.location.href = file;
}

// Export for global use
window.navigate = navigate;
window.checkAuth = checkAuth;