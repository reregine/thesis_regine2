// Notification System - Included directly in cart.js
if (typeof window.notification === 'undefined') {
    class NotificationSystem {
        constructor() {
            this.initStyles();
        }

        initStyles() {
            if (document.getElementById('notification-styles')) return;

            const styles = `
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
                .notification.show { transform: translateX(0); }
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
                .notification-icon { font-size: 24px; flex-shrink: 0; }
                .notification-content { flex: 1; }
                .notification-title { font-weight: 700; font-size: 16px; margin-bottom: 4px; }
                .notification-message { font-size: 14px; opacity: 0.9; line-height: 1.4; }
                .notification-close {
                    background: none; border: none; color: white; font-size: 18px;
                    cursor: pointer; padding: 4px; border-radius: 4px;
                    transition: background 0.2s ease;
                }
                .notification-close:hover { background: rgba(255, 255, 255, 0.2); }
            `;

            const styleSheet = document.createElement('style');
            styleSheet.id = 'notification-styles';
            styleSheet.textContent = styles;
            document.head.appendChild(styleSheet);
        }

        show(type, title, message, duration = 4000) {
            this.hide();
            const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
            
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

            document.body.appendChild(this.notificationEl);
            setTimeout(() => this.notificationEl.classList.add('show'), 100);
            if (duration > 0) {
                this.autoHideTimeout = setTimeout(() => this.hide(), duration);
            }
            return this;
        }

        hide() {
            if (this.autoHideTimeout) clearTimeout(this.autoHideTimeout);
            if (this.notificationEl) {
                this.notificationEl.classList.remove('show');
                setTimeout(() => {
                    if (this.notificationEl && this.notificationEl.parentElement) {
                        this.notificationEl.remove();
                    }
                }, 400);
            }
        }

        success(message, duration = 4000) { return this.show('success', 'Success!', message, duration); }
        error(message, duration = 4000) { return this.show('error', 'Error!', message, duration); }
        warning(message, duration = 4000) { return this.show('warning', 'Warning!', message, duration); }
    }

    window.notification = new NotificationSystem();
}

// 🟢 GLOBAL DEBOUNCING VARIABLES
let quantityUpdateTimeout = null;
const DEBOUNCE_DELAY = 800; // Wait 800ms after user stops clicking

// 🟢 GLOBAL HELPER FUNCTIONS - MOVED OUTSIDE OF attachCartScripts
window.getUserId = function() {
    // Try sessionStorage first
    let userId = sessionStorage.getItem('user_id');
    
    if (!userId) {
        // Try to get from the page if available
        const userDataElement = document.querySelector('[data-user-id]');
        if (userDataElement) {
            userId = userDataElement.getAttribute('data-user-id');
            if (userId) {
                sessionStorage.setItem('user_id', userId);
            }
        }
    }
    
    return userId || ''; // Return empty string if not found, don't fetch here
}

// 🟢 GLOBAL: Fetch user info from server
window.fetchUserInfo = async function() {
    try {
        const res = await fetch("/login/status");
        if (res.ok) {
            const data = await res.json();
            if (data.success && data.user_id) {
                sessionStorage.setItem("user_id", data.user_id);
                sessionStorage.setItem("username", data.username || "");
                console.log("User ID fetched from server:", data.user_id);
                return data.user_id;
            }
        }
    } catch (err) {
        console.error("Error fetching user info:", err);
    }
    return null;
}

