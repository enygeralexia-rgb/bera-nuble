import { api, esc, showToast } from "../api.js";

export async function renderAdmin(root) {
  const data = await api("/api/admin/dashboard");
  const ind = data.indicators;

  root.innerHTML = `
    <div class="card card-pastel">
      <div class="between">
        <div>
          <h2>Panel de Administración BERA</h2>
          <p><strong>${esc(data.admin.full_name)}</strong> · Nivel: ${esc(data.admin.admin_level)} · Permisos: ${esc(data.admin.permissions.join(", "))}</p>
        </div>
        <span class="badge" style="background:#FFFFFF;">Datos de demostración</span>
      </div>
      <p class="muted" style="margin:0;">${esc(ind.notice)}</p>
    </div>

    <section class="grid-3">
      <div class="card"><strong>Usuarias activas (Demo)</strong><h2>${ind.active_users}</h2></div>
      <div class="card"><strong>Verificaciones pendientes</strong><h2>${ind.pending_verifications}</h2></div>
      <div class="card"><strong>Viajes (Conf / Comp / Canc)</strong><h2>${ind.trips_confirmed} / ${ind.trips_completed} / ${ind.trips_canceled}</h2></div>
      <div class="card"><strong>Postulaciones activas</strong><h2>${ind.job_applications}</h2></div>
      <div class="card"><strong>Emprendimientos activos</strong><h2>${ind.active_ventures}</h2></div>
      <div class="card"><strong>Contactos comerciales / Denuncias</strong><h2>${ind.commercial_contacts} / ${ind.open_reports}</h2></div>
    </section>

    <section class="card">
      <h3>Verificaciones simuladas (Identidad, Conductoras, Empresas)</h3>
      ${data.verifications.map((v) => `
        <div class="between" style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
          <div>
            <strong>#${v.id} ${esc(v.full_name)}</strong> (${esc(v.scope)}) · Estado: <span class="badge">${esc(v.status)}</span>
            <div class="muted">${esc(v.doc_type_simulated)} · Ref: ${esc(v.doc_ref_simulated)} ${v.review_reason ? `· Nota: ${esc(v.review_reason)}` : ""}</div>
          </div>
          <div class="row-wrap">
            <button class="btn btn-sm adm-verif" data-id="${v.id}" data-st="aprobada">Aprobar</button>
            <button class="btn btn-danger btn-sm adm-verif" data-id="${v.id}" data-st="rechazada">Rechazar</button>
            <button class="btn btn-outline btn-sm adm-verif" data-id="${v.id}" data-st="en revisión">En revisión</button>
          </div>
        </div>
      `).join("")}
    </section>

    <section class="grid-2">
      <div class="card">
        <h3>Moderación de Empleos</h3>
        ${data.jobs.map((j) => `
          <div class="between" style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
            <div><strong>${esc(j.title)}</strong><div class="muted">${esc(j.comuna)} · <span class="badge">${esc(j.moderation_status)}</span></div></div>
            <div class="row-wrap">
              <button class="btn btn-sm adm-job" data-id="${j.id}" data-st="aprobada">Aprobar</button>
              <button class="btn btn-danger btn-sm adm-job" data-id="${j.id}" data-st="rechazada">Rechazar</button>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="card">
        <h3>Moderación de Emprendimientos</h3>
        ${data.ventures.map((v) => `
          <div class="between" style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
            <div><strong>${esc(v.name)}</strong><div class="muted">${esc(v.comuna)} · <span class="badge">${esc(v.moderation_status)}</span></div></div>
            <div class="row-wrap">
              <button class="btn btn-sm adm-vent" data-id="${v.id}" data-st="aprobada">Aprobar</button>
              <button class="btn btn-danger btn-sm adm-vent" data-id="${v.id}" data-st="rechazada">Rechazar</button>
            </div>
          </div>
        `).join("")}
      </div>
    </section>

    <section class="grid-2">
      <div class="card">
        <h3>Denuncias</h3>
        ${data.reports.map((r) => `
          <div class="between" style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
            <div>
              <strong>#${r.id} [${esc(r.target_type)}]</strong> <span class="badge">${esc(r.status)}</span>
              <div class="muted">${esc(r.description)}</div>
            </div>
            <div class="row-wrap">
              <button class="btn btn-sm adm-rep" data-id="${r.id}" data-st="resuelta">Resolver</button>
              <button class="btn btn-outline btn-sm adm-rep" data-id="${r.id}" data-st="desestimada">Desestimar</button>
            </div>
          </div>
        `).join("")}
      </div>

      <div class="card">
        <h3>Publicidad ficticia</h3>
        ${data.ads.map((a) => `
          <div class="between" style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
            <div><strong>${esc(a.title)}</strong> (${esc(a.placement)}) · <span class="badge">${esc(a.status)}</span></div>
            <div class="row-wrap">
              <button class="btn btn-sm adm-ad" data-id="${a.id}" data-st="aprobada">Aprobar</button>
              <button class="btn btn-outline btn-sm adm-ad" data-id="${a.id}" data-st="pausada">Pausar</button>
            </div>
          </div>
        `).join("")}
      </div>
    </section>

    <section class="card">
      <h3>Registro de auditoría administrativa</h3>
      ${data.audit_logs.map((l) => `
        <div style="padding:6px 0;border-bottom:1px solid var(--border-soft);font-size:0.84rem;">
          <strong>${esc(l.admin_name)}</strong> (${esc(l.admin_level)}) → <code>${esc(l.action)}</code> sobre ${esc(l.target_type)} #${l.target_id}
          · Motivo: ${esc(l.reason)} · <span class="muted">${esc(l.created_at)}</span>
        </div>
      `).join("")}
    </section>
  `;

  const bindDecide = (selector, urlPrefix) => {
    document.querySelectorAll(selector).forEach((btn) => {
      btn.onclick = async () => {
        const reason = prompt(`Motivo para marcar como '${btn.dataset.st}':`, "Revisión administrativa de demostración");
        if (!reason) return;
        try {
          const r = await api(`${urlPrefix}/${btn.dataset.id}/decide`, {
            method: "POST",
            body: JSON.stringify({ status: btn.dataset.st, reason }),
          });
          showToast(r.message);
          renderAdmin(root);
        } catch (err) {
          showToast(err.message, "err");
        }
      };
    });
  };

  bindDecide(".adm-verif", "/api/admin/verifications");
  bindDecide(".adm-job", "/api/admin/jobs");
  bindDecide(".adm-vent", "/api/admin/ventures");
  bindDecide(".adm-rep", "/api/admin/reports");
  bindDecide(".adm-ad", "/api/admin/ads");
}
