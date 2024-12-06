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
    selectedFiles: [],
    uploadPath: 'uploads/' // Base path for uploads
};

// Initialize Application
function initializeApp() {
    // Check for case data
    const caseData = localStorage.getItem('currentCase');
    if (!caseData) {
        navigate('/new-case');
        return;
    }

    // Parse case data
    const currentCase = JSON.parse(caseData);
    
    // Update UI with case details
    updateCaseDetails(currentCase);
    
    updateCurrentDate();
    setupEventListeners();
}

function updateCaseDetails(caseData) {
    // Add case number or other relevant info to the header
    const headerSubtitle = document.querySelector('.header-subtitle');
    headerSubtitle.textContent = `Select evidence for Case #${caseData.caseNumber}`;
}

// Setup Event Listeners
function setupEventListeners() {
    const uploadZone = document.getElementById('uploadZone');
    const folderInput = document.getElementById('folderInput');
    const analyzeButton = document.getElementById('analyzeButton');
    const cancelButton = document.getElementById('cancelButton');

    // Upload zone click
    uploadZone.addEventListener('click', () => folderInput.click());

    // Drag and drop handlers
    uploadZone.addEventListener('dragover', handleDragOver);
    uploadZone.addEventListener('dragleave', handleDragLeave);
    uploadZone.addEventListener('drop', handleDrop);

    // File input change
    folderInput.addEventListener('change', handleFileSelect);

    // Cancel button
    cancelButton.addEventListener('click', () => navigate('/home'));

    // Analyze button
    analyzeButton.addEventListener('click', handleAnalysis);
}

async function handleAnalysis() {
    if (state.selectedFiles.length === 0) return;

    try {
        const currentCase = JSON.parse(localStorage.getItem('currentCase'));
        
        // Show upload progress UI
        const uploadProgress = document.getElementById('uploadProgress');
        const progressFill = document.querySelector('.progress-fill');
        const progressPercentage = document.querySelector('.progress-percentage');
        const filesCount = document.getElementById('filesCount');
        
        uploadProgress.classList.remove('hidden');
        filesCount.textContent = `${state.selectedFiles.length} files found`;

        // Calculate total size
        const totalSize = state.selectedFiles.reduce((acc, file) => acc + file.size, 0);
        let uploadedSize = 0;

        // Upload files one by one to show progress
        for (let i = 0; i < state.selectedFiles.length; i++) {
            const file = state.selectedFiles[i];
            const formData = new FormData();
            
            formData.append('caseNumber', currentCase.caseNumber);
            formData.append('files[]', file);
            if (file.relativePath) {
                formData.append(`paths[${file.name}]`, file.relativePath);
            }

            const response = await fetch('http://localhost:5000/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Update progress
            uploadedSize += file.size;
            const percentage = Math.round((uploadedSize / totalSize) * 100);
            
            // Update UI
            progressFill.style.width = `${percentage}%`;
            progressPercentage.textContent = `${percentage}%`;
            filesCount.textContent = `${i + 1} of ${state.selectedFiles.length} files uploaded`;

            // Store the last result
            if (i === state.selectedFiles.length - 1) {
                sessionStorage.setItem('evidenceFiles', JSON.stringify(result.files));
                sessionStorage.setItem('evidencePath', result.upload_dir);
            }

            // Add delay between files
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        // Show complete for a moment before redirecting
        progressFill.style.width = '100%';
        progressPercentage.textContent = '100%';
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Navigate to tool page
        window.location.href = '/tool.html';

    } catch (error) {
        console.error('Error during file upload:', error);
        alert(`Error uploading files: ${error.message}`);
    }
}

// Drag and Drop Handlers
function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadZone').classList.add('dragging');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    document.getElementById('uploadZone').classList.remove('dragging');
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    const uploadZone = document.getElementById('uploadZone');
    uploadZone.classList.remove('dragging');

    // Handle files directly from dataTransfer.files
    const files = Array.from(e.dataTransfer.files);
    updateFileList(files);
}

// File Selection Handler
function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    updateFileList(files);
}

// Handle Items (for drag and drop)
function handleItems(items) {
    const files = [];
    
    for (let item of items) {
        if (item.kind === 'file') {
            const file = item.getAsFile();
            if (file) {
                files.push(file);
            }
        }
    }

    updateFileList(files);
}

// Update File List
function updateFileList(files) {
    state.selectedFiles = files;
    const fileList = document.getElementById('fileList');
    const fileItems = document.querySelector('.file-items');
    const analyzeButton = document.getElementById('analyzeButton');

    // Update file items
    fileItems.innerHTML = files.map(file => `
        <div class="file-item">
            <i data-lucide="file" class="file-icon"></i>
            <span class="file-name">${file.relativePath || file.name}</span>
            <span class="file-size">${formatFileSize(file.size)}</span>
        </div>
    `).join('');

    // Reinitialize icons
    lucide.createIcons();

    // Show file list and enable analyze button
    fileList.classList.remove('hidden');
    analyzeButton.disabled = files.length === 0;
    
    // Update files count
    document.getElementById('filesCount').textContent = `${files.length} files found`;
}

// Helper Functions
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function updateCurrentDate() {
    const currentDate = document.getElementById('currentDate');
    currentDate.textContent = new Date().toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

// Authentication Check
function checkAuthentication() {
    if (!localStorage.getItem('isLoggedIn')) {
        navigate('/');
        return;
    }
}