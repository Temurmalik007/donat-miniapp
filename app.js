const tg = window.Telegram?.WebApp;
if (tg) { tg.ready(); tg.expand(); }

const initData = tg?.initData || "";
const API = "";

let state = {
  categories: [],
  currentCategory: null,
  currentProducts: [],
  selectedProduct: null,
  balance: 0,
};

// ---------------- helpers ----------------
function fmt(n) {
  return Number(n).toLocaleString("ru-RU").replace(/,/g, " ");
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2200);
}

async function api(path, body) {
  const res = await fetch(API + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Xatolik yuz berdi" }));
    throw new Error(err.detail || "Xatolik yuz berdi");
  }
  return res.json();
}

async function apiGet(path) {
  const res = await fetch(API + path);
  if (!res.ok) throw new Error("Xatolik yuz berdi");
  return res.json();
}

// ---------------- navigation ----------------
function switchTab(tab) {
  document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
  document.getElementById(`view-${tab}`).classList.remove("hidden");
  document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
  const navBtn = document.querySelector(`.nav-btn[data-tab="${tab}"]`);
  if (navBtn) navBtn.classList.add("active");

  if (tab === "history") loadHistory("orders");
}

document.querySelectorAll(".nav-btn").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.querySelectorAll("[data-back]").forEach(btn => {
  btn.addEventListener("click", () => switchTab(btn.dataset.back));
});

// ---------------- load current user ----------------
async function loadMe() {
  try {
    const me = await api("/api/me", { init_data: initData });
    state.balance = me.balance;
    document.getElementById("balanceValue").textContent = fmt(me.balance);
    document.getElementById("userName").textContent = me.full_name || me.username || "Foydalanuvchi";
    document.getElementById("userIdLabel").textContent = `ID: ${me.user_id}`;
    document.getElementById("avatar").textContent = (me.full_name || "A").charAt(0).toUpperCase();
    document.getElementById("settingsUserId").textContent = me.user_id;
    document.getElementById("settingsBalance").textContent = `${fmt(me.balance)} so'm`;
  } catch (e) {
    showToast("Foydalanuvchini aniqlab bo'lmadi. Botni Telegram ichida oching.");
  }
}

// ---------------- categories ----------------
async function loadCategories() {
  try {
    state.categories = await apiGet("/api/categories");
    const grid = document.getElementById("categoryGrid");
    if (!state.categories.length) {
      grid.innerHTML = `<div class="empty-state" style="grid-column:1/-1">Hozircha xizmatlar qo'shilmagan.</div>`;
      return;
    }
    grid.innerHTML = state.categories.map(c => `
      <button class="tile" data-cat="${c.id}">
        ${c.badge ? `<span class="tile-badge">${c.badge}</span>` : ""}
        <div class="tile-icon">${c.icon_emoji || "🎮"}</div>
        <div class="tile-name">${c.name}</div>
      </button>
    `).join("");
    grid.querySelectorAll(".tile").forEach(tile => {
      tile.addEventListener("click", () => openCategory(parseInt(tile.dataset.cat)));
    });
  } catch (e) {
    showToast("Kategoriyalarni yuklab bo'lmadi.");
  }
}

async function openCategory(categoryId) {
  try {
    const data = await apiGet(`/api/categories/${categoryId}/products`);
    state.currentCategory = data.category;
    state.currentProducts = data.products;
    state.selectedProduct = null;

    document.getElementById("productsTitle").textContent = data.category.name;
    const idBlock = document.getElementById("playerIdBlock");
    idBlock.classList.toggle("hidden", !data.category.needs_player_id);
    document.getElementById("playerIdInput").value = "";

    const list = document.getElementById("productList");
    if (!data.products.length) {
      list.innerHTML = `<div class="empty-state" style="grid-column:1/-1">Bu bo'limda hozircha mahsulot yo'q.</div>`;
    } else {
      list.innerHTML = data.products.map(p => `
        <button class="product-card" data-prod="${p.id}">
          <div class="product-name">${p.name}</div>
          <div class="product-price">${fmt(p.price)} so'm</div>
        </button>
      `).join("");
      list.querySelectorAll(".product-card").forEach(card => {
        card.addEventListener("click", () => selectProduct(parseInt(card.dataset.prod)));
      });
    }
    removeBuyBar();
    switchView("products");
  } catch (e) {
    showToast("Mahsulotlarni yuklab bo'lmadi.");
  }
}

function switchView(name) {
  document.querySelectorAll(".view").forEach(v => v.classList.add("hidden"));
  document.getElementById(`view-${name}`).classList.remove("hidden");
}

function selectProduct(productId) {
  state.selectedProduct = state.currentProducts.find(p => p.id === productId);
  document.querySelectorAll(".product-card").forEach(c => {
    c.classList.toggle("selected", parseInt(c.dataset.prod) === productId);
  });
  renderBuyBar();
}

function removeBuyBar() {
  const existing = document.querySelector(".buy-bar");
  if (existing) existing.remove();
}

