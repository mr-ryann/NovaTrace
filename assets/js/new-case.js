// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Initialize the application
    initializeApp();
    
    // Check authentication
    checkAuthentication();
});

// State Management
const state = {
    caseDetails: {
        caseNumber: '',
        caseName: '',
        priority: 'medium',
        status: 'open',
        dateReceived: '',
        examiner: '',
        requestingAgency: '',
        description: ''
    }
};

// Initialize Application
function initializeApp() {
    // Set current date
    updateCurrentDate();
    
    // Setup event listeners
    setupEventListeners();
}

// Event Listeners Setup
function setupEventListeners() {
    // Form submission
    const form = document.getElementById('caseForm');
    form.addEventListener('submit', handleSubmit);
    
    // Reset button
    const resetButton = document.getElementById('resetButton');
    resetButton.addEventListener('click', resetForm);
    
    // Input change handlers
    setupInputListeners();
}

// Input Change Handlers
function setupInputListeners() {
    // Get all form inputs
    const inputs = document.querySelectorAll('input, select, textarea');
    
    inputs.forEach(input => {
        input.addEventListener('change', (e) => {
            handleInputChange(e.target.name, e.target.value);
        });
    });
}

// Handle Input Changes
function handleInputChange(name, value) {
    state.caseDetails[name] = value;
}

// Form Submission Handler
async function handleSubmit(e) {
    e.preventDefault();
    
    // Get all form data
    const formData = new FormData(e.target);
    const caseData = Object.fromEntries(formData.entries());
    
    try {
        // Show loading state on submit button
        const submitButton = e.target.querySelector('button[type="submit"]');
        setLoadingState(submitButton, true);
        
        // Simulate API call
        await submitCaseData(caseData);
        
        // Store case data in localStorage for folder upload page
        localStorage.setItem('currentCase', JSON.stringify(caseData));
        
        // Show success message with loading indicator
        const successMessage = document.createElement('div');
        successMessage.className = 'success-message';
        successMessage.innerHTML = `
            <div class="success-content">
                <i data-lucide="check-circle" class="success-icon"></i>
                <p>Case created successfully!</p>
                <p class="loading-text">
                    <i data-lucide="loader-2" class="h-4 w-4 animate-spin"></i>
                    Redirecting to evidence upload...
                </p>
            </div>
        `;
        document.body.appendChild(successMessage);
        lucide.createIcons();

        // Wait for 2 seconds before redirecting
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Change this line from /home to /folder-upload
        navigate('/folder-upload');
        
    } catch (error) {
        alert('Failed to create case. Please try again.');
        console.error('Error submitting case:', error);
    } finally {
        setLoadingState(submitButton, false);
    }
}
// Reset Form Handler
function resetForm() {
    // Reset state
    state.caseDetails = {
        caseNumber: '',
        caseName: '',
        priority: 'medium',
        status: 'open',
        dateReceived: '',
        examiner: '',
        requestingAgency: '',
        description: ''
    };
    
    // Reset form fields
    const form = document.getElementById('caseForm');
    form.reset();
}

// Helper Functions
function updateCurrentDate() {
    const currentDate = document.getElementById('currentDate');
    currentDate.textContent = formatDate(new Date());
}

function formatDate(date) {
    return new Intl.DateTimeFormat('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    }).format(date);
}

function setLoadingState(button, isLoading) {
    if (isLoading) {
        const originalContent = button.innerHTML;
        button.setAttribute('data-original-content', originalContent);
        button.innerHTML = '<i data-lucide="loader-2" class="h-4 w-4 animate-spin"></i>';
        button.disabled = true;
    } else {
        const originalContent = button.getAttribute('data-original-content');
        button.innerHTML = originalContent;
        button.removeAttribute('data-original-content');
        button.disabled = false;
    }
    
    // Reinitialize icons
    lucide.createIcons();
}

// API Simulation
async function submitCaseData(data) {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    // Simulate success
    console.log('Case details submitted:', data);
    return true;
}

// Authentication Check
function checkAuthentication() {
    if (!localStorage.getItem('isLoggedIn')) {
        navigate('/');
        return;
    }
}
