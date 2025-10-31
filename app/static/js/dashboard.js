// Dashboard functionality for ATBI User Profile
class UserDashboard {
    constructor() {
        this.currentTab = 'reservations';
        this.isInitialized = false;
        this.setupGlobalFunctions();
    }
    setupGlobalFunctions() {
        // Set up global functions immediately when class is instantiated
        window.openUserDashboard = () => this.openDashboard();
        window.dashboard = this;
    }
    init() {
        if (this.isInitialized) return;
        
        this.bindEvents();
        this.loadDashboardData();
        this.setupPasswordStrength();
        this.isInitialized = true;
    }

    initDashboardFunctionality() {
        this.init();
    }

    bindEvents() {
        // Navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Close modal
        const closeBtn = document.querySelector('.close-dashboard');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeDashboard());
        }

        // Filter reservations
        const filterSelect = document.getElementById('reservationFilter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.filterReservations(e.target.value);
            });
        }

        // Form submissions
        const profileForm = document.getElementById('profileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => this.updateProfile(e));
        }

        const passwordForm = document.getElementById('passwordForm');
        if (passwordForm) {
            passwordForm.addEventListener('submit', (e) => this.changePassword(e));
        }

        // Clear notifications
        const clearBtn = document.getElementById('clearNotifications');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearNotifications());
        }
    }

    switchTab(tabName) {
        // Update navigation
        document.querySelectorAll('.nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update content
        document.querySelectorAll('.tab-content').forEach(tab => {
            tab.classList.toggle('active', tab.id === `${tabName}-tab`);
        });

        this.currentTab = tabName;

        // Load tab-specific data
        switch(tabName) {
            case 'reservations':
                this.loadReservations();
                break;
            case 'notifications':
                this.loadNotifications();
                break;
        }
    }

    async loadDashboardData() {
        await Promise.all([
            this.loadReservations(),
            this.loadNotifications(),
            this.loadUserStats()
        ]);
    }

    async loadReservations() {
        try {
            const userId = sessionStorage.getItem('user_id') || '{{ session.get("user_id") }}';
            if (!userId) {
                this.showError('User not logged in');
                return;
            }

            const response = await fetch(`/reservations/user/${userId}`);
            const data = await response.json();

            if (data.success) {
                this.renderReservations(data.reservations);
                this.updateReservationStats(data.reservations);
            } else {
                this.showError('Failed to load reservations');
            }
        } catch (error) {
            console.error('Error loading reservations:', error);
            this.showError('Error loading reservations');
        }
    }

    renderReservations(reservations) {
        const container = document.getElementById('reservationsList');
        if (!container) return;
        
        if (!reservations || reservations.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-clipboard-list"></i>
                    <p>No reservations yet</p>
                    <small>Your reservations will appear here</small>
                </div>
            `;
            return;
        }

        container.innerHTML = reservations.map(reservation => `
            <div class="reservation-item" data-status="${reservation.status}">
                <div class="reservation-header">
                    <div class="reservation-product">${reservation.product_name}</div>
                    <div class="reservation-price">₱${parseFloat(reservation.price_per_stocks).toLocaleString()}</div>
                </div>
                <div class="reservation-meta">
                    <div class="reservation-quantity">Quantity: ${reservation.quantity}</div>
                    <div class="reservation-date">Reserved: ${new Date(reservation.reserved_at).toLocaleDateString()}</div>
                </div>
                <div class="reservation-status">
                    <div class="status-badge status-${reservation.status}">
                        ${reservation.status.toUpperCase()}
                    </div>
                    <div class="reservation-actions">
                        ${reservation.status === 'pending' ? `
                            <button class="action-btn danger" onclick="dashboard.cancelReservation(${reservation.reservation_id})">
                                <i class="fas fa-times"></i> Cancel
                            </button>
                        ` : ''}
                        ${reservation.status === 'approved' ? `
                            <button class="action-btn primary" onclick="dashboard.confirmPickup(${reservation.reservation_id})">
                                <i class="fas fa-check"></i> Confirm Pickup
                            </button>
                        ` : ''}
                    </div>
                </div>
                ${reservation.rejected_reason ? `
                    <div class="rejection-reason" style="margin-top: 10px; padding: 10px; background: #fef2f2; border-radius: 6px; color: #dc2626;">
                        <strong>Reason:</strong> ${reservation.rejected_reason}
                    </div>
                ` : ''}
            </div>
        `).join('');
    }

    filterReservations(status) {
        const items = document.querySelectorAll('.reservation-item');
        items.forEach(item => {
            const show = status === 'all' || item.dataset.status === status;
            item.style.display = show ? 'block' : 'none';
        });
    }

    updateReservationStats(reservations) {
        const stats = {
            pending: reservations.filter(r => r.status === 'pending').length,
            approved: reservations.filter(r => r.status === 'approved').length,
            total: reservations.length
        };

        const pendingEl = document.getElementById('pendingReservations');
        const approvedEl = document.getElementById('approvedReservations');
        const totalEl = document.getElementById('totalReservations');

        if (pendingEl) pendingEl.textContent = stats.pending;
        if (approvedEl) approvedEl.textContent = stats.approved;
        if (totalEl) totalEl.textContent = stats.total;
    }

    async loadNotifications() {
        try {
            // Simulated notifications - replace with actual API call
            const notifications = [
                {
                    id: 1,
                    type: 'info',
                    title: 'Welcome to ATBI Dashboard',
                    message: 'Start managing your reservations and profile',
                    time: new Date().toISOString(),
                    read: false
                }
            ];

            this.renderNotifications(notifications);
        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notificationsList');
        const badge = document.getElementById('notificationCount');
        if (!container || !badge) return;
        
        const unreadCount = notifications.filter(n => !n.read).length;
        badge.textContent = unreadCount;
        badge.style.display = unreadCount > 0 ? 'flex' : 'none';

        if (notifications.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-bell-slash"></i>
                    <p>No notifications yet</p>
                    <small>You'll see important updates here</small>
                </div>
            `;
            return;
        }

        container.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.read ? 'read' : 'unread'}">
                <div class="notification-icon">
                    <i class="fas fa-${this.getNotificationIcon(notification.type)}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-title">${notification.title}</div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-time">${new Date(notification.time).toLocaleString()}</div>
                </div>
            </div>
        `).join('');
    }

    getNotificationIcon(type) {
        const icons = {
            info: 'info-circle',
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'exclamation-circle'
        };
        return icons[type] || 'bell';
    }

    async loadUserStats() {
        // Additional user statistics can be loaded here
        try {
            const response = await fetch('/user/stats');
            if (response.ok) {
                const data = await response.json();
                // Update any additional stats here
            }
        } catch (error) {
            console.error('Error loading user stats:', error);
        }
    }

    async updateProfile(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);

        try {
            const response = await fetch('/user/profile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Profile updated successfully');
            } else {
                this.showError(result.message || 'Failed to update profile');
            }
        } catch (error) {
            console.error('Error updating profile:', error);
            this.showError('Error updating profile');
        }
    }

    async changePassword(e) {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const data = Object.fromEntries(formData);

        if (data.newPassword !== data.confirmPassword) {
            this.showError('New passwords do not match');
            return;
        }

        try {
            const response = await fetch('/user/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Password changed successfully');
                e.target.reset();
            } else {
                this.showError(result.message || 'Failed to change password');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showError('Error changing password');
        }
    }

    async cancelReservation(reservationId) {
        if (!confirm('Are you sure you want to cancel this reservation?')) {
            return;
        }

        try {
            const response = await fetch(`/reservations/cancel/${reservationId}`, {
                method: 'POST'
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Reservation cancelled successfully');
                this.loadReservations();
            } else {
                this.showError(result.message || 'Failed to cancel reservation');
            }
        } catch (error) {
            console.error('Error cancelling reservation:', error);
            this.showError('Error cancelling reservation');
        }
    }

    async confirmPickup(reservationId) {
        if (!confirm('Confirm that you have picked up the items?')) {
            return;
        }

        try {
            const response = await fetch(`/reservations/complete/${reservationId}`, {
                method: 'POST'
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Pickup confirmed! Thank you.');
                this.loadReservations();
            } else {
                this.showError(result.message || 'Failed to confirm pickup');
            }
        } catch (error) {
            console.error('Error confirming pickup:', error);
            this.showError('Error confirming pickup');
        }
    }

    clearNotifications() {
        if (!confirm('Clear all notifications?')) {
            return;
        }

        // Implement notification clearing logic
        this.showSuccess('Notifications cleared');
        this.renderNotifications([]);
    }

    setupPasswordStrength() {
        const passwordInput = document.getElementById('newPassword');
        const strengthBar = document.querySelector('.strength-bar');
        const strengthText = document.getElementById('strengthText');

        if (!passwordInput || !strengthBar || !strengthText) return;

        passwordInput.addEventListener('input', () => {
            const password = passwordInput.value;
            const strength = this.calculatePasswordStrength(password);
            
            strengthBar.style.width = `${strength.percentage}%`;
            strengthBar.style.background = strength.color;
            strengthText.textContent = strength.text;
        });
    }

    calculatePasswordStrength(password) {
        let score = 0;
        
        if (password.length >= 8) score += 25;
        if (password.match(/[a-z]/) && password.match(/[A-Z]/)) score += 25;
        if (password.match(/\d/)) score += 25;
        if (password.match(/[^a-zA-Z\d]/)) score += 25;

        if (score >= 75) return { percentage: 100, color: '#10b981', text: 'Strong' };
        if (score >= 50) return { percentage: 75, color: '#f59e0b', text: 'Good' };
        if (score >= 25) return { percentage: 50, color: '#f59e0b', text: 'Fair' };
        return { percentage: 25, color: '#ef4444', text: 'Weak' };
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        // Use your existing notification system or create a simple one
        if (window.notification) {
            window.notification[type](message);
        } else {
            alert(message); // Fallback
        }
    }

    openDashboard() {
        const modal = document.getElementById('dashboardModal');
        if (!modal) {
            console.error('Dashboard modal not found');
            return;
        }
        // Clear previous content and show loading
        modal.innerHTML = `
            <div class="dashboard-loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Loading dashboard...</p>
            </div>
        `;
        
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        // Load dashboard content
        this.loadDashboardContent();
    }

    async loadDashboardContent() {
        try {
            const response = await fetch('/dashboard-content');
            if (!response.ok) throw new Error('Failed to load dashboard');
            
            const html = await response.text();
            const modal = document.getElementById('dashboardModal');
            if (modal) {
                modal.innerHTML = html;
                // Re-initialize dashboard functionality
                this.init();
            }
        } catch (error) {
            console.error('Error loading dashboard:', error);
            const modal = document.getElementById('dashboardModal');
            if (modal) {
                modal.innerHTML = `
                    <div class="dashboard-error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Failed to load dashboard</p>
                        <button onclick="dashboard.loadDashboardContent()" class="retry-btn">
                            Try Again
                        </button>
                    </div>
                `;
            }
        }
    }

    closeDashboard() {
        const modal = document.getElementById('dashboardModal');
        if (modal) {
            modal.classList.remove('active');
            modal.innerHTML = ''; // Clear content
        }
        document.body.style.overflow = 'auto';
    }

    isOpen() {
        const modal = document.getElementById('dashboardModal');
        return modal ? modal.classList.contains('active') : false;
    }
}

// Initialize global dashboard instance
let dashboard = new UserDashboard();

// Dashboard Functions
async function openUserDashboard() {
    if (!(await requireLogin('access dashboard'))) return;
    
    try {
        const response = await fetch('/dashboard-content');  // Changed from '/shop/dashboard-content'
        
        if (!response.ok) {
            if (response.status === 401) {
                alert('Please log in to access dashboard');
                window.location.href = '/login';
                return;
            }
            throw new Error('Failed to load dashboard');
        }
        
        const dashboardModal = document.getElementById('dashboardModal');
        const content = await response.text();
        
        dashboardModal.innerHTML = content;
        dashboardModal.style.display = 'block';
        
        // Add close functionality
        dashboardModal.onclick = function(event) {
            if (event.target === dashboardModal) {
                closeDashboard();
            }
        };
        
    } catch (error) {
        console.error('Error opening dashboard:', error);
        showNotification('Failed to load dashboard', 'error');
    }
}

// Make dashboard globally available
window.dashboard = dashboard;
window.openUserDashboard = openUserDashboard;

// Auto-initialize if dashboard container is already in DOM
document.addEventListener('DOMContentLoaded', function() {
    const dashboardContainer = document.querySelector('.dashboard-container');
    if (dashboardContainer && dashboardContainer.closest('#dashboardModal')) {
        dashboard.init();
    }
});