function renderBuyBar() {
  removeBuyBar();
  const bar = document.createElement("div");
  bar.className = "buy-bar";
  bar.innerHTML = `<button class="buy-btn" id="buyBtn">Sotib olish — ${fmt(state.selectedProduct.price)} so'm</button>`;
  document.getElementById("view-products").appendChild(bar);
  document.getElementById("buyBtn").addEventListener("click", submitOrder);
}

async function submitOrder() {
  if (!state.selectedProduct) return;
  const needsId = state.currentCategory?.needs_player_id;
  const playerId = document.getElementById("playerIdInput").value.trim();

  if (needsId && !playerId) {
    showToast("Player ID kiriting");
    return;
  }
  if (state.balance < state.selectedProduct.price) {
    showToast("Balansingiz yetarli emas. Avval hisobni to'ldiring.");
    return;
  }

  const btn = document.getElementById("buyBtn");
  btn.disabled = true;
  btn.textContent = "Yuborilmoqda...";

  try {
    const res = await api("/api/order", {
      init_data: initData,
      product_id: state.selectedProduct.id,
      player_id: needsId ? playerId : null,
    });
    showToast(`Buyurtma #${res.order_id} qabul qilindi ✅`);
    tg?.HapticFeedback?.notificationOccurred("success");
    await loadMe();
    switchTab("history");
  } catch (e) {
    showToast(e.message);
    btn.disabled = false;
    btn.textContent = `Sotib olish — ${fmt(state.selectedProduct.price)} so'm`;
  }
}

// ---------------- history ----------------
const statusLabels = {
  kutilmoqda: "⏳ Kutilmoqda",
  bajarildi: "🎉 Bajarildi",
  bekor_qilindi: "❌ Bekor qilindi",
  tasdiqlandi: "✅ Tasdiqlandi",
  rad_etildi: "❌ Rad etildi",
};

async function loadHistory(tab) {
  document.querySelectorAll(".pill-tab").forEach(t => t.classList.toggle("active", t.dataset.histtab === tab));
  const list = document.getElementById("historyList");
  list.innerHTML = `<div class="empty-state">Yuklanmoqda...</div>`;

  try {
    if (tab === "orders") {
      const orders = await api("/api/orders", { init_data: initData });
      if (!orders.length) {
        list.innerHTML = `<div class="empty-state">Hali buyurtmalar yo'q</div>`;
        return;
      }
      list.innerHTML = orders.map(o => `
        <div class="history-item">
          <div class="hist-left">
            <div class="hist-title">${o.product_name}</div>
            <div class="hist-date">${o.created_at}</div>
          </div>
          <div class="hist-right">
            <div class="hist-amount">${fmt(o.price)} so'm</div>
            <span class="status-badge status-${o.status}">${statusLabels[o.status] || o.status}</span>
          </div>
        </div>
      `).join("");
    } else {
      const topups = await api("/api/topups", { init_data: initData });
      if (!topups.length) {
        list.innerHTML = `<div class="empty-state">Hali to'lovlar yo'q</div>`;
        return;
      }
      list.innerHTML = topups.map(t => `
        <div class="history-item">
          <div class="hist-left">
            <div class="hist-title">Hisobni to'ldirish (${t.method.toUpperCase()})</div>
            <div class="hist-date">${t.created_at}</div>
          </div>
          <div class="hist-right">
            <div class="hist-amount">+${fmt(t.amount)} so'm</div>
            <span class="status-badge status-${t.status}">${statusLabels[t.status] || t.status}</span>
          </div>
        </div>
      `).join("");
    }
  } catch (e) {
    list.innerHTML = `<div class="empty-state">Yuklab bo'lmadi</div>`;
  }
}

document.querySelectorAll(".pill-tab").forEach(btn => {
  btn.addEventListener("click", () => loadHistory(btn.dataset.histtab));
});

// ---------------- topup / support (open bot chat) ----------------
function goTopup() {
  tg?.showPopup?.({
    title: "Hisobni to'ldirish",
    message: "Bot chatiga qayting va /topup buyrug'ini yuboring — u yerda summani va to'lov chekini yuborasiz.",
    buttons: [{ type: "ok" }],
  }) || showToast("Bot chatida /topup buyrug'ini yuboring");
}

function goSupport() {
  tg?.showPopup?.({
    title: "Yordam",
    message: "Savollaringiz bo'lsa, bot chatiga qaytib yozing — admin siz bilan bog'lanadi.",
    buttons: [{ type: "ok" }],
  }) || showToast("Bot chatida admin bilan bog'laning");
}

document.getElementById("btnTopup").addEventListener("click", goTopup);
document.getElementById("btnTopupSettings").addEventListener("click", goTopup);
document.getElementById("btnSupport").addEventListener("click", goSupport);
document.getElementById("btnSupportSettings").addEventListener("click", goSupport);

// ---------------- init ----------------
(async function init() {
  await loadMe();
  await loadCategories();
})();
