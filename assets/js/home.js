// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Initialize the application
    initializeApp();
});

// State Management
const state = {
    user: {
        name: "John Doe",
        email: "john.doe@company.com",
        role: "Senior Digital Forensics Investigator",
        lastLogin: "2024-11-19T08:30:00",
        notifications: 3
    },
    recentActivities: [
        {
            id: 1,
            type: "update",
            description: "Updated Case #2024-11-001 - Added new evidence items",
            timestamp: "2024-11-19T10:15:00"
        },
        {
            id: 2,
            type: "create",
            description: "Created new Case #2024-11-002 - Incident Response",
            timestamp: "2024-11-19T09:45:00"
        },
        {
            id: 3,
            type: "close",
            description: "Closed Case #2024-11-000 - Investigation complete",
            timestamp: "2024-11-18T16:30:00"
        }
    ],
    isSidebarCollapsed: false
};

// Initialize Application
function initializeApp() {
    // Setup event listeners
    setupEventListeners();
    
    // Initial render
    updateUserInterface();
    
    // Check authentication
    checkAuthentication();
}

// Event Listeners Setup
function setupEventListeners() {
    // Sidebar toggle
    document.getElementById('toggleSidebar').addEventListener('click', toggleSidebar);
    
    // Logout button
    document.getElementById('logoutButton').addEventListener('click', handleLogout);
    
    // Window resize handler
    window.addEventListener('resize', handleResize);

    // Quick action buttons
    setupQuickActionListeners();
}

// Authentication Check
function checkAuthentication() {
    // Check if user is logged in (you might want to check a token in localStorage)
    const isLoggedIn = localStorage.getItem('isLoggedIn');
    if (!isLoggedIn) {
        window.location.href = 'landing.html';
    }
}

// Sidebar Toggle Function
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggleSidebar');
    
    state.isSidebarCollapsed = !state.isSidebarCollapsed;
    
    if (state.isSidebarCollapsed) {
        sidebar.classList.add('collapsed');
        toggleBtn.innerHTML = '<i data-lucide="menu" class="h-6 w-6"></i>';
    } else {
        sidebar.classList.remove('collapsed');
        toggleBtn.innerHTML = '<i data-lucide="chevron-left" class="h-6 w-6"></i>';
    }
    
    // Reinitialize icons after changing the HTML
    lucide.createIcons();
}

// Logout Handler
async function handleLogout() {
    try {
        // Show loading state
        const logoutButton = document.getElementById('logoutButton');
        logoutButton.disabled = true;
        logoutButton.innerHTML = '<i data-lucide="loader-2" class="w-4 h-4 animate-spin"></i>';
        lucide.createIcons();

        // Simulate API call
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Clear local storage
        localStorage.clear();
        
        // Redirect to landing page
        window.location.href = 'landing.html';
    } catch (error) {
        console.error('Logout failed:', error);
        alert('Failed to logout. Please try again.');
    }
}


// Quick Actions Setup
function setupQuickActionListeners() {
    // Get the new case button by ID
    lucide.createIcons({
        attrs: {
            class: "w-4 h-4"
        }
    });
    document.getElementById('newCaseButton').addEventListener('click', () => {
        navigate('/new-case');
    });

    document.getElementById('openCasesButton').addEventListener('click', () => {
        navigate('/existing-cases');
    });

    document.getElementById('completedCasesButton').addEventListener('click', () => {
        navigate('/completed-cases');
    });

}

const quickActionButtons = document.querySelectorAll('.quick-action-button');
    quickActionButtons.forEach(button => {
        button.addEventListener('mouseenter', () => {
            button.classList.add('transform', 'scale-105', 'transition-transform');
        });
        
        button.addEventListener('mouseleave', () => {
            button.classList.remove('transform', 'scale-105', 'transition-transform');
        });
    });

// UI Update Functions
function updateUserInterface() {
    // Update user information
    document.getElementById('userName').textContent = state.user.name;
    document.getElementById('welcomeName').textContent = state.user.name;
    document.getElementById('userRole').textContent = state.user.role;
    document.getElementById('lastLogin').textContent = formatDate(state.user.lastLogin);
    document.getElementById('notificationCount').textContent = state.user.notifications;
    
    // Update recent activities
    updateRecentActivities();
}

function updateRecentActivities() {
    const activitiesContainer = document.getElementById('recentActivities');
    activitiesContainer.innerHTML = '';
    
    state.recentActivities.forEach(activity => {
        const activityElement = createActivityElement(activity);
        activitiesContainer.appendChild(activityElement);
    });
}

// Helper Functions
function createActivityElement(activity) {
    const div = document.createElement('div');
    div.className = 'flex items-start space-x-4 p-3 bg-gray-50 rounded-lg activity-card';
    
    div.innerHTML = `
        <div class="p-2 bg-white rounded-full activity-icon ${activity.type}">
            ${getActivityIcon(activity.type)}
        </div>
        <div class="flex-1">
            <p class="text-sm">${activity.description}</p>
            <p class="text-xs text-gray-500 mt-1">${formatDate(activity.timestamp)}</p>
        </div>
    `;
    
    return div;
}

function getActivityIcon(type) {
    const iconMap = {
        'update': '<i data-lucide="activity" class="h-4 w-4 text-blue-500"></i>',
        'create': '<i data-lucide="plus" class="h-4 w-4 text-green-500"></i>',
        'close': '<i data-lucide="check-square" class="h-4 w-4 text-purple-500"></i>'
    };
    
    return iconMap[type] || '<i data-lucide="clock" class="h-4 w-4 text-gray-500"></i>';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Responsive Handler
function handleResize() {
    const width = window.innerWidth;
    if (width < 768 && !state.isSidebarCollapsed) {
        toggleSidebar();
    }
}

// Prevent XSS
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
