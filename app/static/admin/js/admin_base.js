/* admin_base.js - Shared behaviour for all admin pages */

(function () {
  "use strict";

  // ---- Mobile sidebar toggle ----
  const toggle = document.getElementById("adminSidebarToggle");
  const sidebar = document.querySelector(".admin-sidebar");
  const mobileOverlay = document.getElementById("adminMobileOverlay");

  if (toggle && sidebar) {
    function openSidebar() {
      sidebar.classList.add("mobile-open");
      if (mobileOverlay) mobileOverlay.classList.add("active");
      document.body.style.overflow = "hidden";
    }
    function closeSidebar() {
      sidebar.classList.remove("mobile-open");
      if (mobileOverlay) mobileOverlay.classList.remove("active");
      document.body.style.overflow = "";
    }
    toggle.addEventListener("click", () => {
      sidebar.classList.contains("mobile-open") ? closeSidebar() : openSidebar();
    });
    if (mobileOverlay) {
      mobileOverlay.addEventListener("click", closeSidebar);
    }
    sidebar.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => {
        if (window.innerWidth <= 768) closeSidebar();
      });
    });
    document.addEventListener("click", (e) => {
      if (window.innerWidth > 768) return;
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        closeSidebar();
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
  document.querySelectorAll("form.js-confirm").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const msg = form.dataset.confirm || "Are you sure?";
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // ---- Topbar profile dropdown ----
  const trigger = document.getElementById("adminUserTrigger");
  const dropdown = document.getElementById("adminUserDropdown");
  if (trigger && dropdown) {
    trigger.addEventListener("click", (e) => {
      e.stopPropagation();
      dropdown.classList.toggle("open");
    });
    document.addEventListener("click", (e) => {
      if (!dropdown.contains(e.target) && e.target !== trigger) {
        dropdown.classList.remove("open");
      }
    });
    const logoutBtn = dropdown.querySelector(".admin-user-logout");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", (e) => {
        e.preventDefault();
        alert("Logout will be handled by the auth module when ready.");
      });
    }
  }

  // ---- Loading spinner on form submit ----
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", function () {
      const btn = form.querySelector("button[type='submit'], button:not([type])");
      if (!btn) return;
      if (btn.classList.contains("btn-loading")) return;
      btn.dataset.originalText = btn.innerHTML;
      btn.classList.add("btn-loading");
      if (btn.classList.contains("prod-btn-light") ||
          btn.classList.contains("ord-btn-light") ||
          btn.classList.contains("set-btn-light") ||
          btn.classList.contains("prof-btn-light")) {
        btn.classList.add("btn-loading-light");
      }
      setTimeout(() => {
        btn.classList.remove("btn-loading", "btn-loading-light");
      }, 5000);
    });
  });

  // ---- Delete confirmation modal ----
  const deleteModal = document.getElementById("deleteModal");
  const deleteModalMsg = document.getElementById("deleteModalMsg");
  const deleteModalCancel = document.getElementById("deleteModalCancel");
  const deleteModalConfirm = document.getElementById("deleteModalConfirm");

  if (deleteModal) {
    let pendingForm = null;

    document.querySelectorAll(".prod-delete-form, .ord-delete-form, [data-confirm]").forEach((form) => {
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        pendingForm = form;
        const name = form.dataset.name || "this item";
        deleteModalMsg.textContent = "Are you sure you want to delete " + name + "? This cannot be undone.";
        deleteModal.style.display = "flex";
      });
    });

    deleteModalCancel.addEventListener("click", () => {
      deleteModal.style.display = "none";
      pendingForm = null;
    });

    deleteModalConfirm.addEventListener("click", () => {
      deleteModal.style.display = "none";
      if (pendingForm) {
        pendingForm.submit();
        pendingForm = null;
      }
    });

    deleteModal.addEventListener("click", (e) => {
      if (e.target === deleteModal) {
        deleteModal.style.display = "none";
        pendingForm = null;
      }
    });
  }

})();