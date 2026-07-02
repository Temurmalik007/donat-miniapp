const API = "";
let categoriesCache = [];

function fmt(n) { return Number(n).toLocaleString("ru-RU").replace(/,/g, " "); }

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2400);
}

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    let detail = "Xatolik yuz berdi";
    try { detail = (await res.json()).detail || detail; } catch (e) {}
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

// ---------------- Navigation ----------------
document.querySelectorAll(".side-link").forEach(link => {
  link.addEventListener("click", () => switchPage(link.dataset.page));
});

function switchPage(page) {
  document.querySelectorAll(".page").forEach(p => p.classList.add("hidden"));
  document.getElementById(`page-${page}`).classList.remove("hidden");
  document.querySelectorAll(".side-link").forEach(l => l.classList.toggle("active", l.dataset.page === page));

  if (page === "dashboard") loadStats();
  if (page === "categories") loadCategories();
  if (page === "products") loadProducts();
  if (page === "orders") loadOrders("");
  if (page === "topups") loadTopups("");
}

// ---------------- Modal ----------------
function openModal(title, bodyHtml) {
  document.getElementById("modalTitle").textContent = title;
  document.getElementById("modalBody").innerHTML = bodyHtml;
  document.getElementById("modalOverlay").classList.remove("hidden");
}
function closeModal() {
  document.getElementById("modalOverlay").classList.add("hidden");
}
document.getElementById("modalClose").addEventListener("click", closeModal);
document.getElementById("modalOverlay").addEventListener("click", (e) => {
  if (e.target.id === "modalOverlay") closeModal();
});

// ---------------- Dashboard ----------------
async function loadStats() {
  try {
    const s = await api("GET", "/api/admin/stats");
    const grid = document.getElementById("statGrid");
    grid.innerHTML = `
      <div class="stat-card"><div class="stat-value">${s.users_count}</div><div class="stat-label">Foydalanuvchilar</div></div>
      <div class="stat-card"><div class="stat-value">${s.orders_count}</div><div class="stat-label">Jami buyurtmalar</div></div>
      <div class="stat-card"><div class="stat-value">${s.pending_orders}</div><div class="stat-label">Kutilayotgan buyurtmalar</div></div>
      <div class="stat-card"><div class="stat-value">${s.pending_topups}</div><div class="stat-label">Kutilayotgan to'lovlar</div></div>
      <div class="stat-card"><div class="stat-value">${fmt(s.total_revenue)}</div><div class="stat-label">Umumiy aylanma (so'm)</div></div>
    `;
  } catch (e) { showToast(e.message); }
}

// ---------------- Categories ----------------
async function loadCategories() {
  try {
    categoriesCache = await api("GET", "/api/admin/categories");
    const body = document.getElementById("categoriesBody");
    if (!categoriesCache.length) {
      body.innerHTML = `<tr class="empty-row"><td colspan="6">Hozircha kategoriya yo'q</td></tr>`;
      return;
    }
    body.innerHTML = categoriesCache.map(c => `
      <tr>
        <td>#${c.id}</td>
        <td style="font-size:20px">${c.icon_emoji}</td>
        <td>${c.name}</td>
        <td>${c.badge || "—"}</td>
        <td>${c.needs_player_id ? "Ha" : "Yo'q"}</td>
        <td>
          <button class="btn-icon" onclick="editCategory(${c.id})">✏️ Tahrirlash</button>
          <button class="btn-danger" onclick="removeCategory(${c.id})">O'chirish</button>
        </td>
      </tr>
    `).join("");
  } catch (e) { showToast(e.message); }
}

function categoryFormHtml(c) {
  return `
    <div class="form-row">
      <label class="form-label">Nomi</label>
      <input class="form-input" id="fName" value="${c ? c.name : ""}" placeholder="masalan: PUBG MOBILE" />
    </div>
    <div class="form-row">
      <label class="form-label">Emoji / ikonka</label>
      <input class="form-input" id="fIcon" value="${c ? c.icon_emoji : "🎮"}" placeholder="🎮" />
    </div>
    <div class="form-row">
      <label class="form-label">Badge (ixtiyoriy)</label>
      <input class="form-input" id="fBadge" value="${c ? c.badge : ""}" placeholder="masalan: Global" />
    </div>
    <div class="form-row form-checkbox">
      <input type="checkbox" id="fNeedsId" ${c && c.needs_player_id ? "checked" : ""} />
      <label for="fNeedsId">Player ID so'ralsin</label>
    </div>
    <div class="form-actions">
      <button class="btn-secondary" id="fCancel">Bekor qilish</button>
      <button class="btn-primary" id="fSave">Saqlash</button>
    </div>
  `;
}

document.getElementById("btnNewCategory").addEventListener("click", () => {
  openModal("Yangi kategoriya", categoryFormHtml(null));
  document.getElementById("fCancel").onclick = closeModal;
  document.getElementById("fSave").onclick = async () => {
    try {
      await api("POST", "/api/admin/categories", {
        name: document.getElementById("fName").value.trim(),
        icon_emoji: document.getElementById("fIcon").value.trim() || "🎮",
        badge: document.getElementById("fBadge").value.trim(),
        needs_player_id: document.getElementById("fNeedsId").checked,
      });
      showToast("Kategoriya qo'shildi ✅");
      closeModal();
      loadCategories();
    } catch (e) { showToast(e.message); }
  };
});

