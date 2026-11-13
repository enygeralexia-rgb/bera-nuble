import { api, closeModal, COMUNAS_NUBLE, esc, getActiveSlot, openModal, setActiveSlot, setToken, showToast } from "./api.js";
import { renderHome } from "./views/home.js";
import { renderMobility } from "./views/mobility.js";
import { renderJobs } from "./views/jobs.js";
import { renderVentures } from "./views/ventures.js";
import { renderProfile } from "./views/profile.js";
import { renderAdmin } from "./views/admin.js";

export const state = {
  route: "inicio",
  me: null, // { authenticated, guest, user, verifications, driver, vehicle, company }
  providers: null,
};

export async function refreshSession() {
  try {
    state.me = await api("/api/auth/me");
  } catch {
    state.me = { authenticated: false, guest: true, user: null };
  }
  renderTopActions();
}

function renderTopActions() {
  const el = document.getElementById("top-actions");
  const adminBtn = document.getElementById("nav-admin-desktop");
  const user = state.me?.user;
  const isAdmin = user && (user.roles?.includes("admin") || user.admin_level);

  if (adminBtn) {
    adminBtn.classList.toggle("hidden", !isAdmin);
  }

  const slot = getActiveSlot();
  const slotToggle = `<button class="btn btn-secondary btn-sm" id="btn-switch-slot" title="Alterna entre Sesión A y Sesión B para probar flujos de 2 personas">Sesión ${slot}</button>`;

  if (user) {
    el.innerHTML = `
      ${slotToggle}
      ${isAdmin ? `<button class="btn btn-outline btn-sm" id="btn-go-admin">Admin</button>` : ""}
      <span class="badge">${esc(user.full_name.split(" ")[0])}</span>
      <button class="btn btn-outline btn-sm" id="btn-logout">Salir</button>
    `;
    document.getElementById("btn-logout").onclick = async () => {
      await api("/api/auth/logout", { method: "POST" }).catch(() => {});
      setToken("");
      await refreshSession();
      navigate(state.route);
      showToast("Sesión cerrada.");
    };
    if (isAdmin) {
      document.getElementById("btn-go-admin").onclick = () => navigate("admin");
    }
  } else {
    el.innerHTML = `
      ${slotToggle}
      <span class="badge badge-warn">Invitada</span>
      <button class="btn btn-sm" id="btn-open-auth">Ingresar / Demo</button>
    `;
    document.getElementById("btn-open-auth").onclick = openAuthModal;
  }

  document.getElementById("btn-switch-slot").onclick = async () => {
    const next = getActiveSlot() === "A" ? "B" : "A";
    setActiveSlot(next);
    await refreshSession();
    navigate(state.route);
    showToast(`Cambiado a Sesión ${next} (útil para probar 2 personas en paralelo).`);
  };
}

