document.addEventListener('DOMContentLoaded', function() {
    // Initialize Lucide icons
    lucide.createIcons();

    // Get necessary elements
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const navButtons = document.querySelectorAll('.nav-button');
    const contentArea = document.getElementById('content-area');
    const reportsDropdown = document.getElementById('reportsDropdown');
    const dropdown = document.querySelector('.dropdown');

    // Analysis content for each section
    const analysisContent = {
        log: {
            title: 'Log Analysis',
            description: 'Analyze system logs, event logs, and application logs to identify suspicious activities and potential security incidents. Our advanced log analysis engine processes multiple log formats and correlates events across different sources.',
            buttonText: 'Analyze Logs',
            icon: 'search'
        },
        network: {
            title: 'Network Analysis',
            description: 'Examine network traffic patterns, connections, and protocols to detect anomalies and potential network-based attacks. Includes packet analysis, flow analysis, and protocol analysis capabilities.',
            buttonText: 'Analyze Network',
            icon: 'activity'
        },
        registry: {
            title: 'Registry Analysis',
            description: 'Investigate Windows Registry for signs of system modifications, persistence mechanisms, and malware artifacts. Our registry analysis tool helps identify suspicious registry keys and values.',
            buttonText: 'Analyze Registry',
            icon: 'database'
        }
    };

    function updateNavTooltips() {
        const isCollapsed = sidebar.classList.contains('collapsed');
        navButtons.forEach(button => {
            if (isCollapsed) {
                const text = button.querySelector('span').textContent;
                button.setAttribute('title', text);
            } else {
                button.removeAttribute('title');
            }
        });
    }

    // Toggle sidebar
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
        lucide.createIcons();
    });

    // Dropdown handling
    if (dropdown && reportsDropdown) {
        reportsDropdown.addEventListener('mouseenter', function(e) {
            if (sidebar.classList.contains('collapsed')) {
                dropdown.classList.add('active');
            }
        });
    
        reportsDropdown.addEventListener('click', function(e) {
            if (!sidebar.classList.contains('collapsed')) {
                dropdown.classList.toggle('active');
            }
        });

        dropdown.addEventListener('mouseleave', function(e) {
            if (sidebar.classList.contains('collapsed')) {
                dropdown.classList.remove('active');
            }
        });

        // Handle dropdown item clicks
        const dropdownLinks = dropdown.querySelectorAll('.dropdown-content a');
        dropdownLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const fileName = this.getAttribute('data-file');
                simulateFileDownload(fileName);
                dropdown.classList.remove('active');
            });
        });
    }

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target)&& !sidebar.classList.contains('collapsed')) {
            dropdown.classList.remove('active');
        }
    });

    // Update content area
    function updateContent(section) {
        if (analysisContent[section]) {
            const content = analysisContent[section];
            contentArea.innerHTML = `
                <div class="analysis-section active">
                    <h2>${content.title}</h2>
                    <p>${content.description}</p>
                    <button class="analyze-button" data-analysis="${section}">
                        <i data-lucide="${content.icon}"></i>
                        ${content.buttonText}
                    </button>
                </div>
            `;

            // Reinitialize Lucide icons for new content
            lucide.createIcons();

            // Add click event for the new analyze button
            const analyzeButton = contentArea.querySelector('.analyze-button');
            analyzeButton.addEventListener('click', function() {
                handleAnalysis(section);
            });
        }
    }

    // Handle analysis button clicks
    function handleAnalysis(type) {
        const button = document.querySelector(`[data-analysis="${type}"]`);
        const originalText = button.innerHTML;
        
        // Disable button and show loading state
        button.disabled = true;
        button.innerHTML = '<i data-lucide="loader-2" class="animate-spin"></i> Analyzing...';
        lucide.createIcons();

        // Simulate analysis process
        setTimeout(() => {
            button.innerHTML = '<i data-lucide="check"></i> Analysis Complete!';
            lucide.createIcons();
            
            setTimeout(() => {
                button.disabled = false;
                button.innerHTML = originalText;
                lucide.createIcons();
            }, 2000);
        }, 3000);
    }
    function handleAnalysis(type) {
        const button = document.querySelector(`[data-analysis="${type}"]`);
        const originalText = button.innerHTML;
        
        // Disable button and show loading state
        button.disabled = true;
        button.innerHTML = '<i data-lucide="loader-2" class="animate-spin"></i> Analyzing...';
        lucide.createIcons();
    
        if (type === 'log') {
            // Make API call to execute log analysis
            fetch('http://localhost:5000/api/analyze-logs', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    button.innerHTML = '<i data-lucide="check"></i> Analysis Complete!';
                    // You might want to display the output somewhere
                    console.log('Analysis output:', data.output);
                } else {
                    button.innerHTML = '<i data-lucide="x"></i> Analysis Failed';
                    console.error('Analysis error:', data.message);
                }
                lucide.createIcons();
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = originalText;
                    lucide.createIcons();
                }, 2000);
            })
            .catch(error => {
                console.error('Error:', error);
                button.innerHTML = '<i data-lucide="x"></i> Error';
                lucide.createIcons();
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = originalText;
                    lucide.createIcons();
                }, 2000);
            });
        } else {
            // Handle other analysis types as before
            setTimeout(() => {
                button.innerHTML = '<i data-lucide="check"></i> Analysis Complete!';
                lucide.createIcons();
                
                setTimeout(() => {
                    button.disabled = false;
                    button.innerHTML = originalText;
                    lucide.createIcons();
                }, 2000);
            }, 3000);
        }
    }
    // Add click events to navigation buttons
    navButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            const section = this.getAttribute('data-section');
            
            // Skip if it's the reports button
            if (this.id === 'reportsDropdown') {
                return; // Handled by dropdown-specific event listener
            }

            // Remove active class from all buttons
            navButtons.forEach(btn => {
                btn.classList.remove('active');
                if (btn.id === 'reportsDropdown') {
                    btn.parentElement.classList.remove('active');
                }
            });

            // Add active class to clicked button
            this.classList.add('active');

            // Update content
            if (section) {
                updateContent(section);
            }
        });
    });

    // Function to simulate file download
    function simulateFileDownload(fileName) {
        alert(`Downloading ${fileName}...`);
        // In a real application, this would trigger an actual file download
    }
});