// 🟢 GLOBAL: Load reservation counts for all status tabs
window.loadReservationCounts = async function(container) {
    try {
        const res = await fetch(`/cart/reservations/count`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        if (data.success) {
            const counts = data.counts;
            
            // Update tab counts in the UI
            Object.keys(counts).forEach(status => {
                const tab = container.querySelector(`.status-tab[data-tab="${status}"]`);
                if (tab) {
                    const badge = tab.querySelector('.tab-count');
                    if (badge) {
                        badge.textContent = counts[status];
                        // Show/hide badge based on count
                        if (counts[status] > 0) {
                            badge.style.display = 'inline-flex';
                        } else {
                            badge.style.display = 'none';
                        }
                    }
                }
            });
            
            console.log("Reservation counts updated:", counts);
            return counts;
        } else {
            console.error("Failed to load reservation counts:", data.message);
            return { pending: 0, approved: 0, completed: 0, rejected: 0 };
        }
    } catch (err) {
        console.error("❌ Error loading reservation counts:", err);
        return { pending: 0, approved: 0, completed: 0, rejected: 0 };
    }
};

// 🟢 GLOBAL: Enhanced loadReservationsByStatus with pagination
window.loadReservationsByStatus = async function(status, container, page = 1) {
    const dynamicContent = container.querySelector("#dynamicContent");
    if (!dynamicContent) return;

    try {
        // Show loading state with pagination info
        dynamicContent.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:#666;">
                <div style="font-size:32px;margin-bottom:12px;">⏳</div>
                <p>Loading ${status} reservations...</p>
                <small>Page ${page}</small>
            </div>
        `;

        console.log(`Loading ${status} reservations, page ${page}`);
        
        // Use the new paginated endpoint
        const res = await fetch(`/cart/reservations/${status}?page=${page}&per_page=10`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);

        const data = await res.json();
        
        if (data.success) {
            const reservations = data.reservations || [];
            const pagination = data.pagination || {};
            
            console.log(`Found ${reservations.length} ${status} reservations on page ${page}`);
            
            if (reservations.length === 0) {
                dynamicContent.innerHTML = `
                <div class="empty-status">
                    <img src="https://cdn-icons-png.flaticon.com/512/4076/4076505.png" alt="No ${status} reservations">
                    <p>No ${status} reservations</p>
                    <small>
                        ${status === 'pending' ? 'Reservations waiting for approval will appear here' : 
                            status === 'approved' ? 'Approved reservations ready for pickup/delivery' :
                            status === 'completed' ? 'Completed reservations history' :
                            'Rejected reservations with reasons'}
                    </small>
                </div>`;
            } else {
                // Render reservations
                let reservationsHTML = reservations.map(reservation => {
                    // Image path handling
                    let imagePath = reservation.image_path;
                    
                    if (imagePath) {
                        // Handle Windows absolute path
                        if (imagePath.includes('\\')) {
                            const parts = imagePath.split('\\');
                            const filename = parts[parts.length - 1];
                            imagePath = `/static/uploads/${filename}`;
                        } else if (imagePath.includes('/')) {
                            const parts = imagePath.split('/');
                            const filename = parts[parts.length - 1];
                            imagePath = `/static/uploads/${filename}`;
                        } else {
                            imagePath = `/static/uploads/${imagePath}`;
                        }
                    } else {
                        imagePath = 'https://cdn-icons-png.flaticon.com/512/4076/4076505.png';
                    }
                    
                    // Format date
                    const reservedDate = new Date(reservation.reserved_at);
                    const formattedDate = new Intl.DateTimeFormat('en-US', {
                        timeZone: 'Asia/Manila',
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit', 
                        minute: '2-digit',
                        hour12: true
                    }).format(reservedDate);
                    
                    // Use server-provided discount percentage
                    const discountPercentage = reservation.discount_percentage || 0;
                    
                    const priceDisplay = reservation.new_price_per_stocks && parseFloat(reservation.new_price_per_stocks) < parseFloat(reservation.price_per_stocks) ?
                        `
                        <div class="price-comparison" style="margin-bottom: 4px;">
                            <div class="current-price" style="color: #10b981; font-weight: 700;">
                                ₱${parseFloat(reservation.new_price_per_stocks).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                            <div class="original-price" style="color: #9ca3af; font-size: 12px; text-decoration: line-through;">
                                ₱${parseFloat(reservation.price_per_stocks).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                        </div>
                        `
                        :
                        `<div class="reservation-price">₱${reservation.price_per_stocks.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>`;
                    
                    return `
                    <div class="reservation-item" data-reservation-id="${reservation.reservation_id}">
                        <div class="image-container" style="position: relative;">
                            ${discountPercentage > 0 ? 
                                `<div class="discount-badge" style="position: absolute; top: 5px; right: 5px; background: linear-gradient(135deg, #ef4444, #dc2626); color: white; font-size: 9px; padding: 3px 5px; border-radius: 4px; font-weight: 700;">
                                    ${discountPercentage}% OFF
                                </div>` 
                                : ''
                            }
                            <img src="${imagePath}" alt="${reservation.product_name}" 
                                onerror="this.onerror=null; this.src='https://cdn-icons-png.flaticon.com/512/4076/4076505.png'">
                        </div>
                        <div class="reservation-info">
                            <div class="reservation-name">${reservation.product_name}</div>
                            
                            <!-- Use priceDisplay here -->
                            ${priceDisplay}
                            
                            <div class="reservation-meta">
                                <div class="reservation-quantity">Quantity: ${reservation.quantity}</div>
                                <div class="reservation-date">Reserved: ${formattedDate}</div>
                            </div>
                            
                            <div class="status-section">
                                <div class="status-badge status-${reservation.status}">
                                    ${reservation.status.toUpperCase()}
                                </div>
                                ${reservation.status === 'pending' ? `
                                <div class="reservation-actions">
                                    <button class="action-btn secondary" 
                                            onclick="cancelReservation(${reservation.reservation_id}, '${reservation.product_name.replace(/'/g, "\\'")}')">
                                        Cancel
                                    </button>
                                </div>
                                ` : ''}

                                ${reservation.status === 'completed' ? `
                                <div class="reservation-actions" style="margin-top: 12px;">
                                    <button class="action-btn secondary" 
                                            onclick="window.showVoidRequestModal(${reservation.reservation_id}, '${reservation.product_name.replace(/'/g, "\\'")}', ${reservation.quantity})"
                                            style="padding: 6px 16px; border-radius: 8px; font-size: 13px; 
                                                font-weight: 600; cursor: pointer; background: #f3f4f6; 
                                                border: 1px solid #d1d5db; color: #dc2626; transition: all 0.3s;">
                                        🔄 Request Return
                                    </button>
                                </div>
                                ` : ''}
                            </div>
                            
                            ${reservation.rejected_reason ? `
                            <div class="rejection-reason">
                                ${reservation.rejected_reason}
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    `;
                }).join("");
                
                // Add pagination controls if needed
                if (pagination.pages > 1) {
                    const paginationHTML = createPaginationControls(pagination, status, page);
                    reservationsHTML += paginationHTML;
                }
                
                dynamicContent.innerHTML = reservationsHTML;
                
                // Attach pagination event listeners
                attachPaginationListeners(container, status);
            }
        } else {
            dynamicContent.innerHTML = `
                <div style="text-align:center;padding:40px 20px;color:#d32f2f;">
                    <div style="font-size:32px;margin-bottom:12px;">❌</div>
                    <p>${data.message || "Failed to load reservations."}</p>
                </div>`;
        }
    } catch (err) {
        console.error(`❌ Error loading ${status} reservations:`, err);
        dynamicContent.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:#d32f2f;">
                <div style="font-size:32px;margin-bottom:12px;">⚠️</div>
                <p>Server error while loading ${status} reservations.</p>
            </div>`;
    }
};

// Helper function to create pagination controls
function createPaginationControls(pagination, status, currentPage) {
    let html = `
    <div class="pagination-container" style="margin-top: 20px; padding: 15px; text-align: center; border-top: 1px solid #e5e7eb;">
        <div style="display: flex; justify-content: center; align-items: center; gap: 10px;">
    `;
    
    // Previous button
    if (pagination.has_prev) {
        html += `<button class="pagination-btn prev" data-page="${currentPage - 1}" data-status="${status}" 
                 style="padding: 8px 16px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.3s;">
                 ← Previous</button>`;
    } else {
        html += `<button disabled style="padding: 8px 16px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px; color: #9ca3af; cursor: not-allowed;">
                 ← Previous</button>`;
    }
    
    // Page info
    html += `<span style="font-size: 14px; color: #6b7280; padding: 0 10px;">
                Page ${currentPage} of ${pagination.pages}
             </span>`;
    
    // Next button
    if (pagination.has_next) {
        html += `<button class="pagination-btn next" data-page="${currentPage + 1}" data-status="${status}"
                 style="padding: 8px 16px; background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 8px; cursor: pointer; transition: all 0.3s;">
                 Next →</button>`;
    } else {
        html += `<button disabled style="padding: 8px 16px; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 8px; color: #9ca3af; cursor: not-allowed;">
                 Next →</button>`;
    }
    
    html += `
        </div>
        <div style="font-size: 12px; color: #9ca3af; margin-top: 8px;">
            Showing ${Math.min(pagination.per_page, pagination.total)} of ${pagination.total} items
        </div>
    </div>
    `;
    
    return html;
}

// Helper function to attach pagination event listeners
function attachPaginationListeners(container, status) {
    const paginationBtns = container.querySelectorAll('.pagination-btn');
    paginationBtns.forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const page = parseInt(e.target.dataset.page);
            const status = e.target.dataset.status;
            
            if (page && status) {
                await window.loadReservationsByStatus(status, container, page);
                
                // Scroll to top of the dynamic content
                const dynamicContent = container.querySelector("#dynamicContent");
                if (dynamicContent) {
                    dynamicContent.scrollTop = 0;
                }
            }
        });
    });
}

// 🟢 GLOBAL: Initialize status tabs with auto-loading
window.initializeStatusTabs = async function(container) {
    const tabs = container.querySelectorAll(".status-tab");
    
    // Load reservation counts using the optimized endpoint
    await window.loadReservationCounts(container);
    
    // Set up click events
    tabs.forEach((tab) => {
        tab.addEventListener("click", async () => {
            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");
            const tabName = tab.dataset.tab;
            
            // 🟢 FIX: Handle void tab separately
            if (tabName === 'void') {
                // Load void requests from void blueprint
                await window.loadVoidRequests(container);
            } else {
                // Load regular reservations from cart blueprint
                await window.loadReservationsByStatus(tabName, container, 1);
            }
        });
    });
    
    // Auto-show pending tab if there are pending reservations
    const pendingTab = container.querySelector('.status-tab[data-tab="pending"]');
    const pendingBadge = pendingTab ? pendingTab.querySelector('.tab-count') : null;
    const pendingCount = pendingBadge ? parseInt(pendingBadge.textContent) || 0 : 0;
    
    if (pendingCount > 0) {
        // Switch to pending tab automatically and load first page
        tabs.forEach(t => t.classList.remove("active"));
        pendingTab.classList.add("active");
        await window.loadReservationsByStatus("pending", container, 1);
    } else {
        // Otherwise load the first non-void tab (usually pending)
        const firstNonVoidTab = Array.from(tabs).find(tab => tab.dataset.tab !== 'void');
        if (firstNonVoidTab) {
            firstNonVoidTab.classList.add("active");
            const firstTabName = firstNonVoidTab.dataset.tab;
            await window.loadReservationsByStatus(firstTabName, container, 1);
        }
    }
};

// Modern confirmation dialog for cancel reservation
window.cancelReservation = async function(reservationId, productName = 'this product') {
    return new Promise((resolve) => {
        const dialogOverlay = document.createElement('div');
        dialogOverlay.className = 'confirm-dialog-overlay';
        dialogOverlay.innerHTML = `
            <div class="confirm-dialog">
                <div class="confirm-dialog-icon">⚠️</div>
                <div class="confirm-dialog-title">Cancel Reservation?</div>
                <div class="confirm-dialog-message">
                    Are you sure you want to cancel the reservation for <strong>${productName}</strong>? 
                    This item will be returned to your cart.
                </div>
                <div class="confirm-dialog-buttons">
                    <button class="confirm-btn no">Keep Reserved</button>
                    <button class="confirm-btn yes">Yes, Cancel</button>
                </div>
            </div>
        `;

        document.body.appendChild(dialogOverlay);

        setTimeout(() => {
            dialogOverlay.classList.add('show');
            dialogOverlay.querySelector('.confirm-dialog').classList.add('show');
        }, 10);

        const noBtn = dialogOverlay.querySelector('.confirm-btn.no');
        const yesBtn = dialogOverlay.querySelector('.confirm-btn.yes');

        const closeDialog = async (confirmed) => {
            dialogOverlay.classList.remove('show');
            dialogOverlay.querySelector('.confirm-dialog').classList.remove('show');
            
            setTimeout(() => {
                if (dialogOverlay.parentElement) {
                    dialogOverlay.remove();
                }
            }, 300);

            if (confirmed) {
                try {
                    const response = await fetch(`/cart/cancel-reservation/${reservationId}`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        }
                    });

                    const data = await response.json();
                    
                    if (data.success) {
                        window.notification.success("Reservation canceled! Item returned to cart.", 4000);
                        
                        // Enhanced refresh: reload both counts and current tab
                        const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
                        if (container) {
                            // Reload reservation counts
                            await window.loadReservationCounts(container);
                            
                            // Get current active tab and reload it
                            const activeTab = container.querySelector('.status-tab.active');
                            const currentTab = activeTab ? activeTab.dataset.tab : 'pending';
                            await window.loadReservationsByStatus(currentTab, container);
                            
                            console.log("Reservation canceled, refreshed:", currentTab);
                        }
                    } else {
                        window.notification.error(data.message || "Failed to cancel reservation", 4000);
                    }
                } catch (error) {
                    console.error('Error canceling reservation:', error);
                    window.notification.error("Error canceling reservation. Please try again.", 4000);
                }
            }
            
            resolve(confirmed);
        };

        noBtn.addEventListener('click', () => closeDialog(false));
        yesBtn.addEventListener('click', () => closeDialog(true));

        dialogOverlay.addEventListener('click', (e) => {
            if (e.target === dialogOverlay) {
                closeDialog(false);
            }
        });

        const escHandler = (e) => {
            if (e.key === 'Escape') {
                closeDialog(false);
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    });
};

document.addEventListener("DOMContentLoaded", () => {
    const openCartBtn = document.getElementById("openCartBtn");
    const cartModal = document.getElementById("cartModal");
    const cartContent = document.getElementById("cartContent");

    // 🛒 Open cart modal and load cart.html from Flask
    if (openCartBtn) {
        openCartBtn.addEventListener("click", async (e) => {
            e.preventDefault();
            if (!cartModal || !cartContent) return;

            cartModal.classList.add("active");

            try {
                const response = await fetch("/cart/");
                const html = await response.text();
                cartContent.innerHTML = html;
                attachCartScripts(cartContent);
            } catch (err) {
                cartContent.innerHTML = "<p style='padding:20px;color:red;'>Failed to load cart.</p>";
                console.error("Error loading cart:", err);
            }
        });
    }

    // ✖️ Close modal
    if (cartModal) {
        cartModal.addEventListener("click", (e) => {
            if (e.target.classList.contains("close-cart") || e.target === cartModal) {
                cartModal.classList.remove("active");
                // 🟢 Clean up any pending quantity updates
                if (window.cleanupQuantityUpdates) {
                    window.cleanupQuantityUpdates();
                }
            }
        });
    }

    // ⎋ ESC to close
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && cartModal) {
            cartModal.classList.remove("active");
            // 🟢 Clean up any pending quantity updates
            if (window.cleanupQuantityUpdates) {
                window.cleanupQuantityUpdates();
            }
        }
    });
});
document.addEventListener('DOMContentLoaded', function() {
    const tabsContainer = document.querySelector('.status-tabs-container');
    const tabs = document.querySelector('.status-tabs');
    
    function checkScrollable() {
        if (tabsContainer && tabs) {
            if (tabs.scrollWidth > tabsContainer.clientWidth) {
                tabsContainer.classList.add('scrollable');
            } else {
                tabsContainer.classList.remove('scrollable');
            }
        }
    }
    
    // Check on load
    checkScrollable();
    
    // Check on window resize
    window.addEventListener('resize', checkScrollable);
});
// ======================
// Internal cart scripts - UPDATED WITH SMOOTH QUANTITY UPDATES
// ======================
function attachCartScripts(container) {
    if (!container) return;

    // IMMEDIATELY LOAD CART ITEMS WHEN CART OPENS
    loadCartItems(container);
    // Status Tabs - Load reservation counts and set up click events
    window.initializeStatusTabs(container);
    window.initializeVoidTab(container);
    // FIXED: Load cart items function - SINGLE DEFINITION
    async function loadCartItems(container) {
        const cartItemsContainer = container.querySelector("#cartItems");
        const cartCountElem = container.querySelector("#cartCount");
        const totalElem = container.querySelector("#totalAmount");

        if (!cartItemsContainer) return;

        try {
            // Show loading state
            cartItemsContainer.innerHTML = "<p style='text-align:center;color:#999;'>Loading your cart...</p>";

            const res = await fetch("/cart/get-items");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            
            if (!data.success) {
                cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">${data.message || "Failed to load cart."}</p>`;
                if (cartCountElem) cartCountElem.textContent = "0 items";
                if (totalElem) totalElem.textContent = "Total: ₱0.00";
                return;
            }

            const items = data.items || [];
            
            if (items.length === 0) {
                cartItemsContainer.innerHTML = `
                <div class="empty-cart">
                    <p style="text-align:center;color:#999;padding:40px 20px;">
                    Your cart is empty<br>
                    <small>Add some products to get started!</small>
                    </p>
                </div>`;
                if (cartCountElem) cartCountElem.textContent = "0 items";
                if (totalElem) totalElem.textContent = "Total: ₱0.00";
                return;
            }

            // RENDER THE ACTUAL CART ITEMS
            renderCartItems(items, container);
            
        } catch (err) {
            console.error("❌ Error loading cart:", err);
            cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">Server error while loading cart.</p>`;
        }
    }

    //global refresh function
    window.refreshStatusSection = async function() {
        const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
        if (!container) return;
        
        // Reload counts first
        const counts = await window.loadReservationCounts(container);
        
        // Get current active tab
        const activeTab = container.querySelector('.status-tab.active');
        const currentTab = activeTab ? activeTab.dataset.tab : 'pending';
        
        console.log("Refreshing status section, current tab:", currentTab);
        
        // Reload the current tab's content
        await window.loadReservationsByStatus(currentTab, container);
    };

    // Render cart items function with checkboxes - UPDATED WITH EVENT DELEGATION
    function renderCartItems(items, container) {
        const cartItemsContainer = container.querySelector("#cartItems");

        if (!cartItemsContainer) return;

        cartItemsContainer.innerHTML = items.map(item => {
            // FIXED: Proper image path handling for cart items
            let imgSrc = item.image_path;
            
            console.log("Cart item original image path:", imgSrc); // Debug log
            
            if (imgSrc) {
                // Handle Windows absolute path: D:\documents\thesis_regine2\app\static\uploads\filename.jpg
                // Extract just the filename from any path format
                let filename;
                
                if (imgSrc.includes('\\')) {
                    // Windows path with backslashes
                    const parts = imgSrc.split('\\');
                    filename = parts[parts.length - 1]; // Get last part (filename)
                } else if (imgSrc.includes('/')) {
                    // Unix path or URL with forward slashes
                    const parts = imgSrc.split('/');
                    filename = parts[parts.length - 1]; // Get last part (filename)
                } else {
                    // Just a filename
                    filename = imgSrc;
                }
                
                // Use the correct web path - relative to your Flask static folder
                imgSrc = `/static/uploads/${filename}`;
                console.log("Cart item converted image path:", imgSrc); // Debug log
            } else {
                // Fallback image
                imgSrc = '/static/images/no-image.png';
            }
            
            const price = parseFloat(item.price_per_stocks || 0);
            const stockAmount = parseInt(item.stock_amount || 0);
            const currentQuantity = parseInt(item.quantity || 1);

            return `
            <div class="cart-item" data-cart-id="${item.cart_id}" data-product-id="${item.product_id}" data-stock="${stockAmount}" data-price="${price}">
                <input type="checkbox" class="item-checkbox">
                
                <!-- Image container with discount badge -->
                <div class="image-container">
                    ${item.discount_percentage > 0 ?  // CHANGED: Use item.discount_percentage
                        `<div class="discount-badge">
                            <span class="discount-percent">${item.discount_percentage}% OFF</span>
                        </div>` 
                        : ''
                    }
                    <img src="${imgSrc}" alt="${item.name}" 
                        onerror="this.onerror=null; this.src='/static/images/no-image.png'">
                </div>
                
                <div class="item-info">
                    <div class="item-name">${item.name}</div>
                    
                    <!-- Price comparison section -->
                    <div class="price-comparison">
                        ${item.new_price_per_stocks && parseFloat(item.new_price_per_stocks) < parseFloat(item.price_per_stocks) ? 
                            `
                            <div class="current-price">
                                ₱${parseFloat(item.new_price_per_stocks).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                            <div class="original-price">
                                ₱${parseFloat(item.price_per_stocks).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                            <div class="discount-amount">
                                Save ₱${(parseFloat(item.price_per_stocks) - parseFloat(item.new_price_per_stocks)).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </div>
                            `
                            :
                            `<div class="current-price">₱${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>`
                        }
                    </div>
                    
                    ${stockAmount < currentQuantity ? 
                        `<div class="stock-warning">Only ${stockAmount} left in stock</div>` : 
                        `<div class="stock-info">${stockAmount} available</div>`
                    }
                    <div class="quantity">
                        <button class="qty-btn decrease" data-cart-id="${item.cart_id}" data-action="decrease" ${currentQuantity <= 1 ? 'disabled' : ''}>-</button>
                        <span class="qty">${currentQuantity}</span>
                        <button class="qty-btn increase" data-cart-id="${item.cart_id}" data-action="increase" ${currentQuantity >= stockAmount ? 'disabled' : ''}>+</button>
                    </div>
                    <div class="quantity-message" id="message-${item.cart_id}" style="display:none; font-size:12px; margin-top:5px;"></div>
                </div>
                <button class="delete-btn" data-cart-id="${item.cart_id}" 
                        style="background:none;border:none;color:#dc2626;cursor:pointer;padding:5px;font-size:16px;">🗑️</button>
            </div>`;
        }).join("");

        // 🟢 CRITICAL FIX: Attach event listeners using event delegation
        attachDynamicCartEvents(container);
        
        // Initialize select all functionality
        initializeSelectAll(container);
        
        // Update counts and totals
        updateCartTotals(container);
    }

    // 🟢 Add helper function to get current cart container
    window.getCurrentCartContainer = function() {
        return document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
    }

    // Initialize Select All functionality
    function initializeSelectAll(container) {
        const selectAllCheckbox = container.querySelector("#selectAll");
        const itemCheckboxes = container.querySelectorAll(".item-checkbox");

        // Reset Select All checkbox to unchecked
        if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        }

        if (selectAllCheckbox) {
            // Select All checkbox event
            selectAllCheckbox.addEventListener("change", function() {
                const isChecked = this.checked;
                itemCheckboxes.forEach(checkbox => {
                    checkbox.checked = isChecked;
                });
                updateCartTotals(container);
            });

            // Individual checkbox events
            itemCheckboxes.forEach(checkbox => {
                checkbox.addEventListener("change", function() {
                    // Update Select All checkbox state
                    const allChecked = Array.from(itemCheckboxes).every(cb => cb.checked);
                    const someChecked = Array.from(itemCheckboxes).some(cb => cb.checked);
                    
                    selectAllCheckbox.checked = allChecked;
                    selectAllCheckbox.indeterminate = someChecked && !allChecked;
                    
                    updateCartTotals(container);
                });
            });
        }
    }

    // 🟢 UPDATED: Event delegation for dynamic content
    function attachDynamicCartEvents(container) {
        // Use event delegation for quantity buttons
        container.addEventListener('click', async (e) => {
            const target = e.target;
            
            // Handle quantity decrease
            if (target.classList.contains('decrease')) {
                const cartId = parseInt(target.dataset.cartId);
                const cartItem = target.closest('.cart-item');
                const qtyElement = cartItem.querySelector('.qty');
                const currentQuantity = parseInt(qtyElement.textContent);
                
                if (currentQuantity > 1) {
                    await window.smoothUpdateQuantity(cartId, currentQuantity - 1, target);
                }
            }
            
            // Handle quantity increase
            if (target.classList.contains('increase')) {
                const cartId = parseInt(target.dataset.cartId);
                const cartItem = target.closest('.cart-item');
                const qtyElement = cartItem.querySelector('.qty');
                const currentQuantity = parseInt(qtyElement.textContent);
                
                await window.smoothUpdateQuantity(cartId, currentQuantity + 1, target);
            }
            
            // Handle delete buttons
            if (target.classList.contains('delete-btn')) {
                const cartId = parseInt(target.dataset.cartId);
                await window.removeFromCart(cartId);
            }
        });

        // Handle checkbox changes with event delegation
        container.addEventListener('change', (e) => {
            if (e.target.classList.contains('item-checkbox')) {
                updateCartTotals(container);
            }
        });
    }

    // Update cart totals based on selected items
    function updateCartTotals(container, items = null) {
        if (!container) {
            container = window.getCurrentCartContainer();
        }
        
        const cartItemsContainer = container.querySelector("#cartItems");
        const totalElem = container.querySelector("#totalAmount");
        const cartCountElem = container.querySelector("#cartCount");
        const reserveBtn = container.querySelector(".reserve-btn");

        if (!cartItemsContainer || !totalElem) return;

        let total = 0;
        let selectedProducts = 0;
        let totalProducts = 0;
        let selectedItemsCount = 0;

        // Get all cart items
        const cartItems = cartItemsContainer.querySelectorAll(".cart-item");
        
        cartItems.forEach(item => {
            const checkbox = item.querySelector(".item-checkbox");
            const price = parseFloat(item.dataset.price || 0);
            const qty = parseInt(item.querySelector(".qty").textContent) || 0;
            totalProducts++;
            
            if (checkbox.checked) {
                total += price * qty;
                selectedProducts++;
                selectedItemsCount += qty;
            }
        });

        // Update total display
        totalElem.textContent = `Total: ₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
        
        // Update cart count
        if (cartCountElem) {
            if (selectedProducts > 0) {
                cartCountElem.textContent = `${selectedProducts} of ${totalProducts} products selected`;
            } else {
                cartCountElem.textContent = `${totalProducts} products`;
            }
        }

        // Update reserve button text
        if (reserveBtn) {
            if (selectedProducts > 0) {
                reserveBtn.textContent = `Reserve Selected (${selectedProducts} products)`;
                reserveBtn.disabled = false;
                reserveBtn.style.background = 'var(--green)';
                reserveBtn.style.cursor = 'pointer';
            } else {
                reserveBtn.textContent = "Select products to reserve";
                reserveBtn.disabled = true;
                reserveBtn.style.background = '#9ca3af';
                reserveBtn.style.cursor = 'not-allowed';
            }
        }
    }

    // UPDATED: Smooth quantity update with real-time stock validation
    window.smoothUpdateQuantity = async function(cartId, newQuantity, buttonElement) {
        const cartItem = buttonElement.closest('.cart-item');
        const qtyElement = cartItem.querySelector('.qty');
        const checkbox = cartItem.querySelector('.item-checkbox');
        const decreaseBtn = cartItem.querySelector('.decrease');
        const increaseBtn = cartItem.querySelector('.increase');
        const messageElement = cartItem.querySelector('.quantity-message');
        
        const currentQuantity = parseInt(qtyElement.textContent);
        const productId = cartItem.dataset.productId;
        
        // Store current selection state
        const wasSelected = checkbox.checked;
        
        // Validate minimum quantity
        if (newQuantity < 1) {
            showQuantityMessage(messageElement, "Minimum quantity reached (1)", "warning");
            return;
        }
        
        // 🟢 Get real-time stock amount from server
        let stockAmount;
        try {
            const stockResponse = await fetch(`/cart/product-stock/${productId}`);
            const stockData = await stockResponse.json();
            
            if (stockData.success) {
                stockAmount = parseInt(stockData.stock_amount);
                // Update the displayed stock info
                const stockInfoElement = cartItem.querySelector('.stock-info, .stock-warning');
                if (stockInfoElement) {
                    if (newQuantity > stockAmount) {
                        stockInfoElement.innerHTML = `<div class="stock-warning">Only ${stockAmount} left in stock</div>`;
                    } else {
                        stockInfoElement.innerHTML = `<div class="stock-info">${stockAmount} available</div>`;
                    }
                }
            } else {
                // Fallback to dataset if API fails
                stockAmount = parseInt(cartItem.dataset.stock || 0);
            }
        } catch (error) {
            console.error('Error fetching stock:', error);
            stockAmount = parseInt(cartItem.dataset.stock || 0);
        }
        
        // Validate maximum quantity against REAL-TIME stock
        if (newQuantity > stockAmount) {
            showQuantityMessage(messageElement, `Maximum stock available: ${stockAmount}`, "error");
            return;
        }
        
        // Clear any previous messages
        hideQuantityMessage(messageElement);
        
        // 🟢 IMMEDIATE UI UPDATE
        qtyElement.textContent = newQuantity;
        
        // Update button states immediately
        decreaseBtn.disabled = newQuantity <= 1;
        increaseBtn.disabled = newQuantity >= stockAmount;
        
        // Show appropriate messages
        if (newQuantity === 1) {
            showQuantityMessage(messageElement, "Minimum quantity reached", "info");
        } else if (newQuantity === stockAmount) {
            showQuantityMessage(messageElement, "Maximum stock reached", "info");
        }
        
        // Add smooth transition class for visual feedback
        qtyElement.style.transition = 'all 0.2s ease';
        qtyElement.style.transform = 'scale(1.1)';
        
        // Reset animation
        setTimeout(() => {
            qtyElement.style.transform = 'scale(1)';
        }, 200);
        
        // Preserve checkbox selection state
        if (wasSelected) {
            checkbox.checked = true;
        }
        
        // Update totals immediately
        updateCartTotals(window.getCurrentCartContainer());
        
        // 🟢 DEBOUNCED DATABASE UPDATE
        if (quantityUpdateTimeout) {
            clearTimeout(quantityUpdateTimeout);
        }
        
        quantityUpdateTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/cart/update-quantity/${cartId}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ quantity: newQuantity })
                });

                const data = await response.json();
                if (!data.success) {
                    console.error('Failed to save quantity to database:', data.message);
                    // Revert to original quantity if save fails
                    qtyElement.textContent = currentQuantity;
                    decreaseBtn.disabled = currentQuantity <= 1;
                    increaseBtn.disabled = currentQuantity >= stockAmount;
                    window.notification.error('Failed to save quantity', 2000);
                }
            } catch (error) {
                console.error('Error saving quantity to database:', error);
                qtyElement.textContent = currentQuantity;
                decreaseBtn.disabled = currentQuantity <= 1;
                increaseBtn.disabled = currentQuantity >= stockAmount;
                window.notification.error('Error saving quantity', 2000);
            }
        }, DEBOUNCE_DELAY);
    }

    // Helper function to show quantity messages
    function showQuantityMessage(messageElement, text, type) {
        if (!messageElement) return;
        
        messageElement.textContent = text;
        messageElement.style.display = 'block';
        messageElement.style.color = type === 'error' ? '#dc2626' : type === 'warning' ? '#d97706' : '#059669';
        
        setTimeout(() => {
            hideQuantityMessage(messageElement);
        }, 3000);
    }

    // Helper function to hide quantity messages
    function hideQuantityMessage(messageElement) {
        if (messageElement) {
            messageElement.style.display = 'none';
        }
    }

    window.reserveSelectedItems = async function() {
        const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
        if (!container) return;

        const selectedItems = [];
        const itemCheckboxes = container.querySelectorAll(".item-checkbox:checked");
        
        itemCheckboxes.forEach(checkbox => {
            const cartItem = checkbox.closest('.cart-item');
            const cartId = cartItem.dataset.cartId;
            if (cartId) {
                selectedItems.push(parseInt(cartId));
            }
        });

        if (selectedItems.length === 0) {
            window.notification.warning("Please select at least one product to reserve.", 3000);
            return;
        }

        try {
            console.log("Reserving items:", selectedItems);
            
            const reserveResponse = await fetch('/cart/reserve', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    cart_ids: selectedItems,
                    _debug: true // Add debug flag
                })
            });

            console.log("Reservation response status:", reserveResponse.status);
            
            if (!reserveResponse.ok) {
                // Try to get more detailed error information
                let errorMessage = `Server error: ${reserveResponse.status} ${reserveResponse.statusText}`;
                try {
                    const errorData = await reserveResponse.json();
                    errorMessage = errorData.message || errorMessage;
                    console.error("Reservation error details:", errorData);
                } catch (e) {
                    console.error("Could not parse error response:", e);
                }
                throw new Error(errorMessage);
            }

            const reserveData = await reserveResponse.json();
            console.log("Reservation response data:", reserveData);
            
            if (reserveData.success) {
                const productText = selectedItems.length === 1 ? 'product' : 'products';
                window.notification.success(`${selectedItems.length} ${productText} reserved successfully!`, 4000);
                
                if (window.reloadCart) {
                    await window.reloadCart();
                }
                
                setTimeout(() => {
                    if (window.refreshStatusSection) {
                        window.refreshStatusSection();
                    }
                }, 1000);
                
            } else {
                console.error("Reservation failed:", reserveData);
                window.notification.error(reserveData.message || 'Failed to reserve products. Please try again.', 4000);
            }
        } catch (error) {
            console.error('Error reserving products:', error);
            window.notification.error(`Error: ${error.message}`, 5000);
        }
    }

    window.removeFromCart = async function(cartId) {
        try {
            const response = await fetch(`/cart/delete/${cartId}`, {
                method: 'DELETE'
            });

            const data = await response.json();
            if (data.success) {
                if (window.reloadCart) {
                    await window.reloadCart();
                }
                window.notification.success("Item removed from cart", 3000);
            } else {
                window.notification.error(data.message || "Failed to remove item", 3000);
            }
        } catch (error) {
            console.error('Error removing from cart:', error);
            window.notification.error('Error removing item. Please try again.', 4000);
        }
    }
}

// 🟢 GLOBAL cleanup function
window.cleanupQuantityUpdates = function() {
    if (quantityUpdateTimeout) {
        clearTimeout(quantityUpdateTimeout);
        quantityUpdateTimeout = null;
    }
};

// 🟢 GLOBAL function to reload cart without page refresh
window.reloadCart = async function() {
    const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
    if (container) {
        // Re-attach scripts to reload cart items
        attachCartScripts(container);
    }
};

// 🟢 Export functions for global access
window.attachCartScripts = attachCartScripts;

// 🟢 GLOBAL: Initialize void tab (add this near other tab initialization functions)
window.initializeVoidTab = async function(container) {
    const voidTab = container.querySelector('.status-tab[data-tab="void"]');
    if (!voidTab) return;
    
    // Load void counts
    await window.loadVoidCounts(container);
    
    // Set up click event
    voidTab.addEventListener("click", async () => {
        const tabs = container.querySelectorAll(".status-tab");
        tabs.forEach((t) => t.classList.remove("active"));
        voidTab.classList.add("active");
        
        await window.loadVoidRequests(container);
    });
};

// 🟢 GLOBAL: Load void counts
window.loadVoidCounts = async function(container) {
    try {
        const res = await fetch(`/void/count`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        if (data.success) {
            const counts = data.counts;
            const voidTab = container.querySelector(`.status-tab[data-tab="void"]`);
            if (voidTab) {
                const badge = voidTab.querySelector('.tab-count');
                if (badge) {
                    const totalCount = Object.values(counts).reduce((a, b) => a + b, 0);
                    badge.textContent = totalCount;
                    badge.style.display = totalCount > 0 ? 'inline-flex' : 'none';
                }
            }
            return counts;
        }
    } catch (err) {
        console.error("❌ Error loading void counts:", err);
        return { pending: 0, approved: 0, rejected: 0, refunded: 0 };
    }
};

// 🟢 GLOBAL: Load void requests
window.loadVoidRequests = async function(container, page = 1) {
    const dynamicContent = container.querySelector("#dynamicContent");
    if (!dynamicContent) return;
    
    try {
        dynamicContent.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:#666;">
                <div style="font-size:32px;margin-bottom:12px;">📋</div>
                <p>Loading void/return requests...</p>
            </div>
        `;
        
        const res = await fetch(`/void/user-requests`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        const data = await res.json();
        
        if (data.success) {
            const requests = data.requests || [];
            
            if (requests.length === 0) {
                dynamicContent.innerHTML = `
                <div class="empty-status">
                    <img src="https://cdn-icons-png.flaticon.com/512/4076/4076505.png" alt="No void requests">
                    <p>No void/return requests</p>
                    <small>Your void and return requests will appear here.</small>
                </div>`;
            } else {
                let requestsHTML = requests.map(req => {
                    // Determine status color
                    let statusColor = '#6b7280';
                    let statusBg = '#f3f4f6';
                    switch(req.void_status) {
                        case 'pending':
                            statusColor = '#d97706';
                            statusBg = '#fef3c7';
                            break;
                        case 'approved':
                            statusColor = '#059669';
                            statusBg = '#d1fae5';
                            break;
                        case 'rejected':
                            statusColor = '#dc2626';
                            statusBg = '#fee2e2';
                            break;
                        case 'refunded':
                            statusColor = '#2563eb';
                            statusBg = '#dbeafe';
                            break;
                    }
                    
                    return `
                    <div class="reservation-item" data-void-id="${req.void_id}">
                        <div style="position: relative;">
                            <img src="${req.product_image}" alt="${req.product_name}" 
                                style="width: 60px; height: 60px; border-radius: 8px; object-fit: cover; border: 2px solid #e5e7eb;">
                        </div>
                        <div style="flex: 1;">
                            <div style="font-weight: 600; color: #1f2937; margin-bottom: 8px; font-size: 14px;">
                                ${req.product_name}
                            </div>
                            <div style="font-size: 12px; color: #6b7280; margin-bottom: 8px;">
                                <div>Quantity: ${req.quantity}</div>
                                <div>Requested: ${req.requested_at_display}</div>
                                <div>Reason: ${req.return_type_display}</div>
                            </div>
                            
                            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                                <div class="status-badge" style="
                                    display: inline-block; 
                                    padding: 4px 12px; 
                                    border-radius: 20px; 
                                    font-size: 11px; 
                                    font-weight: 600;
                                    background: ${statusBg};
                                    color: ${statusColor};
                                ">
                                    ${req.status_display}
                                </div>
                                
                                ${req.void_status === 'pending' ? `
                                <button class="cancel-void-btn" data-void-id="${req.void_id}" 
                                    style="padding: 4px 12px; font-size: 11px; background: #f3f4f6; 
                                        border: 1px solid #d1d5db; border-radius: 6px; 
                                        color: #6b7280; cursor: pointer;">
                                    Cancel Request
                                </button>
                                ` : ''}
                            </div>
                            
                            ${req.reason ? `
                            <div style="font-size: 12px; color: #4b5563; margin-top: 8px; padding: 8px; 
                                        background: #f8fafc; border-radius: 6px; border-left: 3px solid #9ca3af;">
                                <strong>Reason:</strong> ${req.reason}
                            </div>
                            ` : ''}
                            
                            ${req.problem_description ? `
                            <div style="font-size: 12px; color: #4b5563; margin-top: 8px; padding: 8px; 
                                        background: #f8fafc; border-radius: 6px;">
                                <strong>Description:</strong> ${req.problem_description}
                            </div>
                            ` : ''}
                            
                            ${req.admin_notes ? `
                            <div style="font-size: 12px; color: #7c2d12; margin-top: 8px; padding: 8px; 
                                        background: #fffbeb; border-radius: 6px; border-left: 3px solid #f59e0b;">
                                <strong>ATBI Notes:</strong> ${req.admin_notes}
                            </div>
                            ` : ''}
                            
                            ${req.refund_amount ? `
                            <div style="font-size: 12px; color: #065f46; margin-top: 8px; padding: 8px; 
                                        background: #ecfdf5; border-radius: 6px; border-left: 3px solid #10b981;">
                                <strong>Refund:</strong> ₱${req.refund_amount.toLocaleString()} 
                                ${req.refund_method_display ? `via ${req.refund_method_display}` : ''}
                            </div>
                            ` : ''}
                        </div>
                    </div>
                    `;
                }).join("");
                
                dynamicContent.innerHTML = requestsHTML;
                
                // Attach cancel button events
                const cancelBtns = dynamicContent.querySelectorAll('.cancel-void-btn');
                cancelBtns.forEach(btn => {
                    btn.addEventListener('click', async (e) => {
                        const voidId = e.target.dataset.voidId;
                        await window.cancelVoidRequest(voidId);
                    });
                });
            }
        }
    } catch (err) {
        console.error("❌ Error loading void requests:", err);
        dynamicContent.innerHTML = `
            <div style="text-align:center;padding:40px 20px;color:#d32f2f;">
                <div style="font-size:32px;margin-bottom:12px;">⚠️</div>
                <p>Error loading void requests.</p>
            </div>`;
    }
};

// 🟢 GLOBAL: Cancel void request
window.cancelVoidRequest = async function(voidId) {
    const confirm = await window.showConfirmationDialog(
        "Cancel Void Request",
        "Are you sure you want to cancel this void request?",
        "warning"
    );
    
    if (!confirm) return;
    
    try {
        const response = await fetch(`/void/${voidId}/cancel`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const data = await response.json();
        
        if (data.success) {
            window.notification.success("Void request cancelled successfully", 3000);
            
            // Refresh the void requests list
            const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
            if (container) {
                await window.loadVoidCounts(container);
                await window.loadVoidRequests(container);
            }
        } else {
            window.notification.error(data.message || "Failed to cancel void request", 3000);
        }
    } catch (error) {
        console.error('Error cancelling void request:', error);
        window.notification.error('Error cancelling void request', 3000);
    }
};

// 🟢 GLOBAL: Request void modal (for completed items)
window.showVoidRequestModal = async function(reservationId, productName, quantity) {
    // Create modal HTML
    const modalHTML = `
    <div class="void-modal-overlay" style="
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.5); display: flex; align-items: center;
        justify-content: center; z-index: 10000; padding: 20px;">
        <div class="void-modal" style="
            background: white; border-radius: 16px; width: 100%;
            max-width: 500px; max-height: 90vh; overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);">
            
            <!-- Header -->
            <div style="padding: 20px; border-bottom: 1px solid #e5e7eb;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #1f2937; font-size: 18px; font-weight: 700;">
                        Request Return/Refund
                    </h3>
                    <button class="close-void-modal" style="
                        background: none; border: none; font-size: 24px;
                        cursor: pointer; color: #6b7280; padding: 4px;">
                        ×
                    </button>
                </div>
                <p style="margin: 8px 0 0; color: #6b7280; font-size: 14px;">
                    ${productName} (Quantity: ${quantity})
                </p>
            </div>
            
            <!-- Form -->
            <form id="voidRequestForm" style="padding: 20px;">
                <input type="hidden" name="reservation_id" value="${reservationId}">
                
                <!-- Reason -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                        Reason for Return *
                    </label>
                    <select name="return_type" required style="
                        width: 100%; padding: 10px; border: 1px solid #d1d5db;
                        border-radius: 8px; font-size: 14px; color: #1f2937;">
                        <option value="">Select a reason</option>
                        <option value="defective">Defective Product</option>
                        <option value="wrong_item">Wrong Item Received</option>
                        <option value="damaged">Damaged During Delivery</option>
                        <option value="not_as_described">Not as Described</option>
                        <option value="other">Other Reason</option>
                    </select>
                </div>
                
                <!-- Detailed Reason -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                        Detailed Explanation *
                    </label>
                    <textarea name="reason" required placeholder="Please explain why you want to return this product..." 
                        style="width: 100%; padding: 10px; border: 1px solid #d1d5db;
                               border-radius: 8px; font-size: 14px; color: #1f2937;
                               min-height: 100px; resize: vertical;"></textarea>
                </div>
                
                <!-- Problem Description -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                        Problem Description (Optional)
                    </label>
                    <textarea name="problem_description" placeholder="Describe the issue in detail..." 
                        style="width: 100%; padding: 10px; border: 1px solid #d1d5db;
                               border-radius: 8px; font-size: 14px; color: #1f2937;
                               min-height: 80px; resize: vertical;"></textarea>
                </div>
                
                <!-- Image Upload -->
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; font-weight: 600; color: #374151;">
                        Upload Image (Optional)
                        <span style="font-size: 12px; color: #9ca3af; font-weight: normal;">
                            Upload a photo showing the problem (max 5MB)
                        </span>
                    </label>
                    <input type="file" name="void_image" accept="image/*"
                        style="width: 100%; padding: 10px; border: 2px dashed #d1d5db;
                               border-radius: 8px; font-size: 14px;">
                    <div style="font-size: 12px; color: #6b7280; margin-top: 4px;">
                        Supported formats: PNG, JPG, JPEG, GIF, WEBP
                    </div>
                </div>
                
                <!-- Notice -->
                <div style="margin-bottom: 20px; padding: 12px; background: #fffbeb;
                            border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <div style="display: flex; gap: 8px; align-items: flex-start;">
                        <div style="font-size: 16px;">⚠️</div>
                        <div>
                            <div style="font-weight: 600; color: #92400e; margin-bottom: 4px;">
                                Important Notice
                            </div>
                            <div style="font-size: 13px; color: #92400e;">
                                • Refunds may take 3-7 business days to process.<br>
                                • Keep the item in its original condition.<br>
                                • Admin may contact you for additional information.
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Buttons -->
                <div style="display: flex; gap: 12px;">
                    <button type="button" class="cancel-void-btn" style="
                        flex: 1; padding: 12px; border: 1px solid #d1d5db;
                        border-radius: 8px; background: white; color: #4b5563;
                        font-weight: 600; cursor: pointer; font-size: 14px;">
                        Cancel
                    </button>
                    <button type="submit" class="submit-void-btn" style="
                        flex: 1; padding: 12px; border: none;
                        border-radius: 8px; background: linear-gradient(135deg, #ef4444, #dc2626);
                        color: white; font-weight: 700; cursor: pointer;
                        font-size: 14px; transition: all 0.3s;">
                        Submit Request
                    </button>
                </div>
            </form>
        </div>
    </div>
    `;
    
    // Add modal to body
    const modalContainer = document.createElement('div');
    modalContainer.innerHTML = modalHTML;
    document.body.appendChild(modalContainer);
    
    const modal = modalContainer.querySelector('.void-modal-overlay');
    
    // Show modal with animation
    setTimeout(() => {
        modal.style.opacity = '1';
        modal.querySelector('.void-modal').style.transform = 'scale(1)';
    }, 10);
    
    // Close handlers
    const closeModal = () => {
        modal.style.opacity = '0';
        modal.querySelector('.void-modal').style.transform = 'scale(0.9)';
        setTimeout(() => {
            modal.remove();
        }, 300);
    };
    
    modal.querySelector('.close-void-modal').addEventListener('click', closeModal);
    modal.querySelector('.cancel-void-btn').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    
    // Form submission
    modal.querySelector('#voidRequestForm').addEventListener('submit', async (e) => {
        e.preventDefault();
        const form = e.target;
        const submitBtn = form.querySelector('.submit-void-btn');
        const originalText = submitBtn.textContent;
        
        submitBtn.textContent = 'Submitting...';
        submitBtn.disabled = true;
        
        try {
            const formData = new FormData(form);
            
            const response = await fetch('/void/request', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.success) {
                window.notification.success("Void request submitted successfully!", 4000);
                closeModal();
                
                // Refresh status section
                if (window.refreshStatusSection) {
                    await window.refreshStatusSection();
                }
            } else {
                window.notification.error(data.message || "Failed to submit request", 4000);
                submitBtn.textContent = originalText;
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error('Error submitting void request:', error);
            window.notification.error('Error submitting request', 4000);
            submitBtn.textContent = originalText;
            submitBtn.disabled = false;
        }
    });
};

// Helper function for confirmation dialog
window.showConfirmationDialog = function(title, message, type = 'warning') {
    return new Promise((resolve) => {
        const dialogHTML = `
        <div class="confirm-dialog-overlay" style="
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0,0,0,0.5); display: flex; align-items: center;
            justify-content: center; z-index: 10001;">
            <div class="confirm-dialog" style="
                background: white; border-radius: 16px; padding: 24px;
                max-width: 400px; width: 90%; box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                transform: scale(0.9); transition: transform 0.3s;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <div style="font-size: 40px; margin-bottom: 12px;">
                        ${type === 'warning' ? '⚠️' : type === 'error' ? '❌' : '✅'}
                    </div>
                    <h3 style="margin: 0 0 8px; color: #1f2937; font-size: 18px;">
                        ${title}
                    </h3>
                    <p style="margin: 0; color: #6b7280; font-size: 14px; line-height: 1.5;">
                        ${message}
                    </p>
                </div>
                <div style="display: flex; gap: 12px;">
                    <button class="confirm-no" style="
                        flex: 1; padding: 12px; border: 1px solid #d1d5db;
                        border-radius: 8px; background: white; color: #4b5563;
                        font-weight: 600; cursor: pointer;">
                        No
                    </button>
                    <button class="confirm-yes" style="
                        flex: 1; padding: 12px; border: none;
                        border-radius: 8px; background: linear-gradient(135deg, #ef4444, #dc2626);
                        color: white; font-weight: 700; cursor: pointer;">
                        Yes
                    </button>
                </div>
            </div>
        </div>
        `;
        
        const dialogContainer = document.createElement('div');
        dialogContainer.innerHTML = dialogHTML;
        document.body.appendChild(dialogContainer);
        
        const dialog = dialogContainer.querySelector('.confirm-dialog-overlay');
        const dialogContent = dialogContainer.querySelector('.confirm-dialog');
        
        setTimeout(() => {
            dialog.style.opacity = '1';
            dialogContent.style.transform = 'scale(1)';
        }, 10);
        
        const closeDialog = (confirmed) => {
            dialog.style.opacity = '0';
            dialogContent.style.transform = 'scale(0.9)';
            setTimeout(() => {
                dialog.remove();
                resolve(confirmed);
            }, 300);
        };
        
        dialogContainer.querySelector('.confirm-no').addEventListener('click', () => closeDialog(false));
        dialogContainer.querySelector('.confirm-yes').addEventListener('click', () => closeDialog(true));
        
        dialog.addEventListener('click', (e) => {
            if (e.target === dialog) closeDialog(false);
        });
    });
};