export async function openAuthModal() {
  const [providers, demo] = await Promise.all([
    api("/api/auth/providers"),
    api("/api/auth/demo-accounts"),
  ]);

  openModal(`
    <div class="between" style="margin-bottom:10px;">
      <h3>Acceso a BERA (Demostración)</h3>
      <button class="btn btn-outline btn-sm" id="m-close">Cerrar</button>
    </div>
    <div class="tabs">
      <button class="tab-btn active" data-tab="demo">Cuentas Demo</button>
      <button class="tab-btn" data-tab="login">Ingresar</button>
      <button class="tab-btn" data-tab="register">Registrarse</button>
    </div>

    <div id="tab-demo">
      <p class="muted">Sesión activa: <strong>Sesión ${getActiveSlot()}</strong>. Haz clic en una cuenta ficticia para probar ese rol inmediatamente (clave general demo: <code>BeraDemo2026!</code>):</p>
      <div class="grid-2">
        ${demo.accounts.map((a) => `
          <button class="btn btn-secondary btn-sm demo-pick" data-email="${esc(a.email)}" style="justify-content:flex-start;text-align:left;">
            <div>
              <div><strong>${esc(a.full_name)}</strong></div>
              <div style="font-size:0.75rem;font-weight:400;">${esc(a.email)} · ${esc(a.comuna)}</div>
            </div>
          </button>
        `).join("")}
      </div>
    </div>

    <div id="tab-login" class="hidden">
      <form id="form-login">
        <label>Correo electrónico</label>
        <input type="email" name="email" required placeholder="tu@correo.cl" />
        <label>Contraseña</label>
        <input type="password" name="password" required />
        <button class="btn" type="submit" style="width:100%;">Iniciar sesión</button>
      </form>
      <div style="margin-top:10px;">
        <button class="btn btn-outline btn-sm" id="btn-google-info" style="width:100%;">Continuar con Google</button>
        <p class="muted" style="margin-top:6px;font-size:0.78rem;">${esc(providers.google_oauth_message)}</p>
        <button class="btn btn-secondary btn-sm" id="btn-reset-sim" style="width:100%;margin-top:6px;">Recuperar contraseña (Simulado)</button>
      </div>
    </div>

    <div id="tab-register" class="hidden">
      <form id="form-register">
        <label>Nombre completo</label>
        <input type="text" name="full_name" required placeholder="Ej: Francisca Pérez" />
        <label>Correo electrónico</label>
        <input type="email" name="email" required placeholder="correo@ejemplo.cl" />
        <label>Contraseña (mínimo 8 caracteres)</label>
        <input type="password" name="password" minlength="8" required />
        <div class="grid-2">
          <div>
            <label>Comuna (Región de Ñuble)</label>
            <select name="comuna" required>
              ${COMUNAS_NUBLE.map((c) => `<option value="${esc(c)}">${esc(c)}</option>`).join("")}
            </select>
          </div>
          <div>
            <label>Año de nacimiento (18+)</label>
            <input type="number" name="birth_year" value="1995" min="1920" max="2025" required />
          </div>
        </div>
        <label>¿Qué te gustaría hacer en BERA?</label>
        <select name="intent" required>
          <option value="utilizar servicios">Utilizar servicios</option>
          <option value="ofrecer servicios">Ofrecer servicios</option>
          <option value="ambas">Ambas</option>
        </select>
        <label>Tipo de cuenta</label>
        <select name="account_type" id="reg-account-type">
          <option value="personal">Cuenta personal (Mujer)</option>
          <option value="empresa">Empresa representada por mujer verificada</option>
        </select>
        <div id="reg-company-fields" class="hidden">
          <label>Nombre de la empresa</label>
          <input type="text" name="company_name" placeholder="Ej: Comercial Ñuble SpA (Ficticia)" />
          <label>RUT empresa (simulado)</label>
          <input type="text" name="company_rut_simulated" placeholder="76.000.000-0 (Simulado)" />
        </div>
        <label style="display:flex;gap:8px;align-items:flex-start;font-weight:500;">
          <input type="checkbox" name="eligibility_declared" checked required style="width:auto;margin-top:4px;" />
          <span>Declaro ser mujer (o representante mujer autorizada) y cumplo la elegibilidad de BERA. No se usa reconocimiento facial para inferir género.</span>
        </label>
        <label style="display:flex;gap:8px;align-items:flex-start;font-weight:500;">
          <input type="checkbox" name="consent_accepted" checked required style="width:auto;margin-top:4px;" />
          <span>Acepto condiciones de demostración (datos ficticios, sin cobros ni viajes reales).</span>
        </label>
        <button class="btn" type="submit" style="width:100%;">Crear cuenta</button>
      </form>
    </div>
  `);

  document.getElementById("m-close").onclick = closeModal;

  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      ["demo", "login", "register"].forEach((t) => {
        document.getElementById(`tab-${t}`).classList.toggle("hidden", t !== btn.dataset.tab);
      });
    };
  });

  document.querySelectorAll(".demo-pick").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const res = await api("/api/auth/demo-login", {
          method: "POST",
          body: JSON.stringify({ email: btn.dataset.email }),
        });
        setToken(res.token);
        closeModal();
        await refreshSession();
        navigate(state.route);
        showToast(res.message);
      } catch (e) {
        showToast(e.message, "err");
      }
    };
  });

  document.getElementById("form-login").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    try {
      const res = await api("/api/auth/login", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(fd)),
      });
      setToken(res.token);
      closeModal();
      await refreshSession();
      navigate(state.route);
      showToast("Sesión iniciada.");
    } catch (err) {
      showToast(err.message, "err");
    }
  };

  document.getElementById("btn-google-info").onclick = () => {
    showToast(providers.google_oauth_message, "err");
  };

  document.getElementById("btn-reset-sim").onclick = async () => {
    const email = document.querySelector("#form-login input[name='email']").value || "usuaria@bera.cl";
    const r = await api(`/api/auth/simulate-password-reset?email=${encodeURIComponent(email)}`, { method: "POST" });
    showToast(r.message);
  };

  document.getElementById("reg-account-type").onchange = (e) => {
    document.getElementById("reg-company-fields").classList.toggle("hidden", e.target.value !== "empresa");
  };

  document.getElementById("form-register").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd);
    body.birth_year = Number(body.birth_year);
    body.eligibility_declared = !!fd.get("eligibility_declared");
    body.consent_accepted = !!fd.get("consent_accepted");
    try {
      const res = await api("/api/auth/register", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setToken(res.token);
      closeModal();
      await refreshSession();
      navigate(state.route);
      showToast(res.message);
    } catch (err) {
      showToast(err.message, "err");
    }
  };
}

export async function navigate(route) {
  state.route = route;
  window.location.hash = route;
  document.querySelectorAll("[data-route]").forEach((el) => {
    el.classList.toggle("active", el.dataset.route === route);
  });

  const root = document.getElementById("app-root");
  root.innerHTML = `<div class="skeleton"></div><div class="skeleton"></div>`;

  try {
    if (route === "inicio") await renderHome(root, { navigate, openAuthModal, state });
    else if (route === "movilidad") await renderMobility(root, { navigate, openAuthModal, state });
    else if (route === "empleos") await renderJobs(root, { navigate, openAuthModal, state });
    else if (route === "emprendimientos") await renderVentures(root, { navigate, openAuthModal, state });
    else if (route === "perfil") await renderProfile(root, { navigate, openAuthModal, refreshSession, state });
    else if (route === "admin") await renderAdmin(root, { navigate, state });
    else await renderHome(root, { navigate, openAuthModal, state });
  } catch (err) {
    root.innerHTML = `
      <div class="card">
        <h3>No pudimos cargar esta sección</h3>
        <p class="muted">${esc(err.message)}</p>
        <button class="btn btn-sm" id="btn-retry">Reintentar</button>
      </div>
    `;
    document.getElementById("btn-retry").onclick = () => navigate(route);
  }
}

function setupConnectivity() {
  const banner = document.getElementById("offline-banner");
  const sync = () => banner.classList.toggle("hidden", navigator.onLine);
  window.addEventListener("online", sync);
  window.addEventListener("offline", sync);
  sync();
}

async function init() {
  setupConnectivity();
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }
  document.querySelectorAll("[data-route]").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(btn.dataset.route);
    });
  });

  await refreshSession();
  const initialRoute = (window.location.hash || "#inicio").replace("#", "");
  await navigate(initialRoute || "inicio");
}

init();
