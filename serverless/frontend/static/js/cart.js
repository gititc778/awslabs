/* ShopWave cart — client-side, persisted in localStorage. */
(function () {
  const KEY = "shopwave_cart";
  const SHIPPING_FREE_OVER = 75;
  const SHIPPING_COST = 4.99;

  const money = (n) => "£" + Number(n).toFixed(2);

  function read() {
    try {
      return JSON.parse(localStorage.getItem(KEY)) || [];
    } catch (e) {
      return [];
    }
  }
  function write(items) {
    try {
      localStorage.setItem(KEY, JSON.stringify(items));
    } catch (e) {}
    updateCount();
  }

  function add(item) {
    const items = read();
    const existing = items.find((i) => String(i.id) === String(item.id));
    if (existing) {
      existing.quantity += item.quantity;
    } else {
      items.push(item);
    }
    write(items);
    toast(`Added ${item.name} to cart`);
  }
  function setQty(id, qty) {
    let items = read();
    if (qty <= 0) {
      items = items.filter((i) => String(i.id) !== String(id));
    } else {
      const it = items.find((i) => String(i.id) === String(id));
      if (it) it.quantity = qty;
    }
    write(items);
    renderCart();
  }
  function remove(id) {
    write(read().filter((i) => String(i.id) !== String(id)));
    renderCart();
  }
  function clear() {
    write([]);
    renderCart();
  }

  function totals(items) {
    const subtotal = items.reduce((s, i) => s + i.price * i.quantity, 0);
    const shipping = subtotal === 0 || subtotal >= SHIPPING_FREE_OVER ? 0 : SHIPPING_COST;
    return { subtotal, shipping, total: subtotal + shipping };
  }

  function count() {
    return read().reduce((s, i) => s + i.quantity, 0);
  }
  function updateCount() {
    document.querySelectorAll("[data-cart-count]").forEach((el) => {
      el.textContent = count();
    });
  }

  /* Toast */
  let toastTimer;
  function toast(msg) {
    const el = document.querySelector("[data-toast]");
    if (!el) return;
    el.textContent = msg;
    el.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => (el.hidden = true), 2200);
  }

  /* Render the cart page (if present) */
  function renderCart() {
    const list = document.querySelector("[data-cart-items]");
    if (!list) return;
    const items = read();
    const summary = document.querySelector("[data-cart-summary]");
    const empty = document.querySelector("[data-cart-empty]");

    if (items.length === 0) {
      list.innerHTML = "";
      if (summary) summary.hidden = true;
      if (empty) empty.hidden = false;
      return;
    }
    if (summary) summary.hidden = false;
    if (empty) empty.hidden = true;

    list.innerHTML = items
      .map(
        (i) => `
      <div class="cart-item">
        <div class="cart-item-thumb">${(i.name || "?").charAt(0)}</div>
        <div>
          <div class="cart-item-name">${i.name}</div>
          <div class="cart-item-price">${money(i.price)} each</div>
          <div class="qty" style="margin-top:8px">
            <button type="button" data-dec="${i.id}">−</button>
            <input type="number" value="${i.quantity}" min="1" data-qty-for="${i.id}" />
            <button type="button" data-inc="${i.id}">+</button>
          </div>
        </div>
        <div class="cart-item-right">
          <strong>${money(i.price * i.quantity)}</strong>
          <button class="link-danger" data-remove="${i.id}">Remove</button>
        </div>
      </div>`
      )
      .join("");

    renderTotals(items);
  }

  function renderTotals(items) {
    items = items || read();
    const t = totals(items);
    const set = (sel, val) =>
      document.querySelectorAll(sel).forEach((el) => (el.textContent = val));
    set("[data-summary-subtotal]", money(t.subtotal));
    set("[data-summary-shipping]", t.shipping === 0 ? "Free" : money(t.shipping));
    set("[data-summary-total]", money(t.total));
  }

  /* Wire up global click handlers */
  document.addEventListener("click", (e) => {
    const addBtn = e.target.closest("[data-add-to-cart]");
    if (addBtn) {
      let qty = 1;
      if (addBtn.hasAttribute("data-qty-source")) {
        const input = document.querySelector("[data-qty-input]");
        qty = Math.max(1, parseInt(input && input.value, 10) || 1);
      }
      add({
        id: addBtn.dataset.id,
        name: addBtn.dataset.name,
        price: parseFloat(addBtn.dataset.price),
        quantity: qty,
      });
      return;
    }
    if (e.target.closest("[data-clear-cart]")) return clear();
    const inc = e.target.closest("[data-inc]");
    if (inc) return setQty(inc.dataset.inc, qtyOf(inc.dataset.inc) + 1);
    const dec = e.target.closest("[data-dec]");
    if (dec) return setQty(dec.dataset.dec, qtyOf(dec.dataset.dec) - 1);
    const rm = e.target.closest("[data-remove]");
    if (rm) return remove(rm.dataset.remove);

    // product-detail qty stepper
    const qInc = e.target.closest("[data-qty-inc]");
    const qDec = e.target.closest("[data-qty-dec]");
    if (qInc || qDec) {
      const input = document.querySelector("[data-qty-input]");
      if (input) {
        let v = parseInt(input.value, 10) || 1;
        v += qInc ? 1 : -1;
        input.value = Math.max(1, v);
      }
    }
  });

  document.addEventListener("change", (e) => {
    const q = e.target.closest("[data-qty-for]");
    if (q) setQty(q.dataset.qtyFor, Math.max(1, parseInt(q.value, 10) || 1));
  });

  function qtyOf(id) {
    const it = read().find((i) => String(i.id) === String(id));
    return it ? it.quantity : 0;
  }

  /* Expose for checkout.js */
  window.ShopCart = { read, clear, totals, renderTotals };

  /* Init */
  updateCount();
  renderCart();
})();
