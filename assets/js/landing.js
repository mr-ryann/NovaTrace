// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Setup event listeners
    setupEventListeners();
    
    // If already logged in, redirect to home
    if (checkAuth()) {
        navigate('/home');
    }
});

// State management
let isLoggedIn = false;

// DOM Elements
const loginDialog = document.getElementById('loginDialog');
const loginForm = document.getElementById('loginForm');
const loginButton = document.getElementById('loginButton');
const cancelLogin = document.getElementById('cancelLogin');
const submitLogin = document.getElementById('submitLogin');
const tryButton = document.getElementById('tryButton');
const ctaTryButton = document.getElementById('ctaTryButton');
const emailInput = document.getElementById('email');
const passwordInput = document.getElementById('password');

// Event Listeners Setup
function setupEventListeners() {
    // Login button in navigation
    loginButton.addEventListener('click', () => {
        if (isLoggedIn) {
            handleLogout();
        } else {
            showLoginDialog();
        }
    });

    // Login form submission
    loginForm.addEventListener('submit', handleLoginSubmit);

    // Cancel login button
    cancelLogin.addEventListener('click', hideLoginDialog);

    // Try Now buttons
    tryButton.addEventListener('click', handleTryButtonClick);
    ctaTryButton.addEventListener('click', handleTryButtonClick);

    // Close dialog when clicking outside
    loginDialog.addEventListener('click', (e) => {
        if (e.target === loginDialog) {
            hideLoginDialog();
        }
    });

    // Keyboard events for dialog
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !loginDialog.classList.contains('hidden')) {
            hideLoginDialog();
        }
    });
}

// Event Handlers
function handleTryButtonClick() {
    if (checkAuth()) {
        navigate('/home');
    } else {
        showLoginDialog();
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    
    // Show loading state
    setLoadingState(true);
    
    try {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1500));
        
        // Store login state
        localStorage.setItem('isLoggedIn', 'true');
        isLoggedIn = true;
        
        // Hide dialog
        hideLoginDialog();
        
        // Navigate to home
        navigate('/home');
        
    } catch (error) {
        alert('Login failed. Please try again.');
    } finally {
        setLoadingState(false);
    }
}

async function handleLogout() {
    try {
        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Clear login state
        localStorage.removeItem('isLoggedIn');
        isLoggedIn = false;
        
        // Redirect to landing
        navigate('/');
    } catch (error) {
        console.error('Logout failed:', error);
        alert('Failed to logout. Please try again.');
    }
}

// UI Helper Functions
function showLoginDialog() {
    loginDialog.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    emailInput.focus();
}

function hideLoginDialog() {
    loginDialog.classList.add('hidden');
    document.body.style.overflow = '';
    loginForm.reset();
    setLoadingState(false);
}

function setLoadingState(isLoading) {
    // Update login button state
    submitLogin.disabled = isLoading;
    
    // Toggle loading spinner and text
    const loadingText = submitLogin.querySelector('.loading-text');
    const loginText = submitLogin.querySelector('.login-text');
    
    if (isLoading) {
        loadingText.classList.remove('hidden');
        loginText.classList.add('hidden');
    } else {
        loadingText.classList.add('hidden');
        loginText.classList.remove('hidden');
    }
}

function updateLoggedInState(loggedIn) {
    isLoggedIn = loggedIn;
    
    // Update login button text
    loginButton.innerHTML = loggedIn ? 
        '<i data-lucide="log-out" class="mr-2 h-4 w-4"></i>Logout' :
        '<i data-lucide="log-in" class="mr-2 h-4 w-4"></i>Login';
        
    // Reinitialize icons for the new button content
    lucide.createIcons();
    
    // Update try now buttons
    tryButton.textContent = loggedIn ? 'Download Now' : 'Try Now';
    ctaTryButton.textContent = loggedIn ? 'Get Started Now' : 'Try Now';
}