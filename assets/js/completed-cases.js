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
        timeRange: 'all',
        status: 'all'
    },
    user: {
        name: "John Doe",
        role: "Senior Digital Forensics Investigator"
    }
};

// Sample Data (Replace with actual API call)
const sampleCases = [
    {
        id: "2024-001",
        title: "Network Security Breach Investigation",
        dateCompleted: "2024-01-15",
        status: "solved",
        investigator: "John Doe",
        description: "Investigation of unauthorized access to internal network",
        priority: "high",
        closingNotes: "Identified and patched security vulnerability. Enhanced monitoring implemented."
    },
    {
        id: "2024-002",
        title: "Data Corruption Analysis",
        dateCompleted: "2024-01-20",
        status: "closed",
        investigator: "John Doe",
        description: "Analysis of corrupted database files",
        priority: "medium",
        closingNotes: "Recovered 98% of corrupted data. Implemented new backup system."
    },
    {
        id: "2024-003",
        title: "Employee Device Audit",
        dateCompleted: "2024-01-25",
        status: "archived",
        investigator: "John Doe",
        description: "Annual security audit of employee devices",
        priority: "low",
        closingNotes: "Completed standard audit procedures. No major issues found."
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

    // Time filter
    document.getElementById('timeFilter').addEventListener('change', (e) => {
        state.filters.timeRange = e.target.value;
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

    // Toggle sidebar (if exists in this view)
    const toggleButton = document.getElementById('toggleSidebar');
    if (toggleButton) {
        toggleButton.addEventListener('click', toggleSidebar);
    }
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

    // Apply time range filter
    if (state.filters.timeRange !== 'all') {
        const now = new Date();
        const timeRanges = {
            'week': 7,
            'month': 30,
            'year': 365
        };
        
        const days = timeRanges[state.filters.timeRange];
        if (days) {
            filtered = filtered.filter(case_ => {
                const caseDate = new Date(case_.dateCompleted);
                const diffTime = Math.abs(now - caseDate);
                const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
                return diffDays <= days;
            });
        }
    }

    // Apply status filter
    if (state.filters.status !== 'all') {
        filtered = filtered.filter(case_ => case_.status === state.filters.status);
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
    
    div.innerHTML = `
        <div class="flex justify-between items-start mb-4">
            <h3 class="font-bold text-lg">${sanitizeHTML(case_.title)}</h3>
            <span class="status-badge ${case_.status}">${case_.status.charAt(0).toUpperCase() + case_.status.slice(1)}</span>
        </div>
        <div class="mb-4">
            <p class="text-sm text-gray-600">${sanitizeHTML(case_.description)}</p>
        </div>
        <div class="text-sm text-gray-500 mb-4">
            <div class="flex justify-between mb-2">
                <span>Case ID: ${sanitizeHTML(case_.id)}</span>
                <span>Priority: ${case_.priority.charAt(0).toUpperCase() + case_.priority.slice(1)}</span>
            </div>
            <div class="flex justify-between">
                <span>Completed: ${formatDate(case_.dateCompleted)}</span>
                <span>Investigator: ${sanitizeHTML(case_.investigator)}</span>
            </div>
        </div>
        <div class="mt-4 pt-4 border-t">
            <p class="text-sm text-gray-600"><strong>Closing Notes:</strong> ${sanitizeHTML(case_.closingNotes)}</p>
        </div>
    `;
    
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

// Toggle Sidebar
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
    }
}

// Helper Functions
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Prevent XSS
function sanitizeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}