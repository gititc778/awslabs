/* ShopWave checkout — renders the cart summary and POSTs the order. */
(function () {
  const money = (n) => "£" + Number(n).toFixed(2);
  const cart = window.ShopCart;
  if (!cart) return;

  const items = cart.read();
  const linesEl = document.querySelector("[data-checkout-lines]");

  if (linesEl) {
    if (items.length === 0) {
      linesEl.innerHTML = '<p class="muted small">Your cart is empty.</p>';
    } else {
      linesEl.innerHTML = items
        .map(
          (i) =>
            `<div class="checkout-line"><span>${i.quantity} × ${i.name}</span><span>${money(
              i.price * i.quantity
            )}</span></div>`
        )
        .join("");
    }
  }
  cart.renderTotals(items);

  const form = document.getElementById("checkout-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const errEl = document.querySelector("[data-checkout-error]");
    const btn = document.querySelector("[data-place-order]");
    const showErr = (msg) => {
      if (errEl) {
        errEl.textContent = msg;
        errEl.hidden = false;
      }
    };

    const current = cart.read();
    if (current.length === 0) {
      showErr("Your cart is empty — add something first.");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Placing order…";

    const payload = {
      customer: {
        name: form.name.value.trim(),
        email: form.email.value.trim(),
        address: form.address.value.trim(),
      },
      items: current,
    };

    try {
      const res = await fetch(window.CHECKOUT_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Something went wrong.");
      // Success — go to the confirmation page (cart cleared there).
      window.location.href = data.redirect;
    } catch (err) {
      showErr(err.message);
      btn.disabled = false;
      btn.textContent = "Place order";
    }
  });
})();
