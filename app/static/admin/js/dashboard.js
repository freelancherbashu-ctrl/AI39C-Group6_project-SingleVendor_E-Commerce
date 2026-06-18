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

// ---- 7-day sales chart ----
  const canvas = document.getElementById("dashSalesChart");
  if (canvas && typeof Chart !== "undefined") {
    fetch("/admin/api/sales-chart")
      .then((r) => r.json())
      .then((data) => {
        new Chart(canvas, {
          type: "line",
          data: {
            labels: data.labels,
            datasets: [{
              label: "Revenue (Rs.)",
              data: data.values,
              borderColor: "#1d4ed8",
              backgroundColor: "rgba(29, 78, 216, 0.12)",
              borderWidth: 2,
              tension: 0.3,
              fill: true,
              pointRadius: 4,
              pointBackgroundColor: "#1d4ed8",
            }],
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
              y: { beginAtZero: true, ticks: { callback: (v) => "Rs. " + v.toLocaleString() } },
            },
          },
        });
      })
      .catch((err) => console.warn("Sales chart load failed:", err));
  }
  
})();