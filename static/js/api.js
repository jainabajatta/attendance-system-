/**
 * API Service for Attendance System
 */

const API_BASE = '/api';

class AttendanceAPI {
    // User Management
    static async getUsers() {
        const response = await fetch(`${API_BASE}/users`);
        return await response.json();
    }
    
    static async registerUser(userData, faceSamples) {
        const formData = new FormData();
        formData.append('name', userData.name);
        formData.append('employee_id', userData.employeeId);
        formData.append('department', userData.department);
        formData.append('face_images', JSON.stringify(faceSamples));
        
        const response = await fetch(`${API_BASE}/register`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
    
    static async deleteUser(userId) {
        const response = await fetch(`${API_BASE}/user/${userId}`, {
            method: 'DELETE'
        });
        
        return await response.json();
    }
    
    // Attendance Management
    static async getTodayAttendance() {
        const response = await fetch(`${API_BASE}/attendance/today`);
        return await response.json();
    }
    
    static async getAttendanceByDate(date) {
        const response = await fetch(`${API_BASE}/attendance/date/${date}`);
        return await response.json();
    }
    
    static async getAttendanceRange(dateFrom, dateTo) {
        const response = await fetch(`${API_BASE}/attendance/range?from=${dateFrom}&to=${dateTo}`);
        return await response.json();
    }
    
    static async exportAttendance(dateFrom, dateTo, format = 'excel') {
        window.location.href = `${API_BASE}/attendance/export?date_from=${dateFrom}&date_to=${dateTo}&format=${format}`;
    }
    
    // System Management
    static async getStatistics() {
        const response = await fetch(`${API_BASE}/statistics`);
        return await response.json();
    }
    
    static async trainSystem() {
        const response = await fetch(`${API_BASE}/train`, {
            method: 'POST'
        });
        
        return await response.json();
    }
    
    static async getTrainingStatus() {
        const response = await fetch(`${API_BASE}/training/status`);
        return await response.json();
    }
}

// Utility Functions
class Utils {
    static showToast(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast-custom alert alert-${type}`;
        toast.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'} me-2"></i>
                <span>${message}</span>
            </div>
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
    
    static formatDate(date) {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    static formatTime(time) {
        return new Date(`2000-01-01T${time}`).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }
    
    static getConfidenceColor(confidence) {
        if (confidence > 80) return 'success';
        if (confidence > 65) return 'warning';
        return 'danger';
    }
    
    static async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showToast('Copied to clipboard!', 'success');
        } catch (err) {
            this.showToast('Failed to copy', 'danger');
        }
    }
    
    static debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AttendanceAPI, Utils };
}