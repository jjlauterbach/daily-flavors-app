// App configuration
const API_BASE_URL = window.location.origin;

// DOM elements
const loadingEl = document.getElementById('loading');
const errorEl = document.getElementById('error');
const errorMessageEl = document.getElementById('errorMessage');
const flavorsGridEl = document.getElementById('flavorsGrid');
const currentDateEl = document.getElementById('currentDate');

// Initialize the app
document.addEventListener('DOMContentLoaded', () => {
    setCurrentDate();
    loadFlavors();
});

// Set current date in header
function setCurrentDate() {
    const now = new Date();
    const options = { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    };
    currentDateEl.textContent = now.toLocaleDateString('en-US', options);
}

// Load flavors from API
async function loadFlavors() {
    showLoading();
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/flavors`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const flavors = await response.json();
        
        if (!Array.isArray(flavors)) {
            throw new Error('Invalid response format - expected array');
        }
        
        if (flavors.length === 0) {
            showError('No flavors found for today. Please try again later.');
            return;
        }
        
        displayFlavors(flavors);
        
    } catch (error) {
        console.error('Error loading flavors:', error);
        showError(`Failed to load flavors: ${error.message}`);
    }
}

// Show loading state
function showLoading() {
    loadingEl.style.display = 'block';
    errorEl.style.display = 'none';
    flavorsGridEl.innerHTML = '';
}

// Show error state
function showError(message) {
    loadingEl.style.display = 'none';
    errorEl.style.display = 'block';
    errorMessageEl.textContent = message;
    flavorsGridEl.innerHTML = '';
}

// Display flavors in the grid
function displayFlavors(flavors) {
    loadingEl.style.display = 'none';
    errorEl.style.display = 'none';
    
    // Clear existing content
    flavorsGridEl.innerHTML = '';
    
    // Create cards for each flavor
    flavors.forEach(flavor => {
        const card = createFlavorCard(flavor);
        flavorsGridEl.appendChild(card);
    });
}

// Create a flavor card element
function createFlavorCard(flavor) {
    const card = document.createElement('div');
    card.className = 'flavor-card';
    
    // Format description
    const description = flavor.description && flavor.description.trim() && 
                       flavor.description !== 'No description available' 
                       ? flavor.description 
                       : null;
    
    // Format date
    const date = formatDate(flavor.date);
    
    card.innerHTML = `
        <div class="shop-header">
            <div class="shop-icon">
                <i class="fas fa-ice-cream"></i>
            </div>
            <div class="shop-name">${escapeHtml(flavor.location)}</div>
        </div>
        
        <div class="flavor-name">${escapeHtml(flavor.flavor)}</div>
        
        ${description ? 
            `<div class="flavor-description">${escapeHtml(description)}</div>` :
            `<div class="flavor-description no-description">No description available</div>`
        }
        
        <div class="flavor-date">
            <i class="fas fa-calendar-alt"></i>
            ${date}
        </div>
    `;
    
    return card;
}

// Format date for display
function formatDate(dateString) {
    try {
        const date = new Date(dateString);
        const options = { 
            weekday: 'short',
            month: 'short', 
            day: 'numeric',
            year: 'numeric'
        };
        return date.toLocaleDateString('en-US', options);
    } catch (error) {
        return dateString; // Fallback to original string
    }
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Auto-refresh functionality (optional)
function startAutoRefresh() {
    // Refresh every 30 minutes
    setInterval(() => {
        console.log('Auto-refreshing flavors...');
        loadFlavors();
    }, 30 * 60 * 1000);
}

// Start auto-refresh after initial load
setTimeout(startAutoRefresh, 5000);
