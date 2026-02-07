// Dashboard functionality for ATBI User Profile
class UserDashboard {
    constructor() {
        this.currentTab = 'reservations';
        this.isInitialized = false;
        this.userId = null;
        this.setupGlobalFunctions();
    }

    setupGlobalFunctions() {
        window.openUserDashboard = () => this.openDashboard();
        window.dashboard = this;
    }

    async init() {
        if (this.isInitialized) return;
        
        // Get user ID first before loading any data
        await this.getCurrentUser();
        this.bindEvents();
        this.loadDashboardData();
        this.setupPasswordStrength();
        this.isInitialized = true;
    }

    initDashboardFunctionality() {
        this.init();
    }

    async getCurrentUser() {
        try {
            const response = await fetch('/user/current');
            if (response.ok) {
                const userData = await response.json();
                if (userData.success) {
                    this.userId = userData.user_id;
                    this.username = userData.username;
                    sessionStorage.setItem('user_id', this.userId);
                    sessionStorage.setItem('username', this.username);
                    this.updateUserWelcome();
                    return true;
                } else {
                    console.error('Failed to get current user:', userData.message);
                    this.showError('Please log in to access dashboard');
                    this.closeDashboard();
                    return false;
                }
            } else {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
        } catch (error) {
            console.error('Error getting current user:', error);
            this.showError('Unable to verify user session');
            this.closeDashboard();
            return false;
        }
    }

    updateUserWelcome() {
        const usernameElement = document.getElementById('dashboardUsername');
        if (usernameElement && this.username) {
            usernameElement.textContent = this.username;
        }
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

        // Notification controls
        const markAllReadBtn = document.getElementById('markAllNotificationsRead');
        if (markAllReadBtn) {
            markAllReadBtn.addEventListener('click', () => this.markAllNotificationsAsRead());
        }

        const clearAllBtn = document.getElementById('clearAllNotifications');
        if (clearAllBtn) {
            clearAllBtn.addEventListener('click', () => this.clearAllNotifications());
        }

        // Notification filter buttons
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.applyNotificationFilter();
            });
        });

        // Auto-refresh toggle
        const refreshToggle = document.getElementById('autoRefreshToggle');
        if (refreshToggle) {
            refreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.setupNotificationPolling();
                } else {
                    this.stopNotificationPolling();
                }
            });
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
                this.setupNotificationPolling();
                break;
            case 'profile':
                this.stopNotificationPolling();
                this.loadProfileData();
                break;
        }
    }

    async loadDashboardData() {
        if (!this.userId) {
            console.error('No user ID available');
            return;
        }

        await Promise.all([
            this.loadReservations(),
            this.loadNotifications(),
            this.loadUserStats()
        ]);
    }

    async loadReservations() {
        try {
            if (!this.userId) {
                this.showError('User not logged in');
                return;
            }

            const response = await fetch(`/reservations/user/${this.userId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                this.renderReservations(data.reservations);
                this.updateReservationStats(data.reservations);
            } else {
                this.showError(data.message || 'Failed to load reservations');
            }
        } catch (error) {
            console.error('Error loading reservations:', error);
            this.showError('Error loading reservations: ' + error.message);
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
                ${reservation.pending_info ? `
                    <div class="pending-info" style="margin-top: 10px; padding: 10px; background: #f0f9ff; border-radius: 6px; color: #0369a1;">
                        <strong>Pending:</strong> ${reservation.pending_info.time_elapsed_minutes} minutes elapsed, 
                        ${reservation.pending_info.time_remaining_minutes} minutes remaining
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

    // NOTIFICATION FUNCTIONS - Using reservation data to generate notifications
    async loadNotifications() {
        try {
            if (!this.userId) return;

            // Generate notifications from reservation data
            const notifications = await this.generateNotificationsFromReservations();
            this.renderNotifications(notifications);
            this.updateNotificationStats(notifications);

        } catch (error) {
            console.error('Error loading notifications:', error);
        }
    }

    async generateNotificationsFromReservations() {
        try {
            if (!this.userId) return [];

            const response = await fetch(`/reservations/user/${this.userId}`);
            if (!response.ok) return [];

            const data = await response.json();
            if (!data.success) return [];

            const reservations = data.reservations;
            const notifications = [];

            // Create notifications based on reservation status
            reservations.forEach(reservation => {
                const notification = this.createNotificationFromReservation(reservation);
                if (notification) {
                    notifications.push(notification);
                }
            });

            // Sort by date (newest first)
            return notifications.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

        } catch (error) {
            console.error('Error generating notifications:', error);
            return [];
        }
    }

    createNotificationFromReservation(reservation) {
        const baseNotification = {
            notification_id: reservation.reservation_id,
            user_id: this.userId,
            type: 'reservation',
            related_id: reservation.reservation_id,
            related_type: 'reservation',
            created_at: reservation.reserved_at,
            status: 'unread' // You can implement read status logic
        };

        switch(reservation.status) {
            case 'pending':
                return {
                    ...baseNotification,
                    title: '🕒 Reservation Submitted',
                    message: `Your reservation for ${reservation.quantity} ${reservation.product_name} is pending approval. Status will update in 2 minutes.`
                };
            case 'approved':
                return {
                    ...baseNotification,
                    title: '✅ Reservation Approved!',
                    message: `Great news! Your reservation for ${reservation.quantity} ${reservation.product_name} has been approved. You can now proceed to pick up your items.`
                };
            case 'completed':
                return {
                    ...baseNotification,
                    title: '🎉 Pickup Confirmed!',
                    message: `Thank you! Pickup for ${reservation.quantity} ${reservation.product_name} has been confirmed. We hope you enjoy your purchase!`
                };
            case 'rejected':
                return {
                    ...baseNotification,
                    title: '❌ Reservation Rejected',
                    message: `Your reservation for ${reservation.quantity} ${reservation.product_name} was rejected.${reservation.rejected_reason ? ` Reason: ${reservation.rejected_reason}` : ''}`
                };
            default:
                return null;
        }
    }

    renderNotifications(notifications) {
        const container = document.getElementById('notificationsList');
        const emptyState = document.getElementById('notificationsEmptyState');
        const loading = document.getElementById('notificationsLoading');
        
        if (!container) return;

        // Hide loading
        if (loading) loading.style.display = 'none';

        if (!notifications || notifications.length === 0) {
            if (emptyState) emptyState.style.display = 'block';
            container.innerHTML = '';
            return;
        }

        if (emptyState) emptyState.style.display = 'none';

        container.innerHTML = notifications.map(notification => `
            <div class="notification-item ${notification.status} ${notification.type}" 
                 data-notification-id="${notification.notification_id}" 
                 data-type="${notification.type}">
                <div class="notification-icon">
                    <i class="fas fa-${this.getNotificationIcon(notification)}"></i>
                </div>
                <div class="notification-content">
                    <div class="notification-header">
                        <div class="notification-title">${notification.title}</div>
                        <div class="notification-actions">
                            ${notification.status === 'unread' ? `
                                <button class="btn-mark-read" onclick="dashboard.markNotificationAsRead(${notification.notification_id})" 
                                        title="Mark as read">
                                    <i class="fas fa-check"></i>
                                </button>
                            ` : ''}
                            <button class="btn-delete-notification" onclick="dashboard.deleteNotification(${notification.notification_id})" 
                                    title="Delete notification">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="notification-message">${notification.message}</div>
                    <div class="notification-meta">
                        <span class="notification-time">${this.getTimeAgo(notification.created_at)}</span>
                        ${notification.related_type === 'reservation' ? 
                          `<span class="notification-context">Reservation #${notification.related_id}</span>` : ''}
                        ${notification.status === 'unread' ? '<span class="unread-badge">New</span>' : ''}
                    </div>
                </div>
            </div>
        `).join('');

        this.applyNotificationFilter();
    }

    getNotificationIcon(notification) {
        const iconMap = {
            'reservation': {
                'pending': 'clock',
                'approved': 'check-circle',
                'completed': 'party-horn',
                'rejected': 'times-circle',
                'cancelled': 'trash-alt',
                'default': 'shopping-cart'
            },
            'system': 'cog',
            'alert': 'exclamation-triangle'
        };

        if (notification.type === 'reservation') {
            if (notification.title.includes('🕒')) return 'clock';
            if (notification.title.includes('✅')) return 'check-circle';
            if (notification.title.includes('❌')) return 'times-circle';
            if (notification.title.includes('🗑️')) return 'trash-alt';
            if (notification.title.includes('🎉')) return 'party-horn';
            return iconMap.reservation.default;
        }

        return iconMap[notification.type] || 'bell';
    }

    getTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diff = now - date;
        
        if (diff < 60000) return "Just now";
        if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
        return `${Math.floor(diff / 86400000)} days ago`;
    }

    updateNotificationStats(notifications) {
        const total = notifications.length;
        const unread = notifications.filter(n => n.status === 'unread').length;
        const reservationNotifs = notifications.filter(n => n.type === 'reservation').length;
        
        // Update stats bar
        const totalEl = document.getElementById('totalNotifications');
        const unreadEl = document.getElementById('unreadNotifications');
        const reservationEl = document.getElementById('reservationNotifications');
        
        if (totalEl) totalEl.textContent = total;
        if (unreadEl) unreadEl.textContent = unread;
        if (reservationEl) reservationEl.textContent = reservationNotifs;
        
        // Update notification badge in nav
        const navBadge = document.getElementById('notificationCount');
        if (navBadge) {
            navBadge.textContent = unread;
            navBadge.style.display = unread > 0 ? 'flex' : 'none';
        }
    }

    applyNotificationFilter() {
        const activeFilter = document.querySelector('.filter-btn.active')?.dataset.filter || 'all';
        const notifications = document.querySelectorAll('.notification-item');
        
        notifications.forEach(notification => {
            let shouldShow = true;
            
            switch (activeFilter) {
                case 'unread':
                    shouldShow = notification.classList.contains('unread');
                    break;
                case 'reservation':
                    shouldShow = notification.classList.contains('reservation');
                    break;
                case 'system':
                    shouldShow = notification.classList.contains('system');
                    break;
                // 'all' shows everything
            }
            
            notification.style.display = shouldShow ? 'flex' : 'none';
        });
    }

    async markNotificationAsRead(notificationId) {
        try {
            // Since we're using reservation-based notifications, we'll just update the UI
            // In a real implementation, you'd call your notification API
            const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationElement) {
                notificationElement.classList.remove('unread');
                notificationElement.classList.add('read');
                
                const markReadBtn = notificationElement.querySelector('.btn-mark-read');
                if (markReadBtn) {
                    markReadBtn.remove();
                }
            }
            
            // Reload to update stats
            this.loadNotifications();
            this.showSuccess('Notification marked as read');
            
        } catch (error) {
            console.error('Error marking notification as read:', error);
            this.showError('Error marking notification as read');
        }
    }

    async markAllNotificationsAsRead() {
        try {
            // Update all notifications in UI
            document.querySelectorAll('.notification-item.unread').forEach(item => {
                item.classList.remove('unread');
                item.classList.add('read');
                const markReadBtn = item.querySelector('.btn-mark-read');
                if (markReadBtn) markReadBtn.remove();
            });
            
            // Reload to update stats
            this.loadNotifications();
            this.showSuccess('All notifications marked as read');
            
        } catch (error) {
            console.error('Error marking all notifications as read:', error);
            this.showError('Error marking notifications as read');
        }
    }

    async deleteNotification(notificationId) {
        if (!confirm('Are you sure you want to delete this notification?')) {
            return;
        }

        try {
            // Remove from UI
            const notificationElement = document.querySelector(`[data-notification-id="${notificationId}"]`);
            if (notificationElement) {
                notificationElement.remove();
            }
            
            // Reload to update stats
            this.loadNotifications();
            this.showSuccess('Notification deleted');
            
        } catch (error) {
            console.error('Error deleting notification:', error);
            this.showError('Error deleting notification');
        }
    }

    async clearAllNotifications() {
        if (!confirm('Are you sure you want to clear all notifications? This action cannot be undone.')) {
            return;
        }

        try {
            // Clear all notifications from UI
            const container = document.getElementById('notificationsList');
            if (container) {
                container.innerHTML = '';
            }
            
            // Show empty state
            const emptyState = document.getElementById('notificationsEmptyState');
            if (emptyState) {
                emptyState.style.display = 'block';
            }
            
            // Update stats
            this.updateNotificationStats([]);
            this.showSuccess('All notifications cleared');
            
        } catch (error) {
            console.error('Error clearing all notifications:', error);
            this.showError('Error clearing notifications');
        }
    }

    setupNotificationPolling() {
        // Start/stop polling based on toggle and active tab
        this.stopNotificationPolling(); // Clear existing interval
        
        this.notificationPollingInterval = setInterval(() => {
            const toggle = document.getElementById('autoRefreshToggle');
            const isNotificationsTab = this.currentTab === 'notifications';
            
            if (toggle?.checked && isNotificationsTab) {
                this.loadNotifications();
            }
        }, 30000); // 30 seconds
    }

    stopNotificationPolling() {
        if (this.notificationPollingInterval) {
            clearInterval(this.notificationPollingInterval);
            this.notificationPollingInterval = null;
        }
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

    async loadProfileData() {
        try {
            const response = await fetch('/user/profile');
            if (response.ok) {
                const data = await response.json();
                if (data.success) {
                    this.populateProfileForm(data.profile);
                } else {
                    console.error('Failed to load profile:', data.message);
                }
            }
        } catch (error) {
            console.error('Error loading profile data:', error);
        }
    }

    populateProfileForm(profile) {
        const emailInput = document.getElementById('email');
        const phoneInput = document.getElementById('phone');
        const usernameInput = document.getElementById('username');
        
        if (emailInput && profile.email) emailInput.value = profile.email;
        if (phoneInput && profile.phone) phoneInput.value = profile.phone;
        if (usernameInput && profile.username) {
            usernameInput.value = profile.username;
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

        // Client-side validation
        if (!data.currentPassword) {
            this.showError('Current password is required');
            return;
        }

        if (!data.newPassword) {
            this.showError('New password is required');
            return;
        }

        if (data.newPassword !== data.confirmPassword) {
            this.showError('New passwords do not match');
            return;
        }

        if (data.newPassword.length < 6) {
            this.showError('New password must be at least 6 characters long');
            return;
        }

        try {
            const response = await fetch('/user/change-password', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    currentPassword: data.currentPassword,
                    newPassword: data.newPassword,
                    confirmPassword: data.confirmPassword
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showSuccess('Password changed successfully');
                e.target.reset();
                
                // Reset password strength indicator
                const strengthBar = document.querySelector('.strength-bar');
                const strengthText = document.getElementById('strengthText');
                if (strengthBar && strengthText) {
                    strengthBar.style.width = '25%';
                    strengthBar.style.background = '#ef4444';
                    strengthText.textContent = 'Weak';
                }
            } else {
                this.showError(result.message || 'Failed to change password');
            }
        } catch (error) {
            console.error('Error changing password:', error);
            this.showError('Error changing password');
        }
    }

    async init() {
        if (this.isInitialized) return;
        
        // Get user ID first before loading any data
        const userLoaded = await this.getCurrentUser();
        if (!userLoaded) {
            return; // Stop initialization if user is not authenticated
        }
        
        this.bindEvents();
        this.loadDashboardData();
        this.setupPasswordStrength();
        this.isInitialized = true;
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
                this.loadNotifications(); // Refresh notifications
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
                this.loadNotifications(); // Refresh notifications
            } else {
                this.showError(result.message || 'Failed to confirm pickup');
            }
        } catch (error) {
            console.error('Error confirming pickup:', error);
            this.showError('Error confirming pickup');
        }
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

    async openDashboard() {
        try {
            // First check if user is logged in by calling your auth endpoint
            const authCheck = await fetch('/auth/check');
            const authResult = await authCheck.json();
            
            if (!authResult.authenticated) {
                // User is not logged in, redirect to login page
                window.location.href = '/login';
                return;
            }
            
            // User is authenticated, proceed with opening dashboard
            const modal = document.getElementById('dashboardModal');
            if (!modal) {
                console.error('Dashboard modal not found');
                return;
            }
            
            modal.innerHTML = `
                <div class="dashboard-loading">
                    <i class="fas fa-spinner fa-spin"></i>
                    <p>Loading dashboard...</p>
                </div>
            `;
            
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';

            // Load dashboard content
            await this.loadDashboardContent();
            // Initialize dashboard functionality
            await this.init();
            
        } catch (error) {
            console.error('Error opening dashboard:', error);
            // If there's an error checking auth, redirect to login
            window.location.href = '/login';
        }
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
                await this.init();
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
        this.stopNotificationPolling();
    }

    isOpen() {
        const modal = document.getElementById('dashboardModal');
        return modal ? modal.classList.contains('active') : false;
    }
}

// Initialize global dashboard instance
let dashboard = new UserDashboard();

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