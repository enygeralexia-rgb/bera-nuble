import { api, closeModal, COMUNAS_NUBLE, esc, formatCLP, openModal, showToast } from "../api.js";

export async function renderMobility(root, { openAuthModal, state }) {
  const data = await api("/api/mobility/overview");
  const user = state.me?.user;
  const isDriver = !!state.me?.driver && state.me?.driver?.approval_status === "aprobada";

  root.innerHTML = `
    <div class="between" style="margin-bottom:12px;">
      <div>
        <h2>Movilidad BERA (Ñuble)</h2>
        <p class="muted">Sistema propio de coordinación y negociación de tarifas entre mujeres. Seguimiento y pagos simulados.</p>
      </div>
      <div class="row-wrap">
        <button class="btn btn-danger btn-sm" id="btn-sos-test">🆘 Botón de ayuda (Prueba)</button>
        ${user ? `<button class="btn btn-sm" id="btn-new-trip">+ Solicitar viaje</button>` : `<button class="btn btn-sm" id="btn-mob-login">Ingresar para solicitar</button>`}
      </div>
    </div>

    <div class="card" style="background:#FFF0F6;">
      <strong>Política de menores de edad:</strong> ${esc(data.minor_policy_note)}
      ${user ? `<button class="btn btn-outline btn-sm" id="btn-test-minor-block" style="margin-left:8px;">Probar bloqueo autónomo menor</button>` : ""}
    </div>

    <section class="card">
      <h3>Solicitudes abiertas y en negociación</h3>
      ${data.open_requests.length === 0 ? `<div class="empty-state">No hay solicitudes abiertas en este momento.</div>` :
        data.open_requests.map((req) => `
          <div class="card" style="box-shadow:none;margin-bottom:10px;">
            <div class="between">
              <div>
                <strong>${esc(req.origin_comuna)} → ${esc(req.destination_comuna)}</strong>
                <span class="badge">${esc(req.trip_type)}</span>
                <span class="badge badge-warn">${esc(req.status)}</span>
                ${req.for_minor_demo ? `<span class="badge badge-ad">Flujo propuesto: menor acompañada</span>` : ""}
              </div>
              <strong>Tarifa propuesta: ${formatCLP(req.proposed_fare)}</strong>
            </div>
            <p class="muted" style="margin-top:4px;">
              Pasajera: ${esc(req.passenger_name)} · ${esc(req.origin_address_simulated)} → ${esc(req.destination_address_simulated)}
              · Est. ${req.estimated_km} km / ${req.estimated_min} min · Pago: ${esc(req.payment_method)}
              ${req.scheduled_at ? `<br>Programado: <strong>${esc(req.scheduled_at.replace("T", " ").slice(0, 16))}</strong>` : ""}
              ${req.minor_label_simulated ? `<br><em>${esc(req.minor_label_simulated)}</em>` : ""}
            </p>

            ${req.proposals.length > 0 ? `
              <div style="background:var(--bg-soft);padding:10px;border-radius:10px;margin:8px 0;">
                <strong style="font-size:0.85rem;">Historial de negociación:</strong>
                ${req.proposals.map((p) => `
                  <div class="between" style="padding:6px 0;border-bottom:1px solid var(--border-soft);font-size:0.86rem;">
                    <div>
                      <strong>${esc(p.proposer_role === "conductora" ? p.driver_name : "Pasajera")}</strong>
                      propone <strong>${formatCLP(p.amount)}</strong> (${esc(p.payment_method)})
                      · Vehículo: ${esc(p.brand_model)} (${esc(p.plate_simulated)})
                      · Estado: <span class="badge">${esc(p.status)}</span>
                      ${p.note ? `<div class="muted">${esc(p.note)}</div>` : ""}
                    </div>
                    <div class="row-wrap">
                      ${user && p.status === "vigente" && (
                        (p.proposer_role === "conductora" && req.passenger_id === user.id) ||
                        (p.proposer_role === "pasajera" && isDriver)
                      ) ? `<button class="btn btn-sm btn-accept-prop" data-req="${req.id}" data-prop="${p.id}">Aceptar ${formatCLP(p.amount)}</button>` : ""}
                      ${user && req.passenger_id === user.id && p.proposer_role === "conductora" && p.status === "vigente" ? `
                        <button class="btn btn-secondary btn-sm btn-counter" data-req="${req.id}" data-drv="${p.driver_id}">Contraofertar</button>
                      ` : ""}
                    </div>
                  </div>
                `).join("")}
              </div>
            ` : ""}

            ${user && isDriver && req.passenger_id !== user.id ? `
              <button class="btn btn-secondary btn-sm btn-driver-offer" data-req="${req.id}" data-fare="${req.proposed_fare}">
                Enviar oferta / contraoferta como conductora
              </button>
            ` : ""}
          </div>
        `).join("")}
    </section>

    ${user ? `
      <section class="card">
        <h3>Mis viajes confirmados e historial</h3>
        ${data.my_trips.length === 0 ? `<div class="empty-state">Aún no tienes viajes confirmados.</div>` :
          data.my_trips.map((t) => {
            const isPassenger = t.passenger_id === user.id;
            const isTripDriver = t.driver_user_id === user.id;
            return `
              <div class="card" style="box-shadow:none;margin-bottom:10px;">
                <div class="between">
                  <div>
                    <strong>Viaje #${t.id}: ${esc(t.origin_comuna)} → ${esc(t.destination_comuna)}</strong>
                    <span class="badge badge-ok">${esc(t.status)}</span>
                    <span class="badge">PIN inicio: ${esc(t.start_pin)}</span>
                  </div>
                  <strong>${formatCLP(t.final_fare)} (${esc(t.payment_method)})</strong>
                </div>
                <p class="muted" style="margin-top:4px;">
                  Conductora: ${esc(t.driver_name)} (★ ${t.driver_rating}) · Vehículo: ${esc(t.brand_model)} ${esc(t.color)} (${esc(t.plate_simulated)})<br>
                  Estado de pago: <strong>${esc(t.payment_status)}</strong> · Seguimiento simulado: ${t.simulated_progress}%
                </p>
                <div class="progress-bar"><div class="progress-fill" style="width:${t.simulated_progress}%"></div></div>

                <div class="row-wrap" style="margin-top:8px;">
                  ${isTripDriver && t.status !== "completado" && t.status !== "cancelado" ? `
                    <select class="trip-step-sel" data-trip="${t.id}" style="width:auto;margin:0;">
                      <option value="conductora en camino">Conductora en camino</option>
                      <option value="conductora en origen">Conductora en origen</option>
                      <option value="en curso">En curso</option>
                      <option value="completado">Completado</option>
                    </select>
                    <button class="btn btn-sm btn-adv-trip" data-trip="${t.id}">Actualizar etapa</button>
                  ` : ""}

                  ${isPassenger && t.payment_status === "pendiente" ? `
                    <button class="btn btn-secondary btn-sm btn-pay" data-trip="${t.id}" data-act="declarar_pasajera">Declarar pago (Demo)</button>
                  ` : ""}
                  ${t.payment_status !== "confirmado_simulado" ? `
                    <button class="btn btn-outline btn-sm btn-pay" data-trip="${t.id}" data-act="confirmar_simulado">Confirmar pago simulado</button>
                  ` : ""}

                  ${isPassenger ? `
                    <button class="btn btn-secondary btn-sm btn-share" data-trip="${t.id}">Compartir enlace temporal</button>
                    <button class="btn btn-outline btn-sm btn-revoke" data-trip="${t.id}">Revocar enlace</button>
                  ` : ""}

                  ${t.status !== "completado" && t.status !== "cancelado" ? `
                    <button class="btn btn-danger btn-sm btn-cancel-trip" data-trip="${t.id}">Cancelar viaje</button>
                  ` : ""}

                  ${isPassenger && t.status === "completado" ? `
                    <button class="btn btn-secondary btn-sm btn-review-trip" data-trip="${t.id}">Valorar viaje</button>
                  ` : ""}
                  <button class="btn btn-outline btn-sm btn-report-trip" data-trip="${t.id}">Reportar incidente</button>
                </div>
              </div>
            `;
          }).join("")}
      </section>

      <section class="card">
        <div class="between">
          <h3>Contactos de confianza (Ficticios)</h3>
          <button class="btn btn-secondary btn-sm" id="btn-add-contact">+ Agregar contacto</button>
        </div>
        ${data.trusted_contacts.length === 0 ? `<p class="muted">Sin contactos de confianza registrados.</p>` :
          data.trusted_contacts.map((c) => `
            <div style="padding:6px 0;border-bottom:1px solid var(--border-soft);">
              <strong>${esc(c.name)}</strong> (${esc(c.relation)}) · ${esc(c.phone_simulated)}
            </div>
          `).join("")}
      </section>
    ` : ""}
  `;

  if (document.getElementById("btn-mob-login")) {
    document.getElementById("btn-mob-login").onclick = openAuthModal;
  }

  document.getElementById("btn-sos-test").onclick = async () => {
    if (!user) return openAuthModal();
    const res = await api("/api/mobility/help-test", { method: "POST" });
    openModal(`
      <h3>Flujo de ayuda (Demostración)</h3>
      <p>${esc(res.message)}</p>
      <p class="muted">BERA no promete vigilancia permanente ni respuesta de autoridades. En versión productiva se integraría con canales oficiales definidos.</p>
      <button class="btn" id="close-sos">Entendido</button>
    `);
    document.getElementById("close-sos").onclick = closeModal;
  };

  const minorBtn = document.getElementById("btn-test-minor-block");
  if (minorBtn) {
    minorBtn.onclick = async () => {
      try {
        await api("/api/mobility/requests", {
          method: "POST",
          body: JSON.stringify({
            origin_comuna: "Chillán",
            origin_address_simulated: "Centro",
            destination_comuna: "Bulnes",
            destination_address_simulated: "Plaza",
            proposed_fare: 5000,
            minor_autonomous_attempt: true,
          }),
        });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  }

  const newTripBtn = document.getElementById("btn-new-trip");
  if (newTripBtn) {
    newTripBtn.onclick = () => {
      openModal(`
        <h3>Solicitar viaje en Ñuble</h3>
        <form id="form-new-trip">
          <div class="grid-2">
            <div>
              <label>Comuna origen</label>
              <select name="origin_comuna">${COMUNAS_NUBLE.map((c) => `<option>${esc(c)}</option>`).join("")}</select>
            </div>
            <div>
              <label>Comuna destino</label>
              <select name="destination_comuna">${COMUNAS_NUBLE.map((c, i) => `<option ${i === 1 ? "selected" : ""}>${esc(c)}</option>`).join("")}</select>
            </div>
          </div>
          <label>Dirección origen (simulada)</label>
          <input name="origin_address_simulated" required placeholder="Ej: Plaza de Armas (Simulado)" />
          <label>Dirección destino (simulada)</label>
          <input name="destination_address_simulated" required placeholder="Ej: Campus Chillán (Simulado)" />
          <div class="grid-2">
            <div>
              <label>Tipo de viaje</label>
              <select name="trip_type" id="trip-type-sel">
                <option value="inmediato">Inmediato</option>
                <option value="programado">Programado</option>
              </select>
            </div>
            <div>
              <label>Tarifa propuesta (CLP)</label>
              <input type="number" name="proposed_fare" value="3500" min="1000" required />
            </div>
          </div>
          <div id="sched-wrap" class="hidden">
            <label>Fecha y hora programada</label>
            <input type="datetime-local" name="scheduled_at" />
          </div>
          <label>Método de pago previsto</label>
          <select name="payment_method">
            <option value="efectivo">Efectivo (Demo)</option>
            <option value="transferencia">Transferencia (Demo)</option>
            <option value="pago_bera">Pago dentro de BERA (Simulado)</option>
          </select>
          <label style="display:flex;gap:8px;align-items:flex-start;font-weight:500;">
            <input type="checkbox" name="for_minor_demo" style="width:auto;margin-top:4px;" />
            <span>Mostrar flujo propuesto: adulta responsable solicita viaje para menor acompañada (no habilitado para operación real).</span>
          </label>
          <button class="btn" type="submit" style="width:100%;">Publicar solicitud</button>
        </form>
      `);
      document.getElementById("trip-type-sel").onchange = (e) => {
        document.getElementById("sched-wrap").classList.toggle("hidden", e.target.value !== "programado");
      };
      document.getElementById("form-new-trip").onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const body = Object.fromEntries(fd);
        body.proposed_fare = Number(body.proposed_fare);
        body.for_minor_demo = !!fd.get("for_minor_demo");
        if (!body.scheduled_at) body.scheduled_at = null;
        try {
          const r = await api("/api/mobility/requests", { method: "POST", body: JSON.stringify(body) });
          closeModal();
          showToast(r.message);
          renderMobility(root, { openAuthModal, state });
        } catch (err) {
          showToast(err.message, "err");
        }
      };
    };
  }

  document.querySelectorAll(".btn-driver-offer, .btn-counter").forEach((btn) => {
    btn.onclick = () => {
      const reqId = btn.dataset.req;
      const drvId = btn.dataset.drv ? Number(btn.dataset.drv) : null;
      openModal(`
        <h3>Enviar propuesta de tarifa</h3>
        <form id="form-prop">
          <label>Monto propuesto (CLP)</label>
          <input type="number" name="amount" value="${btn.dataset.fare || 4000}" min="1000" required />
          <label>Método de pago</label>
          <select name="payment_method">
            <option value="efectivo">Efectivo</option>
            <option value="transferencia">Transferencia</option>
            <option value="pago_bera">Pago dentro de BERA</option>
          </select>
          <label>Nota breve</label>
          <input name="note" placeholder="Ej: Disponible en 8 minutos" />
          <button class="btn" type="submit" style="width:100%;">Enviar propuesta</button>
        </form>
      `);
      document.getElementById("form-prop").onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const body = Object.fromEntries(fd);
        body.amount = Number(body.amount);
        body.driver_id = drvId;
        try {
          const r = await api(`/api/mobility/requests/${reqId}/proposals`, { method: "POST", body: JSON.stringify(body) });
          closeModal();
          showToast(r.message);
          renderMobility(root, { openAuthModal, state });
        } catch (err) {
          showToast(err.message, "err");
        }
      };
    };
  });

  document.querySelectorAll(".btn-accept-prop").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const r = await api(`/api/mobility/requests/${btn.dataset.req}/proposals/${btn.dataset.prop}/accept`, { method: "POST" });
        showToast(`${r.message} PIN: ${r.start_pin}`);
        renderMobility(root, { openAuthModal, state });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-adv-trip").forEach((btn) => {
    btn.onclick = async () => {
      const id = btn.dataset.trip;
      const status = document.querySelector(`.trip-step-sel[data-trip="${id}"]`).value;
      try {
        const r = await api(`/api/mobility/trips/${id}/status`, { method: "POST", body: JSON.stringify({ status }) });
        showToast(r.message);
        renderMobility(root, { openAuthModal, state });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-cancel-trip").forEach((btn) => {
    btn.onclick = async () => {
      const reason = prompt("Motivo de cancelación (demostración):") || "Cancelado por usuaria";
      try {
        const r = await api(`/api/mobility/trips/${btn.dataset.trip}/status`, {
          method: "POST",
          body: JSON.stringify({ status: "cancelado", cancellation_reason: reason }),
        });
        showToast(r.message);
        renderMobility(root, { openAuthModal, state });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-pay").forEach((btn) => {
    btn.onclick = async () => {
      try {
        const r = await api(`/api/mobility/trips/${btn.dataset.trip}/payment`, {
          method: "POST",
          body: JSON.stringify({ action: btn.dataset.act }),
        });
        showToast(r.message);
        renderMobility(root, { openAuthModal, state });
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-share").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api(`/api/mobility/trips/${btn.dataset.trip}/share`, { method: "POST" });
      openModal(`
        <h3>Enlace temporal privado</h3>
        <p class="muted">Válido hasta ${esc(r.expires_at)}. Puedes revocarlo en cualquier momento.</p>
        <input readonly value="${esc(window.location.origin + r.share_url)}" />
        <button class="btn" id="close-sh">Cerrar</button>
      `);
      document.getElementById("close-sh").onclick = closeModal;
    };
  });

  document.querySelectorAll(".btn-revoke").forEach((btn) => {
    btn.onclick = async () => {
      const r = await api(`/api/mobility/trips/${btn.dataset.trip}/revoke-share`, { method: "POST" });
      showToast(r.message);
    };
  });

  document.querySelectorAll(".btn-review-trip").forEach((btn) => {
    btn.onclick = async () => {
      const comment = prompt("Tu reseña sobre el viaje completado:");
      if (!comment) return;
      try {
        const r = await api("/api/common/reviews", {
          method: "POST",
          body: JSON.stringify({ context_type: "trip", context_id: Number(btn.dataset.trip), rating: 5, comment }),
        });
        showToast(r.message);
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  document.querySelectorAll(".btn-report-trip").forEach((btn) => {
    btn.onclick = async () => {
      const description = prompt("Describe el incidente de demostración:");
      if (!description) return;
      try {
        const r = await api("/api/common/reports", {
          method: "POST",
          body: JSON.stringify({ target_type: "trip", target_id: Number(btn.dataset.trip), category: "seguridad", description }),
        });
        showToast(r.message);
      } catch (err) {
        showToast(err.message, "err");
      }
    };
  });

  const addContactBtn = document.getElementById("btn-add-contact");
  if (addContactBtn) {
    addContactBtn.onclick = () => {
      openModal(`
        <h3>Agregar contacto de confianza (Ficticio)</h3>
        <form id="form-tc">
          <label>Nombre</label><input name="name" required />
          <label>Relación</label><input name="relation" required placeholder="Ej: Hermana, Amiga" />
          <label>Teléfono ficticio</label><input name="phone_simulated" required value="+56 9 0000 4000" />
          <button class="btn" type="submit" style="width:100%;">Guardar</button>
        </form>
      `);
      document.getElementById("form-tc").onsubmit = async (e) => {
        e.preventDefault();
        const body = Object.fromEntries(new FormData(e.target));
        const r = await api("/api/mobility/trusted-contacts", { method: "POST", body: JSON.stringify(body) });
        closeModal();
        showToast(r.message);
        renderMobility(root, { openAuthModal, state });
      };
    };
  }
}
