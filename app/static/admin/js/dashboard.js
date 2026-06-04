/* =====================================================
   dashboard.js — Animations for admin_index.html
   ===================================================== */

(function () {
  "use strict";

  // Animate counters from 0 -> target
  document.querySelectorAll(".dash-card[data-target]").forEach((card) => {
    const target = parseInt(card.dataset.target, 10) || 0;
    const el = card.querySelector("[data-count]");
    if (!el) return;

    const duration = 800;
    const start = performance.now();

    function step(now) {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);   // ease-out cubic
      el.textContent = Math.floor(eased * target).toLocaleString();
      if (progress < 1) requestAnimationFrame(step);
      else el.textContent = target.toLocaleString();
    }
    requestAnimationFrame(step);
  });

})();