/* =====================================================
   admin_base.js — Shared behaviour for all admin pages
   ===================================================== */

(function () {
  "use strict";

  // ---- Mobile sidebar toggle ----
  const toggle = document.getElementById("adminSidebarToggle");
  const sidebar = document.querySelector(".admin-sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    // close on outside click (mobile)
    document.addEventListener("click", (e) => {
      if (window.innerWidth > 768) return;
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  // ---- Auto-dismiss flash messages after 4 seconds ----
  const flashes = document.getElementById("adminFlashes");
  if (flashes) {
    setTimeout(() => {
      flashes.querySelectorAll(".admin-flash").forEach((el) => {
        el.style.transition = "opacity .4s, transform .4s";
        el.style.opacity = "0";
        el.style.transform = "translateY(-6px)";
        setTimeout(() => el.remove(), 400);
      });
    }, 4000);
  }

  // ---- Global helper for confirm-then-submit forms ----
  // Any form with class .js-confirm asks before submitting.
  document.querySelectorAll("form.js-confirm").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.dataset.confirm || "Are you sure?";
      if (!confirm(msg)) e.preventDefault();
    });
  });

})();