window.editCategory = function (id) {
  const c = categoriesCache.find(x => x.id === id);
  openModal("Kategoriyani tahrirlash", categoryFormHtml(c));
  document.getElementById("fCancel").onclick = closeModal;
  document.getElementById("fSave").onclick = async () => {
    try {
      await api("PUT", `/api/admin/categories/${id}`, {
        name: document.getElementById("fName").value.trim(),
        icon_emoji: document.getElementById("fIcon").value.trim() || "🎮",
        badge: document.getElementById("fBadge").value.trim(),
        needs_player_id: document.getElementById("fNeedsId").checked,
      });
      showToast("Yangilandi ✅");
      closeModal();
      loadCategories();
    } catch (e) { showToast(e.message); }
  };
};

window.removeCategory = async function (id) {
  if (!confirm("Bu kategoriyani (va uning barcha mahsulotlarini) o'chirishga ishonchingiz komilmi?")) return;
  try {
    await api("DELETE", `/api/admin/categories/${id}`);
    showToast("O'chirildi");
    loadCategories();
  } catch (e) { showToast(e.message); }
};

// ---------------- Products ----------------
async function loadProducts() {
  if (!categoriesCache.length) categoriesCache = await api("GET", "/api/admin/categories");
  try {
    const products = await api("GET", "/api/admin/products");
    const body = document.getElementById("productsBody");
    if (!products.length) {
      body.innerHTML = `<tr class="empty-row"><td colspan="5">Hozircha mahsulot yo'q</td></tr>`;
      return;
    }
    body.innerHTML = products.map(p => `
      <tr>
        <td>#${p.id}</td>
        <td>${p.category_name}</td>
        <td>${p.name}</td>
        <td>${fmt(p.price)} so'm</td>
        <td>
          <button class="btn-icon" onclick="editProduct(${p.id}, ${p.category_id}, '${p.name.replace(/'/g, "\\'")}', ${p.price})">✏️ Tahrirlash</button>
          <button class="btn-danger" onclick="removeProduct(${p.id})">O'chirish</button>
        </td>
      </tr>
    `).join("");
  } catch (e) { showToast(e.message); }
}

function categoryOptionsHtml(selectedId) {
  return categoriesCache.map(c => `<option value="${c.id}" ${c.id === selectedId ? "selected" : ""}>${c.name}</option>`).join("");
}

function productFormHtml(categoryId, name, price) {
  return `
    <div class="form-row">
      <label class="form-label">Kategoriya</label>
      <select class="form-select" id="fCategory">${categoryOptionsHtml(categoryId)}</select>
    </div>
    <div class="form-row">
      <label class="form-label">Nomi</label>
      <input class="form-input" id="fPName" value="${name || ""}" placeholder="masalan: 120 UC" />
    </div>
    <div class="form-row">
      <label class="form-label">Narxi (so'm)</label>
      <input class="form-input" id="fPrice" type="number" value="${price || ""}" placeholder="23200" />
    </div>
    <div class="form-actions">
      <button class="btn-secondary" id="fCancel">Bekor qilish</button>
      <button class="btn-primary" id="fSave">Saqlash</button>
    </div>
  `;
}

document.getElementById("btnNewProduct").addEventListener("click", async () => {
  if (!categoriesCache.length) categoriesCache = await api("GET", "/api/admin/categories");
  if (!categoriesCache.length) { showToast("Avval kategoriya qo'shing"); return; }
  openModal("Yangi mahsulot", productFormHtml(categoriesCache[0].id, "", ""));
  document.getElementById("fCancel").onclick = closeModal;
  document.getElementById("fSave").onclick = async () => {
    try {
      await api("POST", "/api/admin/products", {
        category_id: parseInt(document.getElementById("fCategory").value),
        name: document.getElementById("fPName").value.trim(),
        price: parseInt(document.getElementById("fPrice").value),
      });
      showToast("Mahsulot qo'shildi ✅");
      closeModal();
      loadProducts();
    } catch (e) { showToast(e.message); }
  };
});

window.editProduct = function (id, categoryId, name, price) {
  openModal("Mahsulotni tahrirlash", productFormHtml(categoryId, name, price));
  document.getElementById("fCancel").onclick = closeModal;
  document.getElementById("fSave").onclick = async () => {
    try {
      await api("PUT", `/api/admin/products/${id}`, {
        category_id: parseInt(document.getElementById("fCategory").value),
        name: document.getElementById("fPName").value.trim(),
        price: parseInt(document.getElementById("fPrice").value),
      });
      showToast("Narx/nom yangilandi ✅");
      closeModal();
      loadProducts();
    } catch (e) { showToast(e.message); }
  };
};

window.removeProduct = async function (id) {
  if (!confirm("Bu mahsulotni o'chirishga ishonchingiz komilmi?")) return;
  try {
    await api("DELETE", `/api/admin/products/${id}`);
    showToast("O'chirildi");
    loadProducts();
  } catch (e) { showToast(e.message); }
};

// ---------------- Orders ----------------
const orderStatusLabels = {
  kutilmoqda: "Kutilmoqda", bajarildi: "Bajarildi", bekor_qilindi: "Bekor qilindi",
};

document.querySelectorAll("#ordersFilter .filter-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#ordersFilter .filter-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    loadOrders(chip.dataset.status);
  });
});

async function loadOrders(status) {
  try {
    const q = status ? `?status=${status}` : "";
    const orders = await api("GET", "/api/admin/orders" + q);
    const body = document.getElementById("ordersBody");
    if (!orders.length) {
      body.innerHTML = `<tr class="empty-row"><td colspan="8">Buyurtma topilmadi</td></tr>`;
      return;
    }
    body.innerHTML = orders.map(o => `
      <tr>
        <td>#${o.id}</td>
        <td>${o.full_name || "-"} (@${o.username || "-"})<br><span style="color:var(--text-muted);font-size:11.5px">ID: ${o.user_id}</span></td>
        <td>${o.product_name}</td>
        <td>${o.player_id || "—"}</td>
        <td>${fmt(o.price)} so'm</td>
        <td><span class="badge-pill badge-${o.status}">${orderStatusLabels[o.status] || o.status}</span></td>
        <td style="font-size:11.5px;color:var(--text-muted)">${o.created_at}</td>
        <td>
          ${o.status === "kutilmoqda" ? `
            <button class="btn-success" onclick="setOrderStatus(${o.id}, 'bajarildi')">✔️ Bajarildi</button>
            <button class="btn-danger" onclick="cancelOrder(${o.id})">❌ Bekor qilish</button>
          ` : "—"}
        </td>
      </tr>
    `).join("");
  } catch (e) { showToast(e.message); }
}

window.setOrderStatus = async function (id, status) {
  try {
    await api("POST", `/api/admin/orders/${id}/status`, { status });
    showToast("Yangilandi va mijozga xabar berildi ✅");
    const active = document.querySelector("#ordersFilter .filter-chip.active");
    loadOrders(active ? active.dataset.status : "");
  } catch (e) { showToast(e.message); }
};

window.cancelOrder = async function (id) {
  const reason = prompt("Bekor qilish sababi (mijozga yuboriladi, pul balansiga qaytariladi):");
  if (reason === null) return;
  try {
    await api("POST", `/api/admin/orders/${id}/status`, { status: "bekor_qilindi", admin_comment: reason });
    showToast("Bekor qilindi, pul qaytarildi ✅");
    const active = document.querySelector("#ordersFilter .filter-chip.active");
    loadOrders(active ? active.dataset.status : "");
  } catch (e) { showToast(e.message); }
};

// ---------------- Topups ----------------
const topupStatusLabels = { kutilmoqda: "Kutilmoqda", tasdiqlandi: "Tasdiqlandi", rad_etildi: "Rad etildi" };

document.querySelectorAll("#topupsFilter .filter-chip").forEach(chip => {
  chip.addEventListener("click", () => {
    document.querySelectorAll("#topupsFilter .filter-chip").forEach(c => c.classList.remove("active"));
    chip.classList.add("active");
    loadTopups(chip.dataset.status);
  });
});

async function loadTopups(status) {
  try {
    const q = status ? `?status=${status}` : "";
    const topups = await api("GET", "/api/admin/topups" + q);
    const body = document.getElementById("topupsBody");
    if (!topups.length) {
      body.innerHTML = `<tr class="empty-row"><td colspan="7">To'lov topilmadi</td></tr>`;
      return;
    }
    body.innerHTML = topups.map(t => `
      <tr>
        <td>#${t.id}</td>
        <td>${t.full_name || "-"} (@${t.username || "-"})<br><span style="color:var(--text-muted);font-size:11.5px">ID: ${t.user_id}</span></td>
        <td>${fmt(t.amount)} so'm</td>
        <td>${t.method.toUpperCase()}</td>
        <td><span class="badge-pill badge-${t.status}">${topupStatusLabels[t.status] || t.status}</span></td>
        <td style="font-size:11.5px;color:var(--text-muted)">${t.created_at}</td>
        <td>
          ${t.status === "kutilmoqda" ? `
            <button class="btn-success" onclick="setTopupStatus(${t.id}, 'tasdiqlandi')">✔️ Tasdiqlash</button>
            <button class="btn-danger" onclick="setTopupStatus(${t.id}, 'rad_etildi')">❌ Rad etish</button>
          ` : "—"}
        </td>
      </tr>
    `).join("");
  } catch (e) { showToast(e.message); }
}

window.setTopupStatus = async function (id, status) {
  try {
    await api("POST", `/api/admin/topups/${id}/status`, { status });
    showToast("Yangilandi va mijozga xabar berildi ✅");
    const active = document.querySelector("#topupsFilter .filter-chip.active");
    loadTopups(active ? active.dataset.status : "");
  } catch (e) { showToast(e.message); }
};

// ---------------- Init ----------------
loadStats();
