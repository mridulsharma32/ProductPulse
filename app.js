const state = {
  dashboard: null,
};

const elements = {
  form: document.querySelector("#feedbackForm"),
  customer: document.querySelector("#customerInput"),
  content: document.querySelector("#contentInput"),
  csv: document.querySelector("#csvInput"),
  reset: document.querySelector("#resetButton"),
  total: document.querySelector("#totalFeedback"),
  avgRice: document.querySelector("#avgRice"),
  highUrgency: document.querySelector("#highUrgency"),
  negative: document.querySelector("#negativeItems"),
  sentimentChart: document.querySelector("#sentimentChart"),
  categoryChart: document.querySelector("#categoryChart"),
  painPoints: document.querySelector("#painPoints"),
  prd: document.querySelector("#prdOutput"),
  table: document.querySelector("#feedbackTable"),
  toast: document.querySelector("#toast"),
};

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Something went wrong.");
  }
  return data;
}

function showToast(message) {
  elements.toast.textContent = message;
  elements.toast.classList.add("show");
  window.setTimeout(() => elements.toast.classList.remove("show"), 2400);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pillClass(value) {
  return String(value).toLowerCase().replaceAll(" ", "-");
}

function renderBars(target, counts) {
  const entries = Object.entries(counts);
  const max = Math.max(1, ...entries.map((entry) => entry[1]));
  target.innerHTML = entries.length
    ? entries
        .map(([label, value]) => {
          const width = Math.max(8, Math.round((value / max) * 100));
          return `
            <div class="bar-row">
              <strong>${escapeHtml(label)}</strong>
              <div class="bar-track"><div class="bar-fill" style="width:${width}%"></div></div>
              <span>${value}</span>
            </div>
          `;
        })
        .join("")
    : "<p class='hint'>No data yet.</p>";
}

function renderPainPoints(items) {
  elements.painPoints.innerHTML = items.length
    ? items
        .map(
          (item) => `
            <article class="pain-item">
              <strong>
                <span>${escapeHtml(item.phrase)}</span>
                <span>${item.count}x</span>
              </strong>
              <p>${escapeHtml(item.examples[0])}</p>
            </article>
          `
        )
        .join("")
    : "<p class='hint'>Add more similar feedback to reveal repeated pain points.</p>";
}

function renderTable(rows) {
  elements.table.innerHTML = rows
    .map(
      (row) => `
        <tr>
          <td>${escapeHtml(row.customer)}</td>
          <td>${escapeHtml(row.content)}</td>
          <td><span class="pill">${escapeHtml(row.category)}</span></td>
          <td><span class="pill ${pillClass(row.sentiment)}">${escapeHtml(row.sentiment)}</span></td>
          <td><span class="pill ${pillClass(row.urgency)}">${escapeHtml(row.urgency)}</span></td>
          <td><strong>${row.rice_score}</strong></td>
        </tr>
      `
    )
    .join("");
}

function render(dashboard) {
  state.dashboard = dashboard;
  elements.total.textContent = dashboard.stats.total;
  elements.avgRice.textContent = dashboard.stats.avg_rice;
  elements.highUrgency.textContent = dashboard.stats.high_urgency;
  elements.negative.textContent = dashboard.stats.negative;
  renderBars(elements.sentimentChart, dashboard.sentiments);
  renderBars(elements.categoryChart, dashboard.categories);
  renderPainPoints(dashboard.pain_points);
  renderTable(dashboard.feedback);
  elements.prd.textContent = dashboard.prd;
}

async function loadDashboard() {
  render(await api("/api/dashboard"));
}

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length < 2) return [];
  const headers = lines[0].split(",").map((header) => header.trim().toLowerCase());
  const customerIndex = headers.indexOf("customer");
  const contentIndex = headers.indexOf("content");
  if (contentIndex === -1) {
    throw new Error("CSV needs a content column.");
  }
  return lines.slice(1).map((line) => {
    const columns = line.split(",").map((column) => column.trim().replace(/^"|"$/g, ""));
    return {
      customer: customerIndex >= 0 ? columns[customerIndex] : "Anonymous",
      content: columns[contentIndex],
    };
  });
}

elements.form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const content = elements.content.value.trim();
  if (!content) {
    showToast("Add feedback text first.");
    return;
  }
  const dashboard = await api("/api/feedback", {
    method: "POST",
    body: JSON.stringify({
      customer: elements.customer.value.trim() || "Anonymous",
      content,
    }),
  });
  elements.form.reset();
  render(dashboard);
  showToast("Feedback analyzed and prioritized.");
});

elements.csv.addEventListener("change", async () => {
  const file = elements.csv.files[0];
  if (!file) return;
  try {
    const rows = parseCsv(await file.text());
    const dashboard = await api("/api/upload", {
      method: "POST",
      body: JSON.stringify({ rows }),
    });
    render(dashboard);
    showToast(`${rows.length} feedback rows uploaded.`);
  } catch (error) {
    showToast(error.message);
  } finally {
    elements.csv.value = "";
  }
});

elements.reset.addEventListener("click", async () => {
  render(await api("/api/reset", { method: "POST", body: "{}" }));
  showToast("Demo data restored.");
});

loadDashboard().catch((error) => showToast(error.message));
