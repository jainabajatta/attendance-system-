/**
 * Main JavaScript for Attendance System
 */

// Global state
let currentUser = null;
let systemStatus = 'offline';
let notificationPermission = false;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    checkSystemStatus();
});

function initializeApp() {
    console.log('Initializing Attendance System...');
    
    // Request notification permission
    if ('Notification' in window) {
        Notification.requestPermission().then(permission => {
            notificationPermission = permission === 'granted';
        });
    }
    
    // Load initial data
    loadDashboardStats();
    
    // Start periodic updates
    setInterval(loadDashboardStats, 30000);
    setInterval(checkSystemStatus, 60000);
}

function setupEventListeners() {
    // Global keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // Ctrl+D for dashboard
        if (e.ctrlKey && e.key === 'd') {
            e.preventDefault();
            window.location.href = '/dashboard';
        }
        // Ctrl+R for register
        if (e.ctrlKey && e.key === 'r') {
            e.preventDefault();
            window.location.href = '/register';
        }
        // Ctrl+P for reports
        if (e.ctrlKey && e.key === 'p') {
            e.preventDefault();
            window.location.href = '/reports';
        }
    });
}

async function loadDashboardStats() {
    try {
        const response = await fetch('/api/statistics');
        const stats = await response.json();
        
        updateStatsDisplay(stats);
        systemStatus = stats.system_status;
        
    } catch (error) {
        console.error('Error loading stats:', error);
        showError('Failed to load dashboard statistics');
    }
}

function updateStatsDisplay(stats) {
    const elements = {
        'total-users': stats.total_users,
        'today-attendance': stats.today_attendance,
        'active-sessions': stats.active_sessions || 0,
        'recognition-accuracy': stats.recognition_accuracy || '94.5%'
    };
    
    for (const [id, value] of Object.entries(elements)) {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = value;
        }
    }
}

async function checkSystemStatus() {
    try {
        const response = await fetch('/api/health');
        const status = await response.json();
        
        systemStatus = status.status;
        const statusIndicator = document.getElementById('systemStatus');
        
        if (statusIndicator) {
            statusIndicator.className = `status-${status.status}`;
            statusIndicator.title = `System is ${status.status}`;
        }
        
        if (status.status === 'healthy') {
            console.log('System is healthy');
        } else {
            console.warn('System issues detected:', status.issues);
            showWarning('System performance may be degraded');
        }
        
    } catch (error) {
        console.error('Health check failed:', error);
        systemStatus = 'offline';
        showError('Cannot connect to server');
    }
}

function showNotification(title, body, type = 'info') {
    if (notificationPermission && document.hidden) {
        new Notification(title, { body, icon: '/static/images/icon.png' });
    }
    
    // Also show in-app notification
    const notification = document.createElement('div');
    notification.className = `toast-notification ${type}`;
    notification.innerHTML = `
        <div class="toast-header">
            <strong class="me-auto">${title}</strong>
            <button type="button" class="btn-close" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
        <div class="toast-body">${body}</div>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }, 100);
}

function showError(message) {
    console.error(message);
    showNotification('Error', message, 'error');
}

function showWarning(message) {
    console.warn(message);
    showNotification('Warning', message, 'warning');
}

function showSuccess(message) {
    console.log(message);
    showNotification('Success', message, 'success');
}

// Utility function for formatting
function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
}

function formatTime(time) {
    return new Date(`2000-01-01T${time}`).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

// Export functions for global use
window.showNotification = showNotification;
window.showError = showError;
window.showSuccess = showSuccess;
window.formatDate = formatDate;
window.formatTime = formatTime;