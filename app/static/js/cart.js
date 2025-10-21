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
// Internal cart scripts
// ======================
function attachCartScripts(container) {
  if (!container) return;

  const cartItemsContainer = container.querySelector("#cartItems");
  const totalElem = container.querySelector("#totalAmount");

  // 🟩 Load default tab ("cart")
  const cartTab = container.querySelector('.status-tab[data-tab="cart"]');
  if (cartTab) {
    cartTab.classList.add("active");
    loadTabContent("cart");
  }

  // 🟨 Status Tabs
  const tabs = container.querySelectorAll(".status-tab");
  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      tabs.forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const tabName = tab.dataset.tab;
      loadTabContent(tabName);
    });
  });

  // ======================
  // Load Tab Data (Cart or Reservation)
  // ======================
  async function loadTabContent(tabName) {
    const statusContent = container.querySelector("#statusContent");

    if (tabName === "cart") {
      // Load cart items
      try {
        const res = await fetch("/cart/get-items");
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);

        const contentType = res.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
          const text = await res.text();
          console.warn("⚠️ Received HTML instead of JSON:\n", text.substring(0, 200));
          cartItemsContainer.innerHTML = `
            <p style="color:red;text-align:center;">
              Session expired. Please <a href="/login">log in again</a>.
            </p>`;
          return;
        }

        const data = await res.json();
        if (data.success) {
          renderTabItems(data.items || []);
          updateTabCount("cart", data.items?.length || 0);
        } else {
          cartItemsContainer.innerHTML = `<p style="color:red;">${data.message || "Failed to load cart."}</p>`;
        }
      } catch (err) {
        console.error("Error loading cart:", err);
        cartItemsContainer.innerHTML = `<p style="color:red;">Server error while loading cart.</p>`;
      }
    } else {
      // Load reservation statuses
      if (!statusContent) return;
      statusContent.innerHTML = `<p style="text-align:center;">Loading ${tabName}...</p>`;

      try {
        const res = await fetch(`/reservations/status/${tabName}`);
        const contentType = res.headers.get("content-type") || "";

        if (!contentType.includes("application/json")) {
          const text = await res.text();
          console.warn("⚠️ Received HTML instead of JSON:\n", text.substring(0, 200));
          statusContent.innerHTML = `
            <p style="color:red;text-align:center;">
              Session expired. Please <a href="/login">log in again</a>.
            </p>`;
          return;
        }

        const data = await res.json();
        if (data.success) {
          const reservations = data.reservations || [];
          if (!reservations.length) {
            statusContent.innerHTML = `
              <div class="empty-status">
                <img src="https://cdn-icons-png.flaticon.com/512/4076/4076505.png" alt="Empty">
                <p>🕓 No ${tabName} reservations yet.</p>
              </div>`;
          } else {
            statusContent.innerHTML = reservations.map(r => `
              <div class="cart-item">
                <img src="/${r.image_path || 'static/images/no-image.png'}" alt="${r.product_name}">
                <div class="item-info">
                  <div class="item-name">${r.product_name}</div>
                  <div class="item-price">₱${r.price_per_stocks.toLocaleString()}</div>
                  <div class="status-badge status-${tabName}">${tabName.toUpperCase()}</div>
                </div>
              </div>
            `).join("");
          }
          updateTabCount(tabName, reservations.length);
        } else {
          statusContent.innerHTML = `<p style="color:red;">${data.message || "Failed to load reservations."}</p>`;
        }
      } catch (err) {
        console.error("Error loading reservations:", err);
        statusContent.innerHTML = `<p style="color:red;">Server error while loading ${tabName}.</p>`;
      }
    }
  }

  // ======================
  // Render Cart Items
  // ======================
  function renderTabItems(items) {
    if (!items.length) {
      cartItemsContainer.innerHTML = `<p style="text-align:center;color:#999;">No items found.</p>`;
      updateTotal();
      return;
    }

    cartItemsContainer.innerHTML = items.map((item) => {
      const img = item.image_path ? `/${item.image_path}` : "/static/images/no-image.png";
      const qty = item.quantity || 1;
      const price = parseFloat(item.price_per_stocks || item.price || 0);

      return `
        <div class="cart-item">
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
        </div>
      `;
    }).join("");

    attachQuantityEvents();
    updateTotal();
  }

  // ======================
  // Quantity + Total
  // ======================
  function attachQuantityEvents() {
    container.querySelectorAll(".increase").forEach((btn) => {
      btn.addEventListener("click", () => {
        const qty = btn.previousElementSibling;
        qty.textContent = parseInt(qty.textContent) + 1;
        updateTotal();
      });
    });

    container.querySelectorAll(".decrease").forEach((btn) => {
      btn.addEventListener("click", () => {
        const qty = btn.nextElementSibling;
        const current = parseInt(qty.textContent);
        if (current > 1) qty.textContent = current - 1;
        updateTotal();
      });
    });
  }

  function updateTotal() {
    if (!totalElem) return;
    let total = 0;

    container.querySelectorAll(".cart-item").forEach((item) => {
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

  function updateTabCount(tabName, count) {
    const badge = container.querySelector(`.status-tab[data-tab="${tabName}"] .tab-count`);
    if (badge) badge.textContent = count;
  }
}
