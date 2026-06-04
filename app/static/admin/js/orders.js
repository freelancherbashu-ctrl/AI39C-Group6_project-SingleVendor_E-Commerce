/* =====================================================
   orders.js — Behaviour for orders.html & order_detail.html
   ===================================================== */

(function () {
  "use strict";

  // Confirm order deletion
  document.querySelectorAll(".ord-delete-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const id = form.dataset.order || "?";
      if (!confirm(`Delete Order #${id} permanently? This cannot be undone.`)) e.preventDefault();
    });
  });

  // Warn when changing status to "cancelled" or "completed"
  document.querySelectorAll(".ord-status-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const select = form.querySelector("select[name=status]");
      if (!select) return;
      const v = select.value;
      if (v === "cancelled" && !confirm("Mark this order as CANCELLED?")) e.preventDefault();
      else if (v === "completed" && !confirm("Mark this order as COMPLETED? Revenue will be counted.")) e.preventDefault();
    });
  });

})();