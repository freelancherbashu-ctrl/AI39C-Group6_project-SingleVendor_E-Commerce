/* =====================================================
   products.js — Behaviour for products.html & product_form.html
   ===================================================== */

(function () {
  "use strict";

  // ---- Delete confirm (per product, uses data-name) ----
  document.querySelectorAll(".prod-delete-form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const name = form.dataset.name || "this product";
      if (!confirm(`Delete "${name}"? This cannot be undone.`)) e.preventDefault();
    });
  });

  // ---- Live image preview on file select (product_form.html) ----
  const fileInput = document.getElementById("prodImageInput");
  const preview = document.getElementById("prodImagePreview");
  if (fileInput && preview) {
    fileInput.addEventListener("change", (e) => {
      const file = e.target.files && e.target.files[0];
      if (!file) return;
      if (!file.type.startsWith("image/")) {
        alert("Please choose an image file.");
        fileInput.value = "";
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        alert("Image must be smaller than 5 MB.");
        fileInput.value = "";
        return;
      }
      const reader = new FileReader();
      reader.onload = (ev) => {
        preview.src = ev.target.result;
        preview.style.display = "block";
      };
      reader.readAsDataURL(file);
    });
  }

  // ---- Search auto-submit after typing pause (optional UX) ----
  const search = document.getElementById("prodSearch");
  if (search) {
    let t;
    search.addEventListener("input", () => {
      clearTimeout(t);
      t = setTimeout(() => search.form.submit(), 600);
    });
  }

  // ---- Form validation hint ----
  const form = document.getElementById("prodForm");
  if (form) {
    form.addEventListener("submit", (e) => {
      const price = form.querySelector("[name=price]");
      const stock = form.querySelector("[name=stock]");
      if (price && parseFloat(price.value) < 0) {
        alert("Price cannot be negative.");
        e.preventDefault();
        return;
      }
      if (stock && parseInt(stock.value, 10) < 0) {
        alert("Stock cannot be negative.");
        e.preventDefault();
      }
    });
  }

})();