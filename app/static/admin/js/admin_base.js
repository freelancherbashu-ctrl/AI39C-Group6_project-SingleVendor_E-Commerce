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

  // ---- Topbar profile dropdown ----
(function () {
  const trigger = document.getElementById("adminUserTrigger");
  const dropdown = document.getElementById("adminUserDropdown");
  if (!trigger || !dropdown) return;

  trigger.addEventListener("click", (e) => {
    e.stopPropagation();
    dropdown.classList.toggle("open");
  });

  // Close when clicking outside
  document.addEventListener("click", (e) => {
    if (!dropdown.contains(e.target) && e.target !== trigger) {
      dropdown.classList.remove("open");
    }
  });

  // Logout placeholder (teammate will wire this)
  const logoutBtn = dropdown.querySelector(".admin-user-logout");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", (e) => {
      e.preventDefault();
      alert("Logout will be handled by the auth module when ready.");
    });
  }

  // ---- Loading spinner on form submit ----
(function () {
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", function () {
      const btn = form.querySelector("button[type='submit'], button:not([type])");
      if (!btn) return;

      // Skip if it's a "delete" or already-loading button
      if (btn.classList.contains("btn-loading")) return;

      // Save original text in case we need it
      btn.dataset.originalText = btn.innerHTML;
      btn.classList.add("btn-loading");

      // Detect light buttons so spinner is visible
      if (btn.classList.contains("prod-btn-light") ||
          btn.classList.contains("ord-btn-light") ||
          btn.classList.contains("set-btn-light") ||
          btn.classList.contains("prof-btn-light")) {
        btn.classList.add("btn-loading-light");
      }

      // Re-enable after 5s safety net (in case submit fails silently)
      setTimeout(() => {
        btn.classList.remove("btn-loading", "btn-loading-light");
      }, 5000);
    });
  });
})();
})();



})();