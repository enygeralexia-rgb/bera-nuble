import { api, closeModal, COMUNAS_NUBLE, esc, formatCLP, openModal, showToast } from "../api.js";

let filters = { comuna: "", modality: "", schedule_type: "", flexible_hours: false, no_experience: false, q: "" };

export async function renderJobs(root, { openAuthModal, state }) {
  const params = new URLSearchParams();
  if (filters.comuna) params.set("comuna", filters.comuna);
  if (filters.modality) params.set("modality", filters.modality);
  if (filters.schedule_type) params.set("schedule_type", filters.schedule_type);
  if (filters.flexible_hours) params.set("flexible_hours", "true");
  if (filters.no_experience) params.set("no_experience", "true");
  if (filters.q) params.set("q", filters.q);

  const data = await api(`/api/jobs?${params.toString()}`);
  const user = state.me?.user;
  const canPublish = state.me?.verifications?.some((v) =>
    ["empleadora", "empresa", "emprendedora"].includes(v.scope) && v.status === "aprobada"
  );

  root.innerHTML = `
    <div class="between" style="margin-bottom:12px;">
      <div>
        <h2>Empleabilidad en Ñuble</h2>
        <p class="muted">Ofertas laborales formales y flexibles. Separadas de anuncios de servicios independientes.</p>
      </div>
      ${user && canPublish ? `<button class="btn btn-sm" id="btn-new-job">+ Publicar oferta</button>` : ""}
    </div>

    <section class="card">
      <div class="grid-3">
        <div>
          <label>Buscar</label>
          <input id="jf-q" value="${esc(filters.q)}" placeholder="Cargo o rubro..." />
        </div>
        <div>
          <label>Comuna</label>
          <select id="jf-comuna">
            <option value="">Todas las comunas (Ñuble)</option>
            ${COMUNAS_NUBLE.map((c) => `<option ${filters.comuna === c ? "selected" : ""}>${esc(c)}</option>`).join("")}
          </select>
        </div>
        <div>
          <label>Modalidad</label>
          <select id="jf-mod">
            <option value="">Todas</option>
            <option value="presencial" ${filters.modality === "presencial" ? "selected" : ""}>Presencial</option>
            <option value="remota" ${filters.modality === "remota" ? "selected" : ""}>Remota / Teletrabajo</option>
            <option value="híbrida" ${filters.modality === "híbrida" ? "selected" : ""}>Híbrida</option>
          </select>
        </div>
      </div>
      <div class="row-wrap">
        <select id="jf-sched" style="width:auto;margin:0;">
          <option value="">Cualquier jornada</option>
          <option value="part-time" ${filters.schedule_type === "part-time" ? "selected" : ""}>Part-time</option>
          <option value="full-time" ${filters.schedule_type === "full-time" ? "selected" : ""}>Full-time</option>
          <option value="por turnos" ${filters.schedule_type === "por turnos" ? "selected" : ""}>Por turnos</option>
        </select>
        <label style="display:flex;gap:6px;align-items:center;margin:0;">
          <input type="checkbox" id="jf-flex" ${filters.flexible_hours ? "checked" : ""} style="width:auto;margin:0;" /> Horario flexible
        </label>
        <label style="display:flex;gap:6px;align-items:center;margin:0;">
          <input type="checkbox" id="jf-noexp" ${filters.no_experience ? "checked" : ""} style="width:auto;margin:0;" /> Sin experiencia
        </label>
        <button class="btn btn-sm" id="jf-apply">Filtrar</button>
        <button class="btn btn-outline btn-sm" id="jf-clear">Limpiar</button>
      </div>
    </section>

    <section>
      ${data.jobs.length === 0 ? `<div class="empty-state">No encontramos ofertas con esos filtros.</div>` :
        data.jobs.map((j) => `
          <div class="card">
            <div class="between">
              <div>
                <h3>${esc(j.title)}</h3>
                <div class="row-wrap" style="margin-bottom:6px;">
                  <span class="badge">${esc(j.comuna)}</span>
                  <span class="badge">${esc(j.modality)}</span>
                  <span class="badge">${esc(j.schedule_type)}</span>
                  ${j.flexible_hours ? `<span class="badge badge-ok">Horario flexible</span>` : ""}
                  ${!j.experience_required ? `<span class="badge badge-ok">Sin experiencia</span>` : ""}
                </div>
              </div>
              <strong>${j.salary_clp ? formatCLP(j.salary_clp) : esc(j.salary_note)}</strong>
            </div>
            <p class="muted">Responsable: ${esc(j.company_name || j.employer_name)} · Rubro: ${esc(j.rubro)} · Contrato: ${esc(j.contract_type)} · Cierre: ${esc(j.closing_date)}</p>
            <p>${esc(j.description)}</p>
            <p class="muted"><strong>Tareas:</strong> ${esc(j.tasks)}<br><strong>Requisitos:</strong> ${esc(j.requirements)}</p>
            <div class="row-wrap">
              ${user ? `<button class="btn btn-sm btn-apply-job" data-id="${j.id}" data-title="${esc(j.title)}">Postular con perfil BERA</button>` :
                `<button class="btn btn-sm btn-guest-job">Ingresar para postular</button>`}
              <button class="btn btn-outline btn-sm btn-rep-job" data-id="${j.id}">Denunciar oferta</button>
            </div>
          </div>
        `).join("")}
    </section>

    ${user && data.my_applications.length > 0 ? `
      <section class="card">
        <h3>Mis postulaciones</h3>
        ${data.my_applications.map((a) => `
          <div class="between" style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <div>
              <strong>${esc(a.job_title)}</strong> (${esc(a.comuna)})
              <span class="badge">${esc(a.status)}</span>
            </div>
            ${a.status !== "retirada" ? `<button class="btn btn-outline btn-sm btn-withdraw" data-id="${a.id}">Retirar</button>` : ""}
          </div>
        `).join("")}
      </section>
    ` : ""}

    ${user && data.my_offers.length > 0 ? `
      <section class="card">
        <h3>Mis ofertas publicadas (Gestión de empleadora)</h3>
        ${data.my_offers.map((o) => `
          <div class="between" style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <div>
              <strong>${esc(o.title)}</strong> · Estado: <span class="badge">${esc(o.moderation_status)}</span>
            </div>
            <button class="btn btn-secondary btn-sm btn-view-apps" data-id="${o.id}" data-title="${esc(o.title)}">Ver postulantes</button>
          </div>
        `).join("")}
      </section>
    ` : ""}
  `;

  document.getElementById("jf-apply").onclick = () => {
    filters.q = document.getElementById("jf-q").value;
    filters.comuna = document.getElementById("jf-comuna").value;
    filters.modality = document.getElementById("jf-mod").value;
    filters.schedule_type = document.getElementById("jf-sched").value;
    filters.flexible_hours = document.getElementById("jf-flex").checked;
    filters.no_experience = document.getElementById("jf-noexp").checked;
    renderJobs(root, { openAuthModal, state });
  };

  document.getElementById("jf-clear").onclick = () => {
    filters = { comuna: "", modality: "", schedule_type: "", flexible_hours: false, no_experience: false, q: "" };
    renderJobs(root, { openAuthModal, state });
  };

  document.querySelectorAll(".btn-guest-job").forEach((b) => (b.onclick = openAuthModal));

  document.querySelectorAll(".btn-apply-job").forEach((btn) => {
    btn.onclick = () => {
      openModal(`
        <h3>Postular a: ${esc(btn.dataset.title)}</h3>
        <form id="form-apply">
          <label>Carta o nota breve de presentación</label>
          <textarea name="cover_note" rows="3" required placeholder="Cuéntale a la empleadora tu disponibilidad..."></textarea>
          <button class="btn" type="submit" style="width:100%;">Enviar postulación</button>
        </form>
      `);
      document.getElementById("form-apply").onsubmit = async (e) => {
        e.preventDefault();
        try {
          const r = await api(`/api/jobs/${btn.dataset.id}/apply`, {
            method: "POST",
            body: JSON.stringify(Object.fromEntries(new FormData(e.target))),
          });
          closeModal();
          showToast(r.message);
          renderJobs(root, { openAuthModal, state });
        } catch (err) {
          showToast(err.message, "err");
        }
      };
    };
  });

  document.querySelectorAll(".btn-withdraw").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api(`/api/jobs/applications/${btn.dataset.id}/withdraw`, { method: "POST" });
      showToast(r.message);
      renderJobs(root, { openAuthModal, state });
    };
  });

  document.querySelectorAll(".btn-view-apps").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api(`/api/jobs/${btn.dataset.id}/applications`);
      openModal(`
        <h3>Postulantes a: ${esc(btn.dataset.title)}</h3>
        ${r.applications.length === 0 ? `<p class="muted">Sin postulaciones activas.</p>` :
          r.applications.map((a) => `
            <div style="padding:10px 0;border-bottom:1px solid var(--border-soft);">
              <strong>${esc(a.applicant_name)}</strong> (${esc(a.applicant_comuna)}) · <span class="badge">${esc(a.status)}</span>
              <p class="muted">${esc(a.cover_note)}</p>
              <p style="font-size:0.8rem;">CV: ${esc(a.cv_snapshot)}</p>
              <div class="row-wrap">
                ${["en revisión", "preseleccionada", "seleccionada", "no seleccionada"].map((st) => `
                  <button class="btn btn-outline btn-sm app-st-btn" data-app="${a.id}" data-st="${st}">${st}</button>
                `).join("")}
              </div>
            </div>
          `).join("")}
      `);
      document.querySelectorAll(".app-st-btn").forEach((sb) => {
        sb.onclick = async () => {
          const res = await api(`/api/jobs/applications/${sb.dataset.app}/status`, {
            method: "POST",
            body: JSON.stringify({ status: sb.dataset.st }),
          });
          showToast(res.message);
          closeModal();
        };
      });
    };
  });

  document.querySelectorAll(".btn-rep-job").forEach((btn) => {
    btn.onclick = async () => {
      if (!user) return openAuthModal();
      const description = prompt("Motivo de la denuncia (ej: solicitud de dinero o engaño):");
      if (!description) return;
      const r = await api("/api/common/reports", {
        method: "POST",
        body: JSON.stringify({ target_type: "job", target_id: Number(btn.dataset.id), category: "estafa", description }),
      });
      showToast(r.message);
    };
  });

  const newJobBtn = document.getElementById("btn-new-job");
  if (newJobBtn) {
    newJobBtn.onclick = () => {
      openModal(`
        <h3>Publicar oferta laboral (Ñuble)</h3>
        <form id="form-new-job">
          <label>Cargo</label><input name="title" required />
          <div class="grid-2">
            <div><label>Rubro</label><input name="rubro" required value="Comercio y Servicios" /></div>
            <div><label>Comuna</label><select name="comuna">${COMUNAS_NUBLE.map((c) => `<option>${esc(c)}</option>`).join("")}</select></div>
          </div>
          <div class="grid-2">
            <div><label>Modalidad</label><select name="modality"><option value="presencial">Presencial</option><option value="remota">Remota</option><option value="híbrida">Híbrida</option></select></div>
            <div><label>Jornada</label><select name="schedule_type"><option value="part-time">Part-time</option><option value="full-time">Full-time</option><option value="por turnos">Por turnos</option></select></div>
          </div>
          <div class="grid-2">
            <div><label>Tipo de contrato</label><select name="contract_type"><option value="plazo fijo">Plazo fijo</option><option value="indefinido">Indefinido</option><option value="honorarios">Honorarios</option><option value="práctica">Práctica</option></select></div>
            <div><label>Fecha de cierre</label><input type="date" name="closing_date" required value="2026-12-15" /></div>
          </div>
          <label>Remuneración referencial (opcional)</label><input type="number" name="salary_clp" placeholder="Dejar vacío si no informada" />
          <label>Descripción</label><textarea name="description" required rows="2"></textarea>
          <label>Tareas</label><input name="tasks" required />
          <label>Requisitos</label><input name="requirements" required />
          <label style="display:flex;gap:6px;align-items:center;"><input type="checkbox" name="flexible_hours" style="width:auto;" /> Horario flexible</label>
          <label style="display:flex;gap:6px;align-items:center;"><input type="checkbox" name="experience_required" style="width:auto;" /> Requiere experiencia previa</label>
          <button class="btn" type="submit" style="width:100%;">Enviar a moderación</button>
        </form>
      `);
      document.getElementById("form-new-job").onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const body = Object.fromEntries(fd);
        body.flexible_hours = !!fd.get("flexible_hours");
        body.experience_required = !!fd.get("experience_required");
        body.salary_clp = body.salary_clp ? Number(body.salary_clp) : null;
        try {
          const r = await api("/api/jobs", { method: "POST", body: JSON.stringify(body) });
          closeModal();
          showToast(r.message);
          renderJobs(root, { openAuthModal, state });
        } catch (err) {
          showToast(err.message, "err");
        }
      };
    };
  }
}
