// notification.js - Reusable notification system

class NotificationSystem {
    constructor() {
        this.initStyles();
    }

    initStyles() {
        // Only add styles once
        if (document.getElementById('notification-styles')) return;

        const styles = `
            /* Success Notification */
            .notification {
                position: fixed;
                top: 20px;
                left: 20px;
                background: linear-gradient(135deg, #10b981, #059669);
                color: white;
                padding: 16px 20px;
                border-radius: 12px;
                box-shadow: 0 8px 25px rgba(16, 185, 129, 0.3);
                z-index: 10000;
                display: flex;
                align-items: center;
                gap: 12px;
                transform: translateX(-400px);
                transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55);
                max-width: 400px;
                border-left: 4px solid #047857;
            }

            .notification.show {
                transform: translateX(0);
            }

            .notification.error {
                background: linear-gradient(135deg, #ef4444, #dc2626);
                border-left: 4px solid #b91c1c;
                box-shadow: 0 8px 25px rgba(239, 68, 68, 0.3);
            }

            .notification.warning {
                background: linear-gradient(135deg, #f59e0b, #d97706);
                border-left: 4px solid #b45309;
                box-shadow: 0 8px 25px rgba(245, 158, 11, 0.3);
            }

            .notification.info {
                background: linear-gradient(135deg, #3b82f6, #1d4ed8);
                border-left: 4px solid #1e40af;
                box-shadow: 0 8px 25px rgba(59, 130, 246, 0.3);
            }

            .notification-icon {
                font-size: 24px;
                flex-shrink: 0;
            }

            .notification-content {
                flex: 1;
            }

            .notification-title {
                font-weight: 700;
                font-size: 16px;
                margin-bottom: 4px;
            }

            .notification-message {
                font-size: 14px;
                opacity: 0.9;
                line-height: 1.4;
            }

            .notification-close {
                background: none;
                border: none;
                color: white;
                font-size: 18px;
                cursor: pointer;
                padding: 4px;
                border-radius: 4px;
                transition: background 0.2s ease;
            }

            .notification-close:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        `;

        const styleSheet = document.createElement('style');
        styleSheet.id = 'notification-styles';
        styleSheet.textContent = styles;
        document.head.appendChild(styleSheet);
    }

    show(type, title, message, duration = 4000) {
        // Remove existing notification if any
        this.hide();

        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };

        // Create notification element
        this.notificationEl = document.createElement('div');
        this.notificationEl.className = `notification ${type}`;
        this.notificationEl.innerHTML = `
            <div class="notification-icon">${icons[type] || 'ℹ️'}</div>
            <div class="notification-content">
                <div class="notification-title">${title}</div>
                <div class="notification-message">${message}</div>
            </div>
            <button class="notification-close" onclick="window.notification.hide()">×</button>
        `;

        // Add to body
        document.body.appendChild(this.notificationEl);

        // Show notification with animation
        setTimeout(() => {
            this.notificationEl.classList.add('show');
        }, 100);

        // Auto remove after duration
        if (duration > 0) {
            this.autoHideTimeout = setTimeout(() => {
                this.hide();
            }, duration);
        }

        return this;
    }

    hide() {
        if (this.autoHideTimeout) {
            clearTimeout(this.autoHideTimeout);
        }

        if (this.notificationEl) {
            this.notificationEl.classList.remove('show');
            setTimeout(() => {
                if (this.notificationEl && this.notificationEl.parentElement) {
                    this.notificationEl.remove();
                }
            }, 400);
        }
    }

    // Convenience methods
    success(message, duration = 4000) {
        return this.show('success', 'Success!', message, duration);
    }

    error(message, duration = 4000) {
        return this.show('error', 'Error!', message, duration);
    }

    warning(message, duration = 4000) {
        return this.show('warning', 'Warning!', message, duration);
    }

    info(message, duration = 4000) {
        return this.show('info', 'Info', message, duration);
    }
}

// Create global instance
window.notification = new NotificationSystem();