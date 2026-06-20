/* =====================================================
   categories.js — Behaviour for categories.html
   ===================================================== */

(function () {
  "use strict";

  // Smart delete confirm — warns if category has products
  document.querySelectorAll(".cat-delete-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const name = form.dataset.name || "this category";
      const count = parseInt(form.dataset.count || "0", 10);
      let msg = `Delete category "${name}"?`;
      if (count > 0) {
        msg += `\n\n⚠️  ${count} product(s) are linked to it. They will be uncategorised, not deleted.`;
      }
      if (!confirm(msg)) e.preventDefault();
    });
  });

  // Trim whitespace before submit
  document.querySelectorAll("form input[name=name]").forEach((inp) => {
    inp.form && inp.form.addEventListener("submit", () => { inp.value = inp.value.trim(); });
  });

})();