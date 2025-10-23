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
      }
    });
  }

  // ⎋ ESC to close
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && cartModal) {
      cartModal.classList.remove("active");
    }
  });
});

// ======================
// Internal cart scripts - UPDATED WITH RESERVATION SUPPORT
// ======================
function attachCartScripts(container) {
  if (!container) return;

  // IMMEDIATELY LOAD CART ITEMS WHEN CART OPENS
  loadCartItems(container);

  const cartItemsContainer = container.querySelector("#cartItems");
  const totalElem = container.querySelector("#totalAmount");

  //Status Tabs - Load reservation counts and set up click events
  initializeStatusTabs(container);

  // FIXED: Load cart items function
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

      //RENDER THE ACTUAL CART ITEMS
      renderCartItems(items, container);
      
    } catch (err) {
      console.error("❌ Error loading cart:", err);
      cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">Server error while loading cart.</p>`;
    }
  }

  //UPDATED: Initialize status tabs with auto-loading
  async function initializeStatusTabs(container) {
    const tabs = container.querySelectorAll(".status-tab");
    
    // 🟢 FIX: Ensure user ID is available before loading counts
    let userId = getUserId();
    if (!userId) {
      userId = await fetchUserInfo();
    }
    
    // Load reservation counts and auto-show pending tab
    await loadReservationCounts(container);
    
    //AUTO-SHOW PENDING TAB IF THERE ARE PENDING RESERVATIONS
    const pendingCount = parseInt(container.querySelector('.status-tab[data-tab="pending"] .tab-count').textContent) || 0;
    if (pendingCount > 0) {
      // Switch to pending tab automatically
      tabs.forEach(t => t.classList.remove("active"));
      const pendingTab = container.querySelector('.status-tab[data-tab="pending"]');
      pendingTab.classList.add("active");
      await loadReservationsByStatus("pending", container);
    }
    
    tabs.forEach((tab) => {
      tab.addEventListener("click", async () => {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const tabName = tab.dataset.tab;
        
        if (tabName === "cart") {
          loadCartItems(container);
        } else {
          await loadReservationsByStatus(tabName, container);
        }
      });
    });
  }

  //NEW: Load reservation counts for all status tabs
  async function loadReservationCounts(container) {
    try {
      const userId = getUserId();
      if (!userId) {
        console.error("User ID not found");
        return;
      }
      
      const res = await fetch("/reservations/user/" + userId);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.success) {
        const reservations = data.reservations || [];
        
        // Count reservations by status
        const counts = {
          pending: 0,
          approved: 0,
          completed: 0,
          rejected: 0
        };
        
        reservations.forEach(reservation => {
          if (counts.hasOwnProperty(reservation.status)) {
            counts[reservation.status]++;
          }
        });
        
        // Update tab counts
        Object.keys(counts).forEach(status => {
          const badge = container.querySelector(`.status-tab[data-tab="${status}"] .tab-count`);
          if (badge) {
            badge.textContent = counts[status];
          }
        });
        
        return counts; // Return counts for auto-display logic
      }
    } catch (err) {
      console.error("❌ Error loading reservation counts:", err);
      return { pending: 0, approved: 0, completed: 0, rejected: 0 };
    }
  }

  async function loadReservationsByStatus(status, container) {
      const dynamicContent = container.querySelector("#dynamicContent");
      if (!dynamicContent) return;

      try {
          dynamicContent.innerHTML = `
              <div style="text-align:center;padding:60px 20px;color:#666;">
                  <div style="font-size:48px;margin-bottom:16px;">⏳</div>
                  <p>Loading ${status} reservations...</p>
              </div>
          `;

          const res = await fetch(`/reservations/status/${status}`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);

          const data = await res.json();
          
          if (data.success) {
              const reservations = data.reservations || [];
              
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
                  dynamicContent.innerHTML = reservations.map(reservation => {
                      // Clean up image path
                      let imagePath = reservation.image_path;
                      if (imagePath && imagePath.includes('static/uploads/static/uploads/')) {
                          imagePath = imagePath.replace('static/uploads/static/uploads/', 'static/uploads/');
                      }
                      
                      // FIXED: Using Intl.DateTimeFormat with Asia/Manila timezone
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
                      
                      return `
                      <div class="reservation-item">
                          <img src="${imagePath}" alt="${reservation.product_name}" 
                              onerror="this.onerror=null; this.src='https://cdn-icons-png.flaticon.com/512/4076/4076505.png'">
                          <div class="reservation-info">
                              <div class="reservation-name">${reservation.product_name}</div>
                              <div class="reservation-price">₱${reservation.price_per_stocks.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                              
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
              }
          } else {
              dynamicContent.innerHTML = `
                  <div style="text-align:center;padding:60px 20px;color:#d32f2f;">
                      <div style="font-size:48px;margin-bottom:16px;">❌</div>
                      <p>${data.message || "Failed to load reservations."}</p>
                  </div>`;
          }
      } catch (err) {
          console.error(`❌ Error loading ${status} reservations:`, err);
          dynamicContent.innerHTML = `
              <div style="text-align:center;padding:60px 20px;color:#d32f2f;">
                  <div style="font-size:48px;margin-bottom:16px;">⚠️</div>
                  <p>Server error while loading ${status} reservations.</p>
              </div>`;
      }
  }
  window.refreshStatusSection = async function() {
    const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
    if (!container) return;
    
    // Reload counts and auto-show pending tab
    const counts = await loadReservationCounts(container);
    
    if (counts && counts.pending > 0) {
      // Switch to pending tab and show pending reservations
      const tabs = container.querySelectorAll(".status-tab");
      tabs.forEach(t => t.classList.remove("active"));
      const pendingTab = container.querySelector('.status-tab[data-tab="pending"]');
      pendingTab.classList.add("active");
      await loadReservationsByStatus("pending", container);
    }
  };

  //IMPROVED: Helper function to get user ID from multiple sources
  function getUserId() {
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
  //NEW: Fetch user info from server
  async function fetchUserInfo() {
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

  //Render cart items function with checkboxes
  function renderCartItems(items, container) {
      const cartItemsContainer = container.querySelector("#cartItems");
      const cartCountElem = container.querySelector("#cartCount");
      const totalElem = container.querySelector("#totalAmount");
      const selectAllCheckbox = container.querySelector("#selectAll");

      if (!cartItemsContainer) return;

      cartItemsContainer.innerHTML = items.map(item => {
          const imgSrc = item.image_path;
          const price = parseFloat(item.price_per_stocks || 0);

          return `
          <div class="cart-item" data-cart-id="${item.cart_id}">
              <input type="checkbox" class="item-checkbox" onchange="updateCartTotals(window.getCurrentCartContainer())">
              <img src="${imgSrc}" alt="${item.name}" 
                  onerror="this.onerror=null; this.src='/static/images/no-image.png'">
              <div class="item-info">
                  <div class="item-name">${item.name}</div>
                  <div class="item-price">₱${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
                  ${item.stock_amount < item.quantity ? 
                    `<div class="stock-info">Only ${item.stock_amount} left in stock</div>` : 
                    ''
                  }
                  <div class="quantity">
                      <button class="qty-btn decrease" onclick="updateQuantity(${item.cart_id}, ${item.quantity - 1})">-</button>
                      <span class="qty">${item.quantity}</span>
                      <button class="qty-btn increase" onclick="updateQuantity(${item.cart_id}, ${item.quantity + 1})">+</button>
                  </div>
              </div>
              <button class="delete-btn" onclick="removeFromCart(${item.cart_id})" 
                      style="background:none;border:none;color:#dc2626;cursor:pointer;padding:5px;font-size:16px;">🗑️</button>
          </div>`;
      }).join("");

      // Initialize select all functionality
      initializeSelectAll(container);
      
      // Update counts and totals (will show 0 since nothing is selected)
      updateCartTotals(container, items);
  }

  // 🟢 Add helper function to get current cart container
  window.getCurrentCartContainer = function() {
      return document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
  }

  //Initialize Select All functionality
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

  //Update cart totals based on selected items
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
      let selectedProducts = 0; // Count of selected products
      let totalProducts = 0; // Total number of products in cart
      let selectedItemsCount = 0; // Total quantity of selected items

      // Get all cart items
      const cartItems = cartItemsContainer.querySelectorAll(".cart-item");
      
      cartItems.forEach(item => {
          const checkbox = item.querySelector(".item-checkbox");
          const priceElem = item.querySelector(".item-price");
          const qtyElem = item.querySelector(".qty");
          
          if (priceElem && qtyElem) {
              const price = parseFloat(priceElem.textContent.replace(/[^\d.]/g, "")) || 0;
              const qty = parseInt(qtyElem.textContent) || 0;
              totalProducts++; // Count each product
              
              if (checkbox.checked) {
                  total += price * qty;
                  selectedProducts++; // Count selected products
                  selectedItemsCount += qty; // Count total selected items quantity
              }
          }
      });

      // Update total display
      totalElem.textContent = `Total: ₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
      
      // Update cart count (show selected products/total products)
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
          const reserveResponse = await fetch('/cart/reserve', {
              method: 'POST',
              headers: {
                  'Content-Type': 'application/json',
              },
              body: JSON.stringify({ cart_ids: selectedItems })
          });

          const reserveData = await reserveResponse.json();
          if (reserveData.success) {
              // Show success notification
              const productText = selectedItems.length === 1 ? 'product' : 'products';
              window.notification.success(`${selectedItems.length} ${productText} reserved successfully!`, 4000);
              
              // Reload cart to show updated state
              if (window.loadCartItems && container) {
                  window.loadCartItems(container);
              }
              
              // Refresh status section to show pending reservations
              setTimeout(() => {
                  if (window.refreshStatusSection) {
                      window.refreshStatusSection();
                  }
              }, 1000);
              
          } else {
              window.notification.error(reserveData.message || 'Failed to reserve products', 4000);
          }
      } catch (error) {
          console.error('Error reserving products:', error);
          window.notification.error('Error reserving products. Please try again.', 4000);
      }
  }
  // Modern confirmation dialog for cancel reservation
  window.cancelReservation = async function(reservationId, productName = 'this product') {
      return new Promise((resolve) => {
          // Create dialog overlay
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
                      <button class="confirm-btn no" onclick="closeConfirmDialog(false)">Keep Reserved</button>
                      <button class="confirm-btn yes" onclick="closeConfirmDialog(true)">Yes, Cancel</button>
                  </div>
              </div>
          `;

          document.body.appendChild(dialogOverlay);

          // Show with animation
          setTimeout(() => {
              dialogOverlay.classList.add('show');
              dialogOverlay.querySelector('.confirm-dialog').classList.add('show');
          }, 10);

          // Close dialog function
          window.closeConfirmDialog = async (confirmed) => {
              dialogOverlay.classList.remove('show');
              dialogOverlay.querySelector('.confirm-dialog').classList.remove('show');
              
              setTimeout(() => {
                  if (dialogOverlay.parentElement) {
                      dialogOverlay.remove();
                  }
              }, 300);

              if (confirmed) {
                  // Proceed with cancellation
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
                          
                          // Refresh the pending reservations view
                          const container = document.querySelector('.cart-sidebar') || document.querySelector('#cartContent');
                          if (container) {
                              await loadReservationsByStatus("pending", container);
                              await loadReservationCounts(container);
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

          // Close on overlay click
          dialogOverlay.addEventListener('click', (e) => {
              if (e.target === dialogOverlay) {
                  window.closeConfirmDialog(false);
              }
          });

          // Close on ESC key
          const escHandler = (e) => {
              if (e.key === 'Escape') {
                  window.closeConfirmDialog(false);
                  document.removeEventListener('keydown', escHandler);
              }
          };
          document.addEventListener('keydown', escHandler);
      });
  }
  //Add these global functions for the buttons to work
  window.updateQuantity = async function(cartId, newQuantity) {
    if (newQuantity < 1) {
      await removeFromCart(cartId);
      return;
    }

    try {
      const response = await fetch(`/cart/update-quantity/${cartId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ quantity: newQuantity })
      });

      const data = await response.json();
      if (data.success) {
        loadCartItems(container); // Reload cart
      }
    } catch (error) {
      console.error('Error updating quantity:', error);
      window.notification.error('Error updating quantity. Please try again.', 4000);
    }
  }

  window.removeFromCart = async function(cartId) {
    try {
      const response = await fetch(`/cart/delete/${cartId}`, {
        method: 'DELETE'
      });

      const data = await response.json();
      if (data.success) {
        loadCartItems(container); // Reload cart
      }
    } catch (error) {
      console.error('Error removing from cart:', error);
      window.notification.error('Error removing item. Please try again.', 4000);
    }
  }
}
async function loadCartItems(container) {
  const cartItemsContainer = container.querySelector("#cartItems");
  const cartCountElem = container.querySelector("#cartCount");
  const totalElem = container.querySelector("#totalAmount");

  try {
    const res = await fetch("/cart/get-items");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    const data = await res.json();
    if (!data.success) {
      cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">${data.message || "Failed to load cart."}</p>`;
      cartCountElem.textContent = "0 items";
      totalElem.textContent = "Total: ₱0.00";
      return;
    }

    const items = data.items || [];
    if (items.length === 0) {
      cartItemsContainer.innerHTML = `<p style="text-align:center;color:#999;">Your cart is empty 🛒</p>`;
      cartCountElem.textContent = "0 items";
      totalElem.textContent = "Total: ₱0.00";
      return;
    }

    cartItemsContainer.innerHTML = items.map(item => {
      const img = item.image_path;
      const qty = item.quantity;
      const price = parseFloat(item.price_per_stocks || 0);

      return `
        <div class="cart-item" data-cart-id="${item.cart_id}" data-price="${price}">
          <input type="checkbox" class="item-checkbox">
          <img src="${img}" alt="${item.name}">
          <div class="item-info">
            <div class="item-name">${item.name}</div>
            <div class="item-price">₱${price.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
            <div class="stock-info">${item.stock_amount ? `${item.stock_amount} left` : ""}</div>
            <div class="quantity">
              <button class="decrease">−</button>
              <span class="qty">${qty}</span>
              <button class="increase">+</button>
            </div>
          </div>
        </div>`;
    }).join("");

    attachDynamicCartEvents(container);
    recalcTotals(container);

  } catch (err) {
    console.error("❌ Error loading cart:", err);
    window.notification.error('Error loading cart. Please try again.', 4000);
    cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">Server error while loading cart.</p>`;
  }
}

function attachDynamicCartEvents(container) {
  const selectAll = container.querySelector("#selectAll");
  const itemCheckboxes = container.querySelectorAll(".item-checkbox");
  const totalElem = container.querySelector("#totalAmount");
  const cartCountElem = container.querySelector("#cartCount");

  // 🟩 Handle Select All toggle
  selectAll?.addEventListener("change", e => {
    itemCheckboxes.forEach(cb => cb.checked = e.target.checked);
    recalcTotals(container);
  });

  // 🟩 Handle individual checkbox change
  itemCheckboxes.forEach(cb => {
    cb.addEventListener("change", () => {
      const allChecked = Array.from(itemCheckboxes).every(c => c.checked);
      selectAll.checked = allChecked;
      recalcTotals(container);
    });
  });

  // 🟩 Handle quantity change (increase/decrease)
  container.querySelectorAll(".cart-item").forEach(item => {
    const decreaseBtn = item.querySelector(".decrease");
    const increaseBtn = item.querySelector(".increase");
    const qtyElem = item.querySelector(".qty");

    decreaseBtn.addEventListener("click", async () => {
      let qty = parseInt(qtyElem.textContent);
      if (qty > 1) {
        qty--;
        qtyElem.textContent = qty;
        await updateCartQuantity(item.dataset.cartId, qty);
        recalcTotals(container);
      }
    });

    increaseBtn.addEventListener("click", async () => {
      let qty = parseInt(qtyElem.textContent);
      qty++;
      qtyElem.textContent = qty;
      await updateCartQuantity(item.dataset.cartId, qty);
      recalcTotals(container);
    });
  });
}

//Recalculate total dynamically
function recalcTotals(container) {
  const items = container.querySelectorAll(".cart-item");
  const totalElem = container.querySelector("#totalAmount");
  const cartCountElem = container.querySelector("#cartCount");
  let total = 0;
  let totalQty = 0;

  items.forEach(item => {
    const checkbox = item.querySelector(".item-checkbox");
    const qty = parseInt(item.querySelector(".qty").textContent);
    const price = parseFloat(item.dataset.price);

    if (checkbox.checked || !checkbox) {
      total += price * qty;
      totalQty += qty;
    }
  });

  cartCountElem.textContent = `${totalQty} item${totalQty > 1 ? "s" : ""}`;
  totalElem.textContent = `Total: ₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
}

//Optional: update quantity in backend (if you want real persistence)
async function updateCartQuantity(cartId, qty) {
  try {
    const res = await fetch(`/cart/update-quantity/${cartId}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ quantity: qty }),
    });
    const data = await res.json();
    if (!data.success) console.warn("Failed to update quantity:", data.message);
  } catch (err) {
    console.error("Error updating quantity:", err);
    window.notification.error('Error updating quantity. Please try again.', 4000);
  }
}

//Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  const cartSidebar = document.getElementById("cartSidebar");
  if (cartSidebar) loadCartItems(cartSidebar);
});

// ======================
// 🎛 Attach Dynamic Events (Qty + Select All)
// ======================
function attachDynamicCartEvents(container) {
  const cartItemsContainer = container.querySelector("#cartItems");
  const totalElem = container.querySelector("#totalAmount");
  const selectAll = container.querySelector("#selectAll");

  // Quantity increase/decrease
  cartItemsContainer.querySelectorAll(".increase").forEach(btn => {
    btn.addEventListener("click", () => {
      const qtyElem = btn.previousElementSibling;
      qtyElem.textContent = parseInt(qtyElem.textContent) + 1;
      updateDynamicTotal(container);
    });
  });

  cartItemsContainer.querySelectorAll(".decrease").forEach(btn => {
    btn.addEventListener("click", () => {
      const qtyElem = btn.nextElementSibling;
      const current = parseInt(qtyElem.textContent);
      if (current > 1) qtyElem.textContent = current - 1;
      updateDynamicTotal(container);
    });
  });

  // Select All
  if (selectAll) {
    selectAll.addEventListener("change", () => {
      const checked = selectAll.checked;
      container.querySelectorAll(".item-checkbox").forEach(box => (box.checked = checked));
    });
  }

  // Update total dynamically
  function updateDynamicTotal(container) {
    let total = 0;
    container.querySelectorAll(".cart-item").forEach(item => {
      const priceElem = item.querySelector(".item-price");
      const qtyElem = item.querySelector(".qty");
      if (priceElem && qtyElem) {
        const price = parseFloat(priceElem.textContent.replace(/[^\d.]/g, "")) || 0;
        const qty = parseInt(qtyElem.textContent) || 0;
        total += price * qty;
      }
    });
    totalElem.textContent = `Total: ₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
  }
}

