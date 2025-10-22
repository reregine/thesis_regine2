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
// Internal cart scripts - FIXED VERSION
// ======================
function attachCartScripts(container) {
  if (!container) return;

  // 🟢 IMMEDIATELY LOAD CART ITEMS WHEN CART OPENS
  loadCartItems(container);

  const cartItemsContainer = container.querySelector("#cartItems");
  const totalElem = container.querySelector("#totalAmount");

  // 🟨 Status Tabs
  const tabs = container.querySelectorAll(".status-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const tabName = tab.dataset.tab;
      if (tabName === "cart") {
        loadCartItems(container); // Reload cart items when cart tab is clicked
      } else {
        loadTabContent(tabName);
      }
    });
  });

  // 🟢 FIXED: Load cart items function
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

      // 🟢 RENDER THE ACTUAL CART ITEMS
      renderCartItems(items, container);
      
    } catch (err) {
      console.error("❌ Error loading cart:", err);
      cartItemsContainer.innerHTML = `<p style="color:red;text-align:center;">Server error while loading cart.</p>`;
    }
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
      let selectedCount = 0;
      let totalItems = 0;

      // Get all cart items
      const cartItems = cartItemsContainer.querySelectorAll(".cart-item");
      
      cartItems.forEach(item => {
          const checkbox = item.querySelector(".item-checkbox");
          const priceElem = item.querySelector(".item-price");
          const qtyElem = item.querySelector(".qty");
          
          if (priceElem && qtyElem) {
              const price = parseFloat(priceElem.textContent.replace(/[^\d.]/g, "")) || 0;
              const qty = parseInt(qtyElem.textContent) || 0;
              totalItems += qty;
              
              if (checkbox.checked) {
                  total += price * qty;
                  selectedCount += qty;
              }
          }
      });

      // Update total display
      totalElem.textContent = `Total: ₱${total.toLocaleString(undefined, { minimumFractionDigits: 2 })}`;
      
      // Update cart count (show selected/total)
      if (cartCountElem) {
          if (selectedCount > 0) {
              cartCountElem.textContent = `${selectedCount} of ${totalItems} items selected`;
          } else {
              cartCountElem.textContent = `${totalItems} items`;
          }
      }

      // Update reserve button text
      if (reserveBtn) {
          if (selectedCount > 0) {
              reserveBtn.textContent = `Reserve Selected (${selectedCount} items)`;
              reserveBtn.disabled = false;
              reserveBtn.style.background = 'var(--green)';
              reserveBtn.style.cursor = 'pointer';
          } else {
              reserveBtn.textContent = "Select items to reserve";
              reserveBtn.disabled = true;
              reserveBtn.style.background = '#9ca3af';
              reserveBtn.style.cursor = 'not-allowed';
          }
      }
  }

// 🟢 Update the reserve function to only reserve selected items
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
        alert("Please select at least one item to reserve.");
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
            alert('Selected items reserved successfully!');
            // Reload cart to show updated state
            if (window.loadCartItems && container) {
                window.loadCartItems(container);
            }
        } else {
            alert(reserveData.message || 'Failed to reserve items');
        }
    } catch (error) {
        console.error('Error reserving items:', error);
        alert('Error reserving items');
    }
}

  // 🟢 Add these global functions for the buttons to work
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

// 🧮 Recalculate total dynamically
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

// 🔄 Optional: update quantity in backend (if you want real persistence)
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
  }
}

// 🏁 Initialize on page load
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

