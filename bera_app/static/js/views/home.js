import { api, esc } from "../api.js";

export async function renderHome(root, { navigate, openAuthModal, state }) {
  const data = await api("/api/common/home-summary");
  const user = state.me?.user;
  const inicioAd = data.ads.find((a) => a.placement === "inicio");

  root.innerHTML = `
    <section class="card card-pastel">
      <div class="between">
        <div>
          <span class="badge" style="background:#FFFFFF;">Región de Ñuble · 21 comunas</span>
          <h1 style="margin-top:8px;">BERA — Conectadas para avanzar</h1>
          <p style="margin-bottom:12px;">Plataforma para mujeres de Ñuble que centraliza movilidad segura, empleabilidad con enfoque flexible y vitrina de emprendimientos locales.</p>
          <div class="row-wrap">
            ${!user ? `<button class="btn" id="home-login-btn">Ingresar o probar cuentas demo</button>` : `<span class="badge badge-ok">Sesión activa: ${esc(user.full_name)}</span>`}
            <button class="btn btn-outline" id="home-go-mov">Explorar Movilidad</button>
          </div>
        </div>
      </div>
    </section>

    <section class="grid-3">
      <div class="card">
        <h3>🚗 Movilidad</h3>
        <p class="muted">Viajes inmediatos o programados dentro de Ñuble con propuesta y negociación directa de tarifa.</p>
        <button class="btn btn-sm" data-jump="movilidad">Ir a Movilidad</button>
      </div>
      <div class="card">
        <h3>💼 Empleabilidad</h3>
        <p class="muted">Ofertas verificadas con foco en part-time, teletrabajo, flexibilidad y oportunidades sin experiencia.</p>
        <button class="btn btn-sm" data-jump="empleos">Ir a Empleos</button>
      </div>
      <div class="card">
        <h3>🛍️ Emprendimientos</h3>
        <p class="muted">Vitrina de productos y servicios liderados por mujeres en las 21 comunas de Ñuble.</p>
        <button class="btn btn-sm" data-jump="emprendimientos">Ir a Vitrina</button>
      </div>
    </section>

    <section class="grid-2">
      <div class="card">
        <div class="between">
          <h3>Actividad reciente</h3>
          <span class="badge">Simulada</span>
        </div>
        ${!user ? `<p class="muted">Estás explorando como invitada. Inicia sesión para ver tus notificaciones y actividad.</p>` :
          data.recent_activity.length === 0 ? `<div class="empty-state">Sin actividad reciente aún.</div>` :
          data.recent_activity.map((n) => `
            <div style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
              <strong>${esc(n.title)}</strong>
              <div class="muted">${esc(n.body)}</div>
            </div>
          `).join("")}
      </div>

      <div class="card">
        <h3>Contenido destacado</h3>
        <p class="muted" style="margin-bottom:8px;">Últimas oportunidades aprobadas:</p>
        ${data.featured_jobs.map((j) => `
          <div style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <strong>${esc(j.title)}</strong>
            <div class="muted">${esc(j.comuna)} · ${esc(j.modality)} · ${esc(j.schedule_type)}</div>
          </div>
        `).join("")}
        ${data.featured_ventures.slice(0, 2).map((v) => `
          <div style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <strong>🛍️ ${esc(v.name)}</strong>
            <div class="muted">${esc(v.comuna)} · ${esc(v.category)}</div>
          </div>
        `).join("")}
      </div>
    </section>

    ${inicioAd ? `
      <section class="card" style="background:#FAF4F7;">
        <div class="between">
          <span class="badge badge-ad">${esc(inicioAd.image_badge)} · Anuncio ficticio</span>
          <span class="muted">Vigencia hasta ${esc(inicioAd.valid_until)}</span>
        </div>
        <h4 style="margin-top:6px;">${esc(inicioAd.title)} — ${esc(inicioAd.advertiser)}</h4>
        <p class="muted">${esc(inicioAd.body)}</p>
      </section>
    ` : ""}
  `;

  document.querySelectorAll("[data-jump]").forEach((b) => {
    b.onclick = () => navigate(b.dataset.jump);
  });
  const loginBtn = document.getElementById("home-login-btn");
  if (loginBtn) loginBtn.onclick = openAuthModal;
  document.getElementById("home-go-mov").onclick = () => navigate("movilidad");
}
