/* BuildCorp - JS del frontend: firma digital, selects encadenados (API REST), filtros y dashboard. */
(function () {
  "use strict";

  async function getJSON(url) {
    const r = await fetch(url, { credentials: "same-origin", headers: { Accept: "application/json" } });
    if (!r.ok) throw new Error("HTTP " + r.status);
    const data = await r.json();
    return Array.isArray(data) ? data : data.results || [];
  }

  function opciones(select, items, seleccionado, vacio) {
    select.innerHTML = "";
    const o = document.createElement("option");
    o.value = "";
    o.textContent = vacio || "---------";
    select.appendChild(o);
    items.forEach(function (it) {
      const op = document.createElement("option");
      op.value = it.id;
      op.textContent = it.label || it.nombre;
      if (String(it.id) === String(seleccionado)) op.selected = true;
      select.appendChild(op);
    });
  }

  // ------------------------------------------------------------------
  // Firma digital en <canvas> -> PNG base64 en un input oculto
  // ------------------------------------------------------------------
  function initFirmas() {
    document.querySelectorAll("canvas[data-firma-para]").forEach(function (canvas) {
      const input = document.getElementById(canvas.dataset.firmaPara);
      const wrap = canvas.parentElement;
      const ctx = canvas.getContext("2d");
      let dibujando = false, trazos = 0;

      function ajustar() {
        const r = canvas.getBoundingClientRect(), ratio = window.devicePixelRatio || 1;
        canvas.width = r.width * ratio;
        canvas.height = r.height * ratio;
        ctx.scale(ratio, ratio);
        ctx.lineWidth = 2.2;
        ctx.lineCap = "round";
        ctx.lineJoin = "round";
        ctx.strokeStyle = "#0b1f4a";
        if (input.value) {
          const img = new Image();
          img.onload = function () { ctx.drawImage(img, 0, 0, r.width, r.height); };
          img.src = input.value;
          wrap.classList.add("firmado");
        }
      }
      function pos(e) {
        const r = canvas.getBoundingClientRect();
        return { x: e.clientX - r.left, y: e.clientY - r.top };
      }
      function tamanoCambio() {
        const r = canvas.getBoundingClientRect();
        return Math.round(r.width * (window.devicePixelRatio || 1)) !== canvas.width;
      }
      // Si la página cargó oculta o cambió el ancho (rotar el celular), se recalcula el lienzo
      window.addEventListener("resize", function () { if (tamanoCambio()) ajustar(); });
      canvas.addEventListener("pointerdown", function (e) {
        if (tamanoCambio()) ajustar();
        dibujando = true;
        canvas.setPointerCapture(e.pointerId);
        const p = pos(e);
        ctx.beginPath();
        ctx.moveTo(p.x, p.y);
      });
      canvas.addEventListener("pointermove", function (e) {
        if (!dibujando) return;
        const p = pos(e);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();
        trazos++;
      });
      function terminar() {
        if (!dibujando) return;
        dibujando = false;
        if (trazos > 1 && canvas.width > 0) {
          input.value = canvas.toDataURL("image/png");
          wrap.classList.add("firmado");
          wrap.classList.remove("invalida");
        }
      }
      canvas.addEventListener("pointerup", terminar);
      canvas.addEventListener("pointerleave", terminar);

      const limpiar = document.querySelector('[data-limpiar-firma="' + canvas.dataset.firmaPara + '"]');
      if (limpiar) limpiar.addEventListener("click", function () {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        input.value = "";
        trazos = 0;
        wrap.classList.remove("firmado");
      });
      ajustar();
    });

    document.querySelectorAll("form[data-requiere-firma]").forEach(function (form) {
      form.addEventListener("submit", function (e) {
        let ok = true;
        form.querySelectorAll("canvas[data-firma-para]").forEach(function (c) {
          if (!document.getElementById(c.dataset.firmaPara).value) {
            c.parentElement.classList.add("invalida");
            ok = false;
          }
        });
        if (!ok) {
          e.preventDefault();
          alert("Debe registrar la firma digital antes de continuar.");
        }
      });
    });
  }

  // ------------------------------------------------------------------
  // Selects encadenados Región -> Ciudad -> Comuna (consume la API REST)
  // ------------------------------------------------------------------
  async function initTerritorio() {
    const comuna = document.querySelector("form[data-territorio] select[name=comuna]");
    if (!comuna) return;
    const cont = comuna.closest("[data-campo]") || comuna.parentElement;
    const fila = document.createElement("div");
    fila.className = "row g-2 mb-2";
    fila.innerHTML =
      '<div class="col-6"><label class="form-label small mb-1">Región</label><select class="form-select form-select-sm" id="sel-region"></select></div>' +
      '<div class="col-6"><label class="form-label small mb-1">Ciudad</label><select class="form-select form-select-sm" id="sel-ciudad"></select></div>';
    cont.insertBefore(fila, cont.firstChild);
    const selRegion = fila.querySelector("#sel-region"), selCiudad = fila.querySelector("#sel-ciudad");
    const actual = comuna.value;
    let regionId = "", ciudadId = "";
    try {
      if (actual) {
        const c = await (await fetch("/api/comunas/" + actual + "/", { credentials: "same-origin" })).json();
        regionId = c.region;
        ciudadId = c.ciudad;
      }
      opciones(selRegion, await getJSON("/api/regiones/?vigente=true"), regionId, "Seleccione región…");
      async function cargarCiudades(sel) {
        const items = selRegion.value ? await getJSON("/api/ciudades/?vigente=true&region=" + selRegion.value) : [];
        opciones(selCiudad, items, sel, "Seleccione ciudad…");
      }
      async function cargarComunas(sel) {
        if (!selCiudad.value) return;
        opciones(comuna, await getJSON("/api/comunas/?vigente=true&ciudad=" + selCiudad.value), sel, "Seleccione comuna…");
      }
      await cargarCiudades(ciudadId);
      if (ciudadId) await cargarComunas(actual);
      selRegion.addEventListener("change", async function () { await cargarCiudades(""); opciones(comuna, [], "", "Seleccione comuna…"); });
      selCiudad.addEventListener("change", function () { cargarComunas(""); });
    } catch (err) {
      fila.remove(); // si la API falla, queda el select completo de comunas
    }
  }

  // ------------------------------------------------------------------
  // Filtro rápido de tablas
  // ------------------------------------------------------------------
  function initFiltrosTabla() {
    document.querySelectorAll("[data-filtro-tabla]").forEach(function (input) {
      const tabla = document.querySelector(input.dataset.filtroTabla);
      input.addEventListener("input", function () {
        const q = input.value.toLowerCase();
        tabla.querySelectorAll("tbody tr").forEach(function (tr) {
          tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
        });
      });
    });
  }

  const clp = (n) => "$ " + Math.round(n).toLocaleString("es-CL");

  window.BuildCorp = {
    // Préstamo: responsables según contratista + cálculo de cobro estimado
    initPrestamo: function () {
      const selC = document.getElementById("id_contratista"), selR = document.getElementById("id_responsable");
      const fecha = document.getElementById("id_fecha_compromiso");
      async function cargarResponsables() {
        if (!selC.value) return opciones(selR, [], "");
        const actual = selR.value;
        const items = await getJSON("/api/responsables/?vigente=true&contratista=" + selC.value);
        opciones(selR, items.map((r) => ({ id: r.id, label: r.nombre + " (" + r.rut + ")" })), actual);
      }
      function recalcular() {
        const marcados = document.querySelectorAll(".chk-activo:checked");
        let tarifa = 0;
        marcados.forEach((c) => (tarifa += parseFloat(c.dataset.tarifa || 0)));
        let dias = 1;
        if (fecha.value) {
          const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
          dias = Math.max(1, Math.round((new Date(fecha.value + "T00:00:00") - hoy) / 86400000));
        }
        document.getElementById("sel-cantidad").textContent = marcados.length;
        document.getElementById("sel-tarifa").textContent = clp(tarifa);
        document.getElementById("sel-dias").textContent = dias;
        document.getElementById("sel-estimado").textContent = clp(tarifa * dias);
      }
      selC.addEventListener("change", cargarResponsables);
      fecha.addEventListener("change", recalcular);
      document.querySelectorAll(".chk-activo").forEach((c) => c.addEventListener("change", recalcular));
      if (selC.value) cargarResponsables();
      recalcular();
    },

    // Dashboard: refresco asíncrono de KPIs
    refrescarDashboard: function (url) {
      async function tick() {
        try {
          const r = await fetch(url, { credentials: "same-origin" });
          if (!r.ok) return;
          const d = await r.json();
          document.querySelectorAll("[data-kpi]").forEach((el) => {
            if (d[el.dataset.kpi] !== undefined) el.textContent = d[el.dataset.kpi];
          });
          document.querySelectorAll("[data-kpi-estado]").forEach((el) => {
            el.textContent = d.activos_por_estado[el.dataset.kpiEstado] || 0;
          });
        } catch (e) { /* sin conexión: se mantiene el último valor */ }
      }
      setInterval(tick, 60000);
    },
  };

  document.addEventListener("DOMContentLoaded", function () {
    initFirmas();
    initTerritorio();
    initFiltrosTabla();
  });
})();
