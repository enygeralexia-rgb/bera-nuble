import { api, closeModal, COMUNAS_NUBLE, esc, formatCLP, openModal, showToast } from "../api.js";

let vFilters = { comuna: "", category: "", q: "" };

export async function renderVentures(root, { openAuthModal, state }) {
  const params = new URLSearchParams();
  if (vFilters.comuna) params.set("comuna", vFilters.comuna);
  if (vFilters.category) params.set("category", vFilters.category);
  if (vFilters.q) params.set("q", vFilters.q);

  const data = await api(`/api/ventures?${params.toString()}`);
  const user = state.me?.user;
  const isVerifiedEntrep = state.me?.verifications?.some((v) => v.scope === "emprendedora" && v.status === "aprobada");

  root.innerHTML = `
    <div class="between" style="margin-bottom:12px;">
      <div>
        <h2>Vitrina de Emprendimientos</h2>
        <p class="muted">Vitrina y canal de contacto en Ñuble (sin carrito ni pagos en línea).</p>
      </div>
      ${user && isVerifiedEntrep ? `<button class="btn btn-sm" id="btn-new-venture">+ Publicar emprendimiento</button>` : ""}
    </div>

    <section class="card">
      <div class="grid-3">
        <div><label>Buscar</label><input id="vf-q" value="${esc(vFilters.q)}" placeholder="Nombre o rubro..." /></div>
        <div>
          <label>Comuna</label>
          <select id="vf-comuna">
            <option value="">Todas las comunas</option>
            ${COMUNAS_NUBLE.map((c) => `<option ${vFilters.comuna === c ? "selected" : ""}>${esc(c)}</option>`).join("")}
          </select>
        </div>
        <div>
          <label>Categoría</label>
          <select id="vf-cat">
            <option value="">Todas</option>
            <option ${vFilters.category === "Cosmética y Bienestar" ? "selected" : ""}>Cosmética y Bienestar</option>
            <option ${vFilters.category === "Servicios y Oficios" ? "selected" : ""}>Servicios y Oficios</option>
            <option ${vFilters.category === "Alimentación y Repostería" ? "selected" : ""}>Alimentación y Repostería</option>
          </select>
        </div>
      </div>
      <div class="row-wrap">
        <button class="btn btn-sm" id="vf-apply">Filtrar</button>
        <button class="btn btn-outline btn-sm" id="vf-clear">Limpiar</button>
      </div>
    </section>

    <section class="grid-2">
      ${data.ventures.length === 0 ? `<div class="empty-state">No hay emprendimientos para este filtro.</div>` :
        data.ventures.map((v) => `
          <div class="card">
            <div class="between">
              <div>
                <span class="badge">${esc(v.comuna)}</span>
                <span class="badge">${esc(v.category)}</span>
              </div>
              ${user ? `<button class="btn btn-outline btn-sm btn-fav" data-id="${v.id}">${v.is_favorite ? "♥ Favorito" : "♡ Guardar"}</button>` : ""}
            </div>
            <h3 style="margin-top:8px;">${esc(v.name)}</h3>
            <p>${esc(v.description)}</p>
            <p class="muted">
              <strong>Horario:</strong> ${esc(v.schedule_text)} · <strong>Disponibilidad:</strong> ${esc(v.availability)}<br>
              <strong>Redes:</strong> ${esc(v.social_handle || "No informadas")}
              ${v.avg_rating ? ` · ★ ${v.avg_rating} (${v.review_count})` : ""}
            </p>
            ${v.items.length > 0 ? `
              <div style="background:var(--bg-soft);padding:10px;border-radius:10px;margin-bottom:10px;">
                <strong style="font-size:0.84rem;">Catálogo:</strong>
                ${v.items.map((it) => `
                  <div class="between" style="font-size:0.84rem;padding:4px 0;">
                    <span>${esc(it.title)} (${esc(it.item_type)})</span>
                    <strong>${it.price_clp ? formatCLP(it.price_clp) : "Consultar"}</strong>
                  </div>
                `).join("")}
              </div>
            ` : ""}
            <div class="row-wrap">
              ${user ? `<button class="btn btn-sm btn-contact-v" data-id="${v.id}" data-name="${esc(v.name)}">Contactar por chat</button>` :
                `<button class="btn btn-sm btn-guest-v">Ingresar para contactar</button>`}
              ${v.whatsapp_authorized ? `<button class="btn btn-secondary btn-sm btn-wa-preview" data-wa="${esc(v.whatsapp_simulated)}">WhatsApp autorizado (Demo)</button>` : ""}
              <button class="btn btn-outline btn-sm btn-rep-v" data-id="${v.id}">Denunciar</button>
            </div>
          </div>
        `).join("")}
    </section>

    ${user && data.my_ventures.length > 0 ? `
      <section class="card">
        <h3>Mis emprendimientos</h3>
        ${data.my_ventures.map((mv) => `
          <div class="between" style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
            <div>
              <strong>${esc(mv.name)}</strong> (${esc(mv.comuna)}) · Estado: <span class="badge">${esc(mv.moderation_status)}</span>
            </div>
            <button class="btn btn-secondary btn-sm btn-edit-v" data-id="${mv.id}" data-name="${esc(mv.name)}" data-cat="${esc(mv.category)}" data-comuna="${esc(mv.comuna)}" data-desc="${esc(mv.description)}" data-sched="${esc(mv.schedule_text)}">Editar</button>
          </div>
        `).join("")}
      </section>
    ` : ""}
  `;

  document.getElementById("vf-apply").onclick = () => {
    vFilters.q = document.getElementById("vf-q").value;
    vFilters.comuna = document.getElementById("vf-comuna").value;
    vFilters.category = document.getElementById("vf-cat").value;
    renderVentures(root, { openAuthModal, state });
  };
  document.getElementById("vf-clear").onclick = () => {
    vFilters = { comuna: "", category: "", q: "" };
    renderVentures(root, { openAuthModal, state });
  };

  document.querySelectorAll(".btn-guest-v").forEach((b) => (b.onclick = openAuthModal));

  document.querySelectorAll(".btn-fav").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api(`/api/ventures/${btn.dataset.id}/favorite`, { method: "POST" });
      showToast(r.message);
      renderVentures(root, { openAuthModal, state });
    };
  });

  document.querySelectorAll(".btn-wa-preview").forEach((btn) => {
    btn.onclick = () => {
      openModal(`
        <h3>Contacto WhatsApp autorizado (Demostración)</h3>
        <p>Número ficticio autorizado por la emprendedora: <strong>${esc(btn.dataset.wa)}</strong></p>
        <p class="muted">En la demostración no se abren conversaciones con terceros reales.</p>
        <button class="btn" id="close-wa">Cerrar</button>
      `);
      document.getElementById("close-wa").onclick = closeModal;
    };
  });

  document.querySelectorAll(".btn-contact-v").forEach((btn) => {
    btn.onclick = async () => {
      const msg = prompt(`Mensaje para ${btn.dataset.name}:`, "Hola, me interesa consultar disponibilidad.");
      if (!msg) return;
      try {
        const r = await api(`/api/ventures/${btn.dataset.id}/contact?message=${encodeURIComponent(msg)}`, { method: "POST" });
        showToast(r.message);
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-rep-v").forEach((btn) => {
    btn.onclick = async () => {
      if (!user) return openAuthModal();
      const description = prompt("Describe el motivo de la denuncia:");
      if (!description) return;
      const r = await api("/api/common/reports", {
        method: "POST",
        body: JSON.stringify({ target_type: "venture", target_id: Number(btn.dataset.id), category: "contenido_enganoso", description }),
      });
      showToast(r.message);
    };
  });

  const newVBtn = document.getElementById("btn-new-venture");
  if (newVBtn) {
    newVBtn.onclick = () => openVentureForm(null, root, openAuthModal, state);
  }
  document.querySelectorAll(".btn-edit-v").forEach((btn) => {
    btn.onclick = () => openVentureForm(btn.dataset, root, openAuthModal, state);
  });
}

function openVentureForm(existing, root, openAuthModal, state) {
  openModal(`
    <h3>${existing ? "Editar emprendimiento (cambios sensibles vuelven a revisión)" : "Nuevo emprendimiento"}</h3>
    <form id="form-venture">
      <label>Nombre</label><input name="name" required value="${esc(existing?.name || "")}" />
      <div class="grid-2">
        <div><label>Categoría</label><input name="category" required value="${esc(existing?.cat || "Servicios y Oficios")}" /></div>
        <div><label>Comuna</label><select name="comuna">${COMUNAS_NUBLE.map((c) => `<option ${existing?.comuna === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></div>
      </div>
      <label>Descripción</label><textarea name="description" required rows="2">${esc(existing?.desc || "")}</textarea>
      <label>Horario de atención</label><input name="schedule_text" required value="${esc(existing?.sched || "Lunes a viernes 10:00 a 18:00")}" />
      <label style="display:flex;gap:6px;align-items:center;"><input type="checkbox" name="whatsapp_authorized" style="width:auto;" /> Autorizar mostrar WhatsApp ficticio</label>
      <input name="whatsapp_simulated" placeholder="+56 9 0000 5555 (Ficticio)" />
      <button class="btn" type="submit" style="width:100%;">Guardar</button>
    </form>
  `);
  document.getElementById("form-venture").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const body = Object.fromEntries(fd);
    body.whatsapp_authorized = !!fd.get("whatsapp_authorized");
    body.items = [];
    try {
      const r = existing
        ? await api(`/api/ventures/${existing.id}`, { method: "PUT", body: JSON.stringify(body) })
        : await api("/api/ventures", { method: "POST", body: JSON.stringify(body) });
      closeModal();
      showToast(r.message);
      renderVentures(root, { openAuthModal, state });
    } catch (err) {
      showToast(err.message, "err");
    }
  };
}
