// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide icons
    lucide.createIcons();
    
    // Initialize the application
    initializeApp();
});

// State Management
const state = {
    cases: [],
    currentPage: 1,
    itemsPerPage: 9,
    filters: {
        search: '',
        priority: 'all',
        status: 'all',
        assignee: 'all'
    },
    user: {
        name: "John Doe",
        role: "Senior Digital Forensics Investigator",
        id: "JD001"
    }
};

// Sample Data (Replace with actual API call)
const sampleCases = [
    {
        id: "2024-001",
        title: "Corporate Network Breach",
        openDate: "2024-01-15",
        dueDate: "2024-02-15",
        status: "in_progress",
        assignee: "John Doe",
        assigneeId: "JD001",
        description: "Investigating potential unauthorized access to corporate network",
        priority: "high",
        progress: 65,
        evidence: 12,
        tasks: {
            total: 8,
            completed: 5
        }
    },
    {
        id: "2024-002",
        title: "Ransomware Incident Analysis",
        openDate: "2024-01-18",
        dueDate: "2024-02-01",
        status: "open",
        assignee: "John Doe",
        assigneeId: "JD001",
        description: "Analysis of ransomware attack on client systems",
        priority: "high",
        progress: 25,
        evidence: 8,
        tasks: {
            total: 10,
            completed: 2
        }
    },
    {
        id: "2024-003",
        title: "Data Recovery Operation",
        openDate: "2024-01-20",
        dueDate: "2024-03-01",
        status: "pending",
        assignee: "Jane Smith",
        assigneeId: "JS001",
        description: "Recovery of corrupted database files from client servers",
        priority: "medium",
        progress: 90,
        evidence: 5,
        tasks: {
            total: 6,
            completed: 5
        }
    }
];

// Initialize Application
function initializeApp() {
    // Load initial data
    state.cases = sampleCases;
    
    // Setup event listeners
    setupEventListeners();
    
    // Initial render
    renderCases();
    updatePagination();
    
    // Update user info
    updateUserInfo();
}

// Event Listeners Setup
function setupEventListeners() {
    // Search input
    document.getElementById('searchInput').addEventListener('input', (e) => {
        state.filters.search = e.target.value;
        state.currentPage = 1;
        renderCases();
        updatePagination();
    });

    // Priority filter
    document.getElementById('priorityFilter').addEventListener('change', (e) => {
        state.filters.priority = e.target.value;
        state.currentPage = 1;
        renderCases();
        updatePagination();
    });

    // Status filter
    document.getElementById('statusFilter').addEventListener('change', (e) => {
        state.filters.status = e.target.value;
        state.currentPage = 1;
        renderCases();
        updatePagination();
    });

    // Assignee filter
    document.getElementById('assigneeFilter').addEventListener('change', (e) => {
        state.filters.assignee = e.target.value;
        state.currentPage = 1;
        renderCases();
        updatePagination();
    });

    // New Case button
    document.getElementById('newCaseBtn').addEventListener('click', () => {
        window.location.href = 'new-case.html';
    });

    // Pagination
    document.getElementById('prevPage').addEventListener('click', () => {
        if (state.currentPage > 1) {
            state.currentPage--;
            renderCases();
            updatePagination();
        }
    });

    document.getElementById('nextPage').addEventListener('click', () => {
        const totalPages = Math.ceil(getFilteredCases().length / state.itemsPerPage);
        if (state.currentPage < totalPages) {
            state.currentPage++;
            renderCases();
            updatePagination();
        }
    });

    // Logout button
    document.getElementById('logoutButton').addEventListener('click', handleLogout);
}

// Filter Cases
function getFilteredCases() {
    let filtered = [...state.cases];

    // Apply search filter
    if (state.filters.search) {
        const searchTerm = state.filters.search.toLowerCase();
        filtered = filtered.filter(case_ => 
            case_.title.toLowerCase().includes(searchTerm) ||
            case_.description.toLowerCase().includes(searchTerm) ||
            case_.id.toLowerCase().includes(searchTerm)
        );
    }

    // Apply priority filter
    if (state.filters.priority !== 'all') {
        filtered = filtered.filter(case_ => case_.priority === state.filters.priority);
    }

    // Apply status filter
    if (state.filters.status !== 'all') {
        filtered = filtered.filter(case_ => case_.status === state.filters.status);
    }

    // Apply assignee filter
    if (state.filters.assignee !== 'all') {
        if (state.filters.assignee === 'me') {
            filtered = filtered.filter(case_ => case_.assigneeId === state.user.id);
        } else if (state.filters.assignee === 'unassigned') {
            filtered = filtered.filter(case_ => !case_.assigneeId);
        }
    }

    return filtered;
}

