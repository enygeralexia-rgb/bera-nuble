export const COMUNAS_NUBLE = [
  "Chillán", "Chillán Viejo", "Bulnes", "El Carmen", "Pemuco", "Pinto", "Quillón",
  "San Ignacio", "Yungay", "San Carlos", "Coihueco", "Ñiquén", "San Fabián",
  "San Nicolás", "Quirihue", "Cobquecura", "Coelemu", "Ninhue", "Portezuelo",
  "Ránquil", "Treguaco"
];

export function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function formatCLP(val) {
  if (val === null || val === undefined) return "No informada";
  return "$" + Number(val).toLocaleString("es-CL");
}

export function getActiveSlot() {
  return localStorage.getItem("bera_active_slot") || "A";
}

export function setActiveSlot(slot) {
  localStorage.setItem("bera_active_slot", slot);
}

export function getToken(slot = getActiveSlot()) {
  return localStorage.getItem(`bera_token_${slot}`) || "";
}

export function setToken(token, slot = getActiveSlot()) {
  if (token) {
    localStorage.setItem(`bera_token_${slot}`, token);
  } else {
    localStorage.removeItem(`bera_token_${slot}`);
  }
}

export function showToast(message, type = "ok") {
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type === "err" ? "toast-err" : "toast-ok"}`;
  el.textContent = message;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4200);
}

export function openModal(html) {
  const root = document.getElementById("modal-root");
  root.innerHTML = `<div class="modal-backdrop" id="modal-backdrop"><div class="modal-card">${html}</div></div>`;
  document.getElementById("modal-backdrop").addEventListener("click", (e) => {
    if (e.target.id === "modal-backdrop") closeModal();
  });
}

export function closeModal() {
  document.getElementById("modal-root").innerHTML = "";
}

export async function api(path, options = {}) {
  const token = getToken();
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(path, { ...options, headers });
  } catch (err) {
    throw new Error("Sin conexión con el servidor. Verifica tu red.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Error ${res.status}`);
  }
  return data;
}
