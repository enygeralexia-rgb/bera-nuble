import { api, COMUNAS_NUBLE, esc, showToast } from "../api.js";

export async function renderProfile(root, { openAuthModal, refreshSession, state }) {
  const user = state.me?.user;
  if (!user) {
    const help = await api("/api/common/help-center");
    root.innerHTML = `
      <div class="card">
        <h2>Perfil de Invitada</h2>
        <p class="muted">Como invitada puedes explorar ofertas y emprendimientos públicos, pero no postular, solicitar viajes, publicar ni enviar mensajes.</p>
        <button class="btn" id="prof-login-btn">Ingresar o usar cuenta demo</button>
      </div>
      <div class="card">
        <h3>Centro de ayuda</h3>
        ${help.articles.map((a) => `<p><strong>${esc(a.title)}:</strong> ${esc(a.body)}</p>`).join("")}
      </div>
    `;
    document.getElementById("prof-login-btn").onclick = openAuthModal;
    return;
  }

  const [convs, notifs, agenda, blocks, help] = await Promise.all([
    api("/api/common/conversations"),
    api("/api/common/notifications"),
    api("/api/common/agenda"),
    api("/api/common/blocks"),
    api("/api/common/help-center"),
  ]);

  root.innerHTML = `
    <div class="card">
      <div class="between">
        <div>
          <h2>${esc(user.full_name)}</h2>
          <p class="muted">${esc(user.email)} · ${esc(user.comuna)} · Roles: ${esc((user.roles || []).join(", "))}</p>
        </div>
        <div>
          ${user.email_verified ? `<span class="badge badge-ok">Correo verificado (Simulado)</span>` :
            `<button class="btn btn-secondary btn-sm" id="btn-sim-email">Simular verificación de correo</button>`}
        </div>
      </div>

      <form id="form-prof" style="margin-top:12px;">
        <div class="grid-2">
          <div><label>Nombre</label><input name="full_name" value="${esc(user.full_name)}" required /></div>
          <div><label>Comuna</label><select name="comuna">${COMUNAS_NUBLE.map((c) => `<option ${user.comuna === c ? "selected" : ""}>${esc(c)}</option>`).join("")}</select></div>
        </div>
        <label>Resumen CV ficticio (solo visible para postulaciones)</label>
        <input name="cv_summary" value="${esc(user.cv_summary || "")}" />
        <label>Habilidades</label>
        <input name="cv_skills" value="${esc(user.cv_skills || "")}" />
        <button class="btn btn-sm" type="submit">Guardar perfil</button>
      </form>
    </div>

    <div class="card">
      <div class="between">
        <h3>Verificación simulada para ofrecer servicios</h3>
        <span class="badge badge-warn">Verificación simulada</span>
      </div>
      <p class="muted">En producción requiere cédula, biometría con prueba de vida y revisión humana. Aquí puedes probar el envío ficticio.</p>
      ${(state.me.verifications || []).map((v) => `
        <div style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
          <strong>Ámbito: ${esc(v.scope)}</strong> · Estado: <span class="badge">${esc(v.status)}</span>
          · Ref: ${esc(v.doc_ref_simulated)}
          ${v.review_reason ? `<div class="muted">Motivo: ${esc(v.review_reason)}</div>` : ""}
        </div>
      `).join("")}
      <form id="form-verif" style="margin-top:10px;">
        <div class="grid-2">
          <div>
            <label>Ámbito</label>
            <select name="scope">
              <option value="identidad">Identidad general</option>
              <option value="conductora">Conductora</option>
              <option value="emprendedora">Emprendedora</option>
              <option value="empleadora">Empleadora</option>
            </select>
          </div>
          <div><label>Referencia documento ficticio</label><input name="doc_ref_simulated" required value="SIM-DOC-DEMO-99" /></div>
        </div>
        <input type="hidden" name="doc_type_simulated" value="Cédula (Simulada)" />
        <label>Licencia / Acreditación (requerida para conductora)</label>
        <input name="license_simulated" placeholder="Ej: LIC-SIM-123" />
        <button class="btn btn-secondary btn-sm" type="submit">Enviar verificación simulada</button>
      </form>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>Chat interno</h3>
        ${convs.conversations.length === 0 ? `<p class="muted">Sin conversaciones activas.</p>` :
          convs.conversations.map((c) => `
            <div style="padding:8px 0;border-bottom:1px solid var(--border-soft);">
              <strong>${esc(c.other_name)}</strong> <span class="badge">${esc(c.context_type)}</span>
              <div style="max-height:130px;overflow-y:auto;margin:6px 0;font-size:0.84rem;">
                ${c.messages.map((m) => `<div><strong>${esc(m.sender_name.split(" ")[0])}:</strong> ${esc(m.body)}</div>`).join("")}
              </div>
              <div class="row-wrap">
                <input class="chat-in" data-conv="${c.id}" placeholder="Escribe un mensaje..." style="flex:1;margin:0;" />
                <button class="btn btn-sm btn-send-chat" data-conv="${c.id}">Enviar</button>
                <button class="btn btn-outline btn-sm btn-block-u" data-uid="${c.other_user_id}">Bloquear</button>
              </div>
            </div>
          `).join("")}
      </div>

      <div class="card">
        <h3>Notificaciones internas (Simuladas)</h3>
        ${notifs.notifications.length === 0 ? `<p class="muted">Sin notificaciones.</p>` :
          notifs.notifications.slice(0, 8).map((n) => `
            <div style="padding:6px 0;border-bottom:1px solid var(--border-soft);font-size:0.86rem;">
              <strong>${esc(n.title)}</strong>
              <div class="muted">${esc(n.body)}</div>
            </div>
          `).join("")}
      </div>
    </div>

    <div class="grid-2">
      <div class="card">
        <h3>Agenda de viajes programados</h3>
        ${agenda.scheduled_requests.length === 0 && agenda.confirmed_scheduled_trips.length === 0
          ? `<p class="muted">No tienes eventos programados.</p>`
          : agenda.scheduled_requests.map((s) => `<div>Solicitud #${s.id}: ${esc(s.origin_comuna)} → ${esc(s.destination_comuna)} (${esc(s.scheduled_at)})</div>`).join("")}
      </div>

      <div class="card">
        <h3>Privacidad, apelación y cuenta</h3>
        <p class="muted">Bloqueos activos: ${blocks.blocks.length}</p>
        <div class="row-wrap">
          <button class="btn btn-outline btn-sm" id="btn-appeal">Enviar apelación de elegibilidad</button>
          <button class="btn btn-danger btn-sm" id="btn-del-acc">Solicitar eliminación de cuenta</button>
        </div>
      </div>
    </div>

    <div class="card">
      <h3>Centro de ayuda</h3>
      ${help.articles.map((a) => `<p><strong>${esc(a.title)}:</strong> ${esc(a.body)}</p>`).join("")}
    </div>
  `;

  const simEmailBtn = document.getElementById("btn-sim-email");
  if (simEmailBtn) {
    simEmailBtn.onclick = async () => {
      const r = await api("/api/auth/simulate-email-verify", { method: "POST" });
      showToast(r.message);
      await refreshSession();
      renderProfile(root, { openAuthModal, refreshSession, state });
    };
  }

  document.getElementById("form-prof").onsubmit = async (e) => {
    e.preventDefault();
    const r = await api("/api/auth/profile", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
    showToast(r.message);
    await refreshSession();
  };

  document.getElementById("form-verif").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await api("/api/auth/verifications", { method: "POST", body: JSON.stringify(Object.fromEntries(new FormData(e.target))) });
      showToast(r.message);
      await refreshSession();
      renderProfile(root, { openAuthModal, refreshSession, state });
    } catch (err) {
      showToast(err.message, "err");
    }
  };

  document.querySelectorAll(".btn-send-chat").forEach((btn) => {
    btn.onclick = async () => {
      const inp = document.querySelector(`.chat-in[data-conv="${btn.dataset.conv}"]`);
      if (!inp.value.trim()) return;
      try {
        await api(`/api/common/conversations/${btn.dataset.conv}/messages`, {
          method: "POST",
          body: JSON.stringify({ body: inp.value.trim(), simulate_auto_reply: true }),
        });
        renderProfile(root, { openAuthModal, refreshSession, state });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-block-u").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api("/api/common/blocks", {
        method: "POST",
        body: JSON.stringify({ blocked_user_id: Number(btn.dataset.uid), reason: "Bloqueo de usuaria" }),
      });
      showToast(r.message);
      renderProfile(root, { openAuthModal, refreshSession, state });
    };
  });

  document.getElementById("btn-appeal").onclick = async () => {
    const reason = prompt("Motivo de tu apelación:");
    if (!reason) return;
    try {
      const r = await api("/api/auth/appeal", { method: "POST", body: JSON.stringify({ reason }) });
      showToast(r.message);
    } catch (err) {
      showToast(err.message, "err");
    }
  };

  document.getElementById("btn-del-acc").onclick = async () => {
    if (!confirm("¿Confirmas solicitar la eliminación de tu cuenta en la demostración?")) return;
    const r = await api("/api/auth/request-deletion", { method: "POST" });
    showToast(r.message);
  };
}