// Render Cases
function renderCases() {
    const casesGrid = document.getElementById('casesGrid');
    const filteredCases = getFilteredCases();
    const startIndex = (state.currentPage - 1) * state.itemsPerPage;
    const endIndex = startIndex + state.itemsPerPage;
    const casesToShow = filteredCases.slice(startIndex, endIndex);

    casesGrid.innerHTML = '';

    if (casesToShow.length === 0) {
        casesGrid.innerHTML = `
            <div class="col-span-full text-center py-8 text-gray-500">
                No cases found matching your criteria
            </div>
        `;
        return;
    }

    casesToShow.forEach(case_ => {
        const caseElement = createCaseElement(case_);
        casesGrid.appendChild(caseElement);
    });
}

// Create Case Element
function createCaseElement(case_) {
    const div = document.createElement('div');
    div.className = 'case-card';
    
    const dueDate = new Date(case_.dueDate);
    const today = new Date();
    const daysUntilDue = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
    
    let dueDateClass = 'safe';
    if (daysUntilDue < 0) {
        dueDateClass = 'overdue';
    } else if (daysUntilDue <= 7) {
        dueDateClass = 'upcoming';
    }
    
    div.innerHTML = `
        <div class="flex justify-between items-start mb-4">
            <div>
                <h3 class="font-bold text-lg">${sanitizeHTML(case_.title)}</h3>
                <p class="text-sm text-gray-500">Case ID: ${sanitizeHTML(case_.id)}</p>
            </div>
            <div class="flex items-center space-x-2">
                <span class="priority-badge ${case_.priority}">${case_.priority.toUpperCase()}</span>
                <span class="status-badge ${case_.status}">${formatStatus(case_.status)}</span>
            </div>
        </div>
        <div class="mb-4">
            <p class="text-sm text-gray-600">${sanitizeHTML(case_.description)}</p>
        </div>
        <div class="mb-4">
            <div class="flex justify-between text-sm text-gray-500 mb-1">
                <span>Progress</span>
                <span>${case_.progress}%</span>
            </div>
            <div class="progress-bar">
                <div class="progress-bar-fill ${getProgressColor(case_.progress)}" 
                     style="width: ${case_.progress}%"></div>
            </div>
        </div>
        <div class="grid grid-cols-2 gap-4 mb-4 text-sm">
            <div>
                <p class="text-gray-500">Assigned To</p>
                <p class="font-medium">${sanitizeHTML(case_.assignee)}</p>
            </div>
            <div>
                <p class="text-gray-500">Due Date</p>
                <p class="font-medium due-date ${dueDateClass}">
                    ${formatDate(case_.dueDate)}
                    ${daysUntilDue < 0 ? '(Overdue)' : 
                      daysUntilDue === 0 ? '(Due today)' : 
                      `(${daysUntilDue} days left)`}
                </p>
            </div>
        </div>
        <div class="flex justify-between items-center pt-4 border-t">
            <div class="flex space-x-4 text-sm text-gray-500">
                <span class="flex items-center">
                    <i data-lucide="check-square" class="w-4 h-4 mr-1"></i>
                    ${case_.tasks.completed}/${case_.tasks.total} Tasks
                </span>
                <span class="flex items-center">
                    <i data-lucide="folder" class="w-4 h-4 mr-1"></i>
                    ${case_.evidence} Evidence Items
                </span>
            </div>
            <div class="flex space-x-2">
                <button class="action-button" onclick="window.location.href='case-details.html?id=${case_.id}'">
                    <i data-lucide="external-link" class="w-4 h-4"></i>
                </button>
                <button class="action-button">
                    <i data-lucide="more-vertical" class="w-4 h-4"></i>
                </button>
            </div>
        </div>
    `;
    
    // Reinitialize icons within the new element
    lucide.createIcons({
        attrs: {
            class: "w-4 h-4"
        },
        elements: div.querySelectorAll('[data-lucide]')
    });
    
    return div;
}

// Update Pagination
function updatePagination() {
    const filteredCases = getFilteredCases();
    const totalPages = Math.ceil(filteredCases.length / state.itemsPerPage);
    
    document.getElementById('currentPage').textContent = state.currentPage;
    document.getElementById('totalPages').textContent = totalPages;
    
    document.getElementById('prevPage').disabled = state.currentPage === 1;
    document.getElementById('nextPage').disabled = state.currentPage === totalPages;
}

// Update User Info
function updateUserInfo() {
    const userNameElement = document.getElementById('userName');
    if (userNameElement) {
        userNameElement.textContent = state.user.name;
    }
    
    const userRoleElement = document.querySelector('#user-info p');
    if (userRoleElement) {
        userRoleElement.textContent = state.user.role;
    }
}

// Helper Functions
function formatStatus(status) {
    return status.split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function getProgressColor(progress) {
    if (progress < 30) return 'low';
    if (progress < 70) return 'medium';
    return 'high';
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
        
        // Reset button state
        const logoutButton = document.getElementById('logoutButton');
        logoutButton.disabled = false;
        logoutButton.innerHTML = '<i data-lucide="log-out" class="w-4 h-4 mr-3"></i><span class="flex-1">Logout</span>';
        lucide.createIcons();
    }
}

// Prevent XSS
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}