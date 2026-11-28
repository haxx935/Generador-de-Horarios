const API_BASE = "http://127.0.0.1:5000";

const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"];
const BLOQUES = [
  { etiqueta: "07-08", ini: 7, fin: 8 },
  { etiqueta: "08-09", ini: 8, fin: 9 },
  { etiqueta: "09-10", ini: 9, fin: 10 },
  { etiqueta: "10-11", ini: 10, fin: 11 },
  { etiqueta: "11-12", ini: 11, fin: 12 },
  { etiqueta: "12-13", ini: 12, fin: 13 },
  { etiqueta: "13-14", ini: 13, fin: 14 },
  { etiqueta: "14-15", ini: 14, fin: 15 },
  { etiqueta: "15-16", ini: 15, fin: 16 },
  { etiqueta: "16-17", ini: 16, fin: 17 },
  { etiqueta: "17-18", ini: 17, fin: 18 },
];

let datosConfig = { maestros: [], grupos: [], aulas: [] };
let horarioGenerado = [];
let grupoEditandoIdx = null;
let fetchController = null;
let sesionActual = null;
let generadorIniciado = false;

// ---------- Datos por defecto ----------
function cargarDatosPorDefecto() {
  datosConfig.maestros = [
    { nombre: "Prof. Matemáticas", materias: ["Matemáticas"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Matemáticas": "proyector" } },
    { nombre: "Prof. Física", materias: ["Física"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Física": "proyector" } },
    { nombre: "Prof. Química", materias: ["Química"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Química": "proyector" } },
    { nombre: "Prof. Programación", materias: ["Programación"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Programación": "computadoras" } },
    { nombre: "Prof. Redes", materias: ["Redes"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Redes": "computadoras" } },
    { nombre: "Prof. Historia", materias: ["Historia"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Historia": "proyector" } },
    { nombre: "Prof. Inglés", materias: ["Inglés"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Inglés": "proyector" } },
    { nombre: "Prof. Biología", materias: ["Biología"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Biología": "proyector" } },
    { nombre: "Prof. Literatura", materias: ["Literatura"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Literatura": "proyector" } },
    { nombre: "Prof. Filosofía", materias: ["Filosofía"], disponibilidad: { entrada: "08:00", salida: "16:00" }, equipo_requerido: { "Filosofía": "proyector" } },
  ];

  datosConfig.grupos = [
    { nombre: "Grupo A", materias: ["Matemáticas", "Física", "Química", "Historia", "Inglés"], equipo_requerido: { "Matemáticas": "proyector", "Física": "proyector", "Química": "proyector", "Historia": "proyector", "Inglés": "proyector" } },
    { nombre: "Grupo B", materias: ["Programación", "Redes", "Biología", "Literatura", "Filosofía"], equipo_requerido: { "Programación": "computadoras", "Redes": "computadoras", "Biología": "proyector", "Literatura": "proyector", "Filosofía": "proyector" } },
  ];

  datosConfig.aulas = [
    { nombre: "Aula 101", tipo: "salón", capacidad: 30, equipo: "proyector", materias_util: ["Matemáticas", "Física", "Química", "Historia", "Inglés", "Biología", "Literatura", "Filosofía"] },
    { nombre: "Lab 201", tipo: "laboratorio de computo", capacidad: 20, equipo: "computadoras", materias_util: ["Programación", "Redes"] },
  ];
}

// ---------- Utilidades ----------
const EQUIPO_POR_MATERIA_DEFECTO = {
  programación: "computadoras",
  programacion: "computadoras",
  redes: "computadoras",
  contabilidad: "computadoras",
};
function equipoPorDefecto(materia) { return EQUIPO_POR_MATERIA_DEFECTO[materia.toLowerCase()] || "proyector"; }
function capitalize(t) { if (!t) return ""; return t.charAt(0).toUpperCase() + t.slice(1); }
function esc(t) { return String(t ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function formatoDia(d) {
  const m = { lunes: "Lunes", martes: "Martes", miercoles: "Miércoles", jueves: "Jueves", viernes: "Viernes" };
  return m[d] || capitalize(d);
}

// ---------- Render listas ----------
function renderListas() {
  const render = (id, items, plantilla, onDel, onEdit) => {
    const el = document.getElementById(id);
    el.innerHTML = items.map((it, i) => {
      const editarBtn = onEdit ? `<button class="btn-editar" data-i="${i}" title="Editar">✎</button>` : "";
      return `<li><span>${plantilla(it)}</span><div class="acciones-lista">${editarBtn}<button class="btn-eliminar" data-i="${i}" title="Eliminar">&times;</button></div></li>`;
    }).join("");
    el.querySelectorAll(".btn-eliminar").forEach(b => b.addEventListener("click", () => { onDel(parseInt(b.dataset.i, 10)); }));
    if (onEdit) {
      el.querySelectorAll(".btn-editar").forEach(b => b.addEventListener("click", () => { onEdit(parseInt(b.dataset.i, 10)); }));
    }
  };

  render("lista-maestros", datosConfig.maestros,
    m => `<strong>${capitalize(m.nombre)}</strong> - ${(m.materias||[]).join(", ")} (${m.disponibilidad.entrada} a ${m.disponibilidad.salida})`,
    i => { datosConfig.maestros.splice(i,1); actualizarChecks(); renderListas(); });

  render("lista-grupos", datosConfig.grupos,
    g => `<strong>${g.nombre}</strong> - ${(g.materias||[]).join(", ")}`,
    i => { datosConfig.grupos.splice(i,1); renderListas(); },
    i => { abrirEdicionGrupo(i); }
  );

  render("lista-aulas", datosConfig.aulas,
    a => `<strong>${a.nombre}</strong> (${a.tipo}) - ${(a.materias_util||[]).join(", ")}`,
    i => { datosConfig.aulas.splice(i,1); renderListas(); });

  document.getElementById("select-maestro").innerHTML = '<option value="">-- Maestro --</option>' + datosConfig.maestros.map(m => `<option value="${m.nombre}">${capitalize(m.nombre)}</option>`).join("");
  document.getElementById("select-grupo").innerHTML = '<option value="">-- Grupo --</option>' + datosConfig.grupos.map(g => `<option value="${g.nombre}">${g.nombre}</option>`).join("");
}

function actualizarChecks() {
  const materias = Array.from(new Set(datosConfig.maestros.flatMap(m => m.materias||[])));
  const chk = (mat, c) => `<label class="checkbox-item"><input type="checkbox" value="${mat}" ${c?"checked":""}> ${capitalize(mat)}</label>`;
  document.getElementById("checkboxes-materias-grupo").innerHTML = materias.map(m => chk(m, false)).join("");
  document.getElementById("checkboxes-materias-aula").innerHTML = materias.map(m => chk(m, false)).join("");
}

// ---------- Edición de grupo ----------
function abrirEdicionGrupo(idx) {
  const grupo = datosConfig.grupos[idx];
  grupoEditandoIdx = idx;
  const modal = document.getElementById("modal-edicion-grupo");
  const cont = document.getElementById("checkboxes-edicion-grupo");
  const titulo = document.getElementById("titulo-edicion-grupo");
  const materias = Array.from(new Set(datosConfig.maestros.flatMap(m => m.materias||[])));

  titulo.textContent = `Editar materias de ${grupo.nombre}`;
  cont.innerHTML = materias.map(m => {
    const esta = (grupo.materias||[]).includes(m);
    return `<label class="checkbox-item"><input type="checkbox" value="${m}" ${esta?"checked":""}> ${capitalize(m)}</label>`;
  }).join("");

  modal.classList.add("visible");
  modal.hidden = false;
  modal.setAttribute("aria-hidden", "false");
}

function cerrarEdicionGrupo() {
  const modal = document.getElementById("modal-edicion-grupo");
  modal.classList.remove("visible");
  modal.hidden = true;
  modal.setAttribute("aria-hidden", "true");
  grupoEditandoIdx = null;
}

function guardarEdicionGrupo() {
  if (grupoEditandoIdx === null) return;
  const checks = document.querySelectorAll("#checkboxes-edicion-grupo input:checked");
  const nuevasMaterias = Array.from(checks).map(c => c.value);
  if (nuevasMaterias.length === 0) {
    alert("Selecciona al menos una materia.");
    return;
  }
  datosConfig.grupos[grupoEditandoIdx].materias = nuevasMaterias;
  const equipoPrevio = datosConfig.grupos[grupoEditandoIdx].equipo_requerido || {};
  const nuevoEquipo = {};
  nuevasMaterias.forEach(m => {
    const prev = equipoPrevio[m];
    nuevoEquipo[m] = (typeof prev === "string" && prev.trim()) ? prev.trim() : equipoPorDefecto(m);
  });
  datosConfig.grupos[grupoEditandoIdx].equipo_requerido = nuevoEquipo;
  cerrarEdicionGrupo();
  renderListas();
  actualizarChecks();
}

// ---------- Formularios ----------
function setupForms() {
  document.getElementById("btn-agregar-maestro").onclick = () => {
    const form = document.getElementById("input-m-nombre");
    if (!form.checkValidity()) { form.reportValidity(); return; }
    const n = document.getElementById("input-m-nombre").value.trim();
    const mat = document.getElementById("input-m-materias").value.trim();
    const e = document.getElementById("input-m-entrada").value;
    const s = document.getElementById("input-m-salida").value;
    if (!n || !mat || !e || !s) {
      document.getElementById("error-maestro").textContent = "Completa todos los campos.";
      return;
    }
    document.getElementById("error-maestro").textContent = "";
    datosConfig.maestros.push({ nombre: n, materias: mat.split(",").map(x=>x.trim()).filter(Boolean), disponibilidad: { entrada: e, salida: s } });
    document.getElementById("input-m-nombre").value = "";
    document.getElementById("input-m-materias").value = "";
    document.getElementById("input-m-entrada").value = "";
    document.getElementById("input-m-salida").value = "";
    actualizarChecks(); renderListas();
  };
  document.getElementById("btn-agregar-grupo").onclick = () => {
    const n = document.getElementById("input-g-nombre").value.trim();
    const mats = Array.from(document.querySelectorAll("#checkboxes-materias-grupo input:checked")).map(c=>c.value);
    if (!n) {
      document.getElementById("error-grupo").textContent = "Ingresa un nombre.";
      return;
    }
    if (mats.length === 0) {
      document.getElementById("error-grupo").textContent = "Selecciona al menos una materia.";
      return;
    }
    document.getElementById("error-grupo").textContent = "";
    datosConfig.grupos.push({ nombre: n, materias: mats });
    document.getElementById("input-g-nombre").value = "";
    document.querySelectorAll("#checkboxes-materias-grupo input").forEach(c=>c.checked=false);
    renderListas();
  };
  document.getElementById("btn-agregar-aula").onclick = () => {
    const n = document.getElementById("input-a-nombre").value.trim();
    const t = document.getElementById("input-a-tipo").value;
    const mats = Array.from(document.querySelectorAll("#checkboxes-materias-aula input:checked")).map(c=>c.value);
    if (!n) {
      document.getElementById("error-aula").textContent = "Ingresa un nombre.";
      return;
    }
    if (!t) {
      document.getElementById("error-aula").textContent = "Selecciona un tipo.";
      return;
    }
    if (mats.length === 0) {
      document.getElementById("error-aula").textContent = "Selecciona al menos una materia útil.";
      return;
    }
    document.getElementById("error-aula").textContent = "";
    datosConfig.aulas.push({ nombre: n, tipo: t, materias_util: mats });
    document.getElementById("input-a-nombre").value = "";
    document.getElementById("input-a-tipo").value = "";
    document.querySelectorAll("#checkboxes-materias-aula input").forEach(c=>c.checked=false);
    renderListas();
  };

  document.getElementById("btn-cerrar-edicion-grupo").onclick = cerrarEdicionGrupo;
  document.getElementById("btn-cancelar-edicion-grupo").onclick = cerrarEdicionGrupo;
  document.getElementById("btn-guardar-edicion-grupo").onclick = guardarEdicionGrupo;

  document.getElementById("modal-edicion-grupo").onclick = (e) => {
    if (e.target.id === "modal-edicion-grupo") cerrarEdicionGrupo();
  };

  document.getElementById("btn-exportar-csv").onclick = exportarCSV;
}

// ---------- Generar ----------
async function generarHorario() {
  if (fetchController) fetchController.abort();
  fetchController = new AbortController();
  const senal = fetchController.signal;

  const btn = document.getElementById("btn-generar");
  btn.disabled = true; btn.textContent = "Generando...";
  const estado = document.getElementById("estado");
  estado.textContent = "Consultando backend..."; estado.className = "estado cargando";
  try {
    // llamadaApi adjunta la sesión (cookie en Flask, Bearer con file:// o
    // Live Server) y convierte errores como 401/403 en mensajes claros.
    const data = await llamadaApi("/generar-horario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datosConfig),
      signal: senal
    });
    horarioGenerado = data.asignaciones || [];
    console.log("Horario:", horarioGenerado);
    if (horarioGenerado.length === 0) throw new Error("No se generaron asignaciones.");
    document.getElementById("resumen").textContent = `Se generaron ${horarioGenerado.length} clases.`;
    document.getElementById("panel-resultado").hidden = false;
    estado.textContent = "Horario generado."; estado.className = "estado exito";
    document.getElementById("btn-exportar-csv").disabled = false;

    setupTabs();

    if (datosConfig.maestros.length > 0) {
      document.getElementById("select-maestro").value = datosConfig.maestros[0].nombre;
      renderVistaMaestro(datosConfig.maestros[0].nombre);
    }
    if (datosConfig.grupos.length > 0) {
      document.getElementById("select-grupo").value = datosConfig.grupos[0].nombre;
      renderReticulaGrupo(datosConfig.grupos[0].nombre);
    }
    document.getElementById("panel-resultado").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    if (err.name === "AbortError") return;
    estado.textContent = err.message; estado.className = "estado error";
    console.error(err);
  } finally {
    btn.disabled = false; btn.textContent = "Generar Horario";
    fetchController = null;
  }
}

function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach(b => b.replaceWith(b.cloneNode(true)));
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach(x=>x.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach(c=>c.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
    });
  });
  document.getElementById("select-maestro").onchange = () => renderVistaMaestro(document.getElementById("select-maestro").value);
  document.getElementById("select-grupo").onchange = () => renderReticulaGrupo(document.getElementById("select-grupo").value);
}

// ---------- Vistas ----------
function construirTablaClases(clases) {
  let html = `<table><thead><tr><th>Grupo</th><th>Materia</th><th>Aula</th><th>Día</th><th>Hora</th></tr></thead><tbody>`;
  clases.forEach(c => {
    html += `<tr><td>${esc(c.grupo)}</td><td>${esc(capitalize(c.materia))}</td><td>${esc(c.aula)}</td>` +
            `<td>${esc(formatoDia(c.dia))}</td><td>${esc(c.bloque || c.hora_inicio)}</td></tr>`;
  });
  return html + "</tbody></table>";
}

function construirReticula(clases) {
  const matriz = {};
  DIAS.forEach(d => { matriz[d] = {}; BLOQUES.forEach(b => matriz[d][b.etiqueta] = null); });
  clases.forEach(c => { const bl = c.bloque || c.hora_inicio; if (matriz[c.dia] && matriz[c.dia][bl] === null) matriz[c.dia][bl] = c; });
  let html = `<table><thead><tr><th>Hora \\ Día</th>${DIAS.map(d => `<th>${formatoDia(d)}</th>`).join("")}</tr></thead><tbody>`;
  BLOQUES.forEach(b => {
    html += `<tr><th>${b.etiqueta}</th>`;
    DIAS.forEach(d => {
      const c = matriz[d][b.etiqueta];
      if (c) html += `<td><div class="clase"><strong>${esc(capitalize(c.materia))}</strong><small>${esc(capitalize(c.maestro))}</small><small>${esc(c.aula)}</small></div></td>`;
      else html += `<td class="empty">-</td>`;
    });
    html += `</tr>`;
  });
  return html + "</tbody></table>";
}

function renderVistaMaestro(nombre) {
  const cont = document.getElementById("contenedor-tabla-maestro");
  cont.innerHTML = "";
  if (!nombre) { cont.innerHTML = '<p class="texto-suave">Selecciona un maestro.</p>'; return; }
  const clases = horarioGenerado.filter(c => c.maestro === nombre);
  if (clases.length === 0) { cont.innerHTML = `<p class="texto-suave">${esc(capitalize(nombre))} no tiene clases.</p>`; return; }
  cont.innerHTML = construirTablaClases(clases);
}

function renderReticulaGrupo(nombre) {
  const cont = document.getElementById("contenedor-reticula-grupo");
  cont.innerHTML = "";
  if (!nombre) { cont.innerHTML = '<p class="texto-suave">Selecciona un grupo.</p>'; return; }
  const clases = horarioGenerado.filter(c => c.grupo === nombre);
  if (clases.length === 0) { cont.innerHTML = `<p class="texto-suave">${esc(nombre)} no tiene clases.</p>`; return; }
  cont.innerHTML = construirReticula(clases);
}

function limpiarTodo() {
  datosConfig = { maestros: [], grupos: [], aulas: [] };
  horarioGenerado = [];
  renderListas();
  document.getElementById("panel-resultado").hidden = true;
  document.getElementById("contenedor-tabla-maestro").innerHTML = "";
  document.getElementById("contenedor-reticula-grupo").innerHTML = "";
  document.getElementById("resumen").textContent = "";
  document.getElementById("estado").textContent = "";
  document.getElementById("estado").className = "estado";
  document.getElementById("select-maestro").innerHTML = '<option value="">-- Maestro --</option>';
  document.getElementById("select-grupo").innerHTML = '<option value="">-- Grupo --</option>';
  document.getElementById("btn-exportar-csv").disabled = true;
}

function exportarCSV() {
  if (horarioGenerado.length === 0) return;
  const cabeceras = ["Grupo", "Materia", "Maestro", "Aula", "Día", "Hora"];
  const filas = horarioGenerado.map(c => [
    c.grupo || "",
    capitalize(c.materia),
    capitalize(c.maestro),
    c.aula || "",
    formatoDia(c.dia),
    c.bloque || c.hora_inicio || ""
  ]);
  const csvContent = [cabeceras, ...filas]
    .map(fila => fila.map(valor => `"${String(valor).replace(/"/g, '""')}"`).join(","))
    .join("\n");
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = "horario.csv";
  enlace.style.display = "none";
  document.body.appendChild(enlace);
  enlace.click();
  document.body.removeChild(enlace);
  URL.revokeObjectURL(url);
}

// ---------- Sesión, enrutamiento por roles y portales ----------
const RUTAS_POR_ROL = { jefe: "/jefe", maestro: "/maestro", alumno: "/alumno" };
const ETIQUETAS_ROL = { jefe: "Jefe de Área", maestro: "Maestro", alumno: "Alumno" };

function tokenSesion() {
  return sessionStorage.getItem("sid") || "";
}

function cerrarSesionLocal() {
  sessionStorage.removeItem("sid");
  sesionActual = null;
  mostrarPortal(null);
  if (esBackend()) location.assign("/");
  else location.hash = "#/login";
}

async function llamadaApi(ruta, opciones = {}) {
  const headers = { ...(opciones.headers || {}) };
  const token = tokenSesion();
  // En Flask (puerto 5000) la cookie HttpOnly es la fuente de la sesión:
  // enviar el token de sessionStorage de otra pestaña podría contradecirla.
  // Con file:// o Live Server no hay cookie y se envía el token como Bearer.
  if (token && !esBackend()) headers["Authorization"] = `Bearer ${token}`;
  const respuesta = await fetch(`${API_BASE}${ruta}`, { ...opciones, headers, credentials: "include" });
  let datos = {};
  try { datos = await respuesta.json(); } catch (_) { datos = {}; }
  if (!respuesta.ok) {
    // Un token vencido (por ejemplo, tras reiniciar el backend) debe llevar
    // al login, no dejar al usuario en un portal que ya no puede usar.
    if (respuesta.status === 401 && ruta !== "/api/login" && ruta !== "/api/login-demo") {
      cerrarSesionLocal();
    }
    const error = new Error(datos.error || `HTTP ${respuesta.status}`);
    error.estado = respuesta.status;
    throw error;
  }
  return datos;
}

function esBackend() {
  // Sólo el servidor Flask (puerto 5000) conoce las rutas /jefe, /maestro, /alumno.
  // Con file:// o Live Server (5500) se debe usar el hash como "ruta".
  const puerto = String(location.port || (location.protocol === "https:" ? "443" : "80"));
  return ["127.0.0.1", "localhost"].includes(location.hostname) && puerto === "5000";
}

function rolDeRuta() {
  if (esBackend()) {
    const parte = location.pathname.replace(/\/+$/, "").split("/").pop();
    return ["jefe", "maestro", "alumno"].includes(parte) ? parte : null;
  }
  const coincidencia = location.hash.match(/^#\/(jefe|maestro|alumno)$/);
  return coincidencia ? coincidencia[1] : null;
}

function navegarAlPortal(rol) {
  if (!RUTAS_POR_ROL[rol]) return;
  if (esBackend()) {
    // El backend valida la cookie de sesión antes de servir /<rol>.
    location.assign(RUTAS_POR_ROL[rol]);
  } else {
    // file:// u otro servidor estático: el backend NO sirve estas rutas.
    location.hash = `#/${rol}`;
    if (sesionActual && sesionActual.rol === rol) mostrarPortal(rol);
  }
}

async function obtenerSesion() {
  try {
    const datos = await llamadaApi("/api/session");
    return datos.autenticado ? datos.usuario : null;
  } catch (_) {
    return null;
  }
}

function iniciarGenerador() {
  if (generadorIniciado) return;
  generadorIniciado = true;
  cargarDatosPorDefecto();
  renderListas();
  setupForms();
  actualizarChecks();
}

function perfilMaestro(usuario) {
  const materias = (usuario.materias || []).map(esc).join(", ") || "No registradas";
  return `<div class="perfil-card"><p><strong>Usuario:</strong> ${esc(usuario.usuario)}</p>` +
         `<p><strong>Nombre:</strong> ${esc(usuario.nombre)}</p>` +
         `<p><strong>Materias que imparte:</strong> ${materias}</p></div>`;
}

function perfilAlumno(usuario) {
  return `<div class="perfil-card"><p><strong>Usuario:</strong> ${esc(usuario.usuario)}</p>` +
         `<p><strong>Nombre:</strong> ${esc(usuario.nombre)}</p>` +
         `<p><strong>Semestre:</strong> ${esc(usuario.semestre)}</p>` +
         `<p><strong>Grupo:</strong> ${esc(usuario.grupo)}</p></div>`;
}

function kardexHTML(usuario) {
  const aprobadas = (usuario.materias_aprobadas || []).map(m => `<li>${esc(m)}</li>`).join("");
  const kardex = (usuario.kardex || []).map(fila =>
    `<tr><td>${esc(fila.materia)}</td><td>${esc(fila.calificacion)}</td><td>${esc(fila.semestre)}</td></tr>`
  ).join("");
  return `<div class="kardex"><h3>Kardex</h3>` +
         `<p><strong>Materias aprobadas:</strong></p><ul class="lista-materias">${aprobadas || "<li>Ninguna</li>"}</ul>` +
         `<table><thead><tr><th>Materia</th><th>Calificación</th><th>Semestre</th></tr></thead><tbody>${kardex}</tbody></table></div>`;
}

async function cargarMiHorario(rol) {
  const estado = document.getElementById(`${rol}-estado`);
  estado.textContent = "Cargando horario...";
  estado.className = "estado cargando";
  try {
    const datos = await llamadaApi("/api/horario");
    const contenedor = document.getElementById(`${rol}-horario`);
    if (rol === "maestro") {
      document.getElementById("maestro-perfil").innerHTML = perfilMaestro(datos.usuario);
      contenedor.innerHTML = datos.total > 0
        ? construirTablaClases(datos.asignaciones)
        : '<p class="texto-suave">Aún no hay clases para ti. El Jefe de Área debe generar el horario.</p>';
    } else {
      document.getElementById("alumno-perfil").innerHTML = perfilAlumno(datos.usuario);
      document.getElementById("alumno-kardex").innerHTML = kardexHTML(datos.usuario);
      contenedor.innerHTML = datos.total > 0
        ? construirReticula(datos.asignaciones)
        : '<p class="texto-suave">Aún no hay horario generado para tu grupo.</p>';
    }
    estado.textContent = `${datos.total} clase(s) encontradas.`;
    estado.className = "estado exito";
  } catch (err) {
    estado.textContent = err.message;
    estado.className = "estado error";
  }
}

function mostrarPortal(rol) {
  const portalVisible = rol || "login";
  ["login", "jefe", "maestro", "alumno"].forEach(nombre => {
    const elemento = document.getElementById(`portal-${nombre}`);
    if (elemento) elemento.hidden = nombre !== portalVisible;
  });
  const barra = document.getElementById("barra-sesion");
  barra.hidden = !rol;
  if (!rol) return;

  document.getElementById("sesion-nombre").textContent = sesionActual.nombre || sesionActual.usuario || "";
  const insignia = document.getElementById("sesion-rol");
  insignia.textContent = ETIQUETAS_ROL[rol] || rol;
  insignia.dataset.rol = rol;

  if (rol === "jefe") iniciarGenerador();
  if (rol === "maestro") cargarMiHorario("maestro");
  if (rol === "alumno") cargarMiHorario("alumno");
}

async function iniciarAplicacion() {
  sesionActual = await obtenerSesion();
  if (!sesionActual) {
    sesionActual = null;
    sessionStorage.removeItem("sid");
    mostrarPortal(null);
    document.getElementById("login-usuario").focus();
    return;
  }

  const solicitado = rolDeRuta();
  if (solicitado && solicitado !== sesionActual.rol) {
    // Un rol no puede entrar directamente a la vista de otro.
    navegarAlPortal(sesionActual.rol);
    return;
  }
  if (!solicitado) {
    if (esBackend()) { navegarAlPortal(sesionActual.rol); return; }
    location.hash = `#/${sesionActual.rol}`;
    mostrarPortal(sesionActual.rol);
    return;
  }
  mostrarPortal(sesionActual.rol);
}

function configurarAutenticacion() {
  document.getElementById("form-login").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const error = document.getElementById("login-error");
    error.textContent = "";
    const boton = document.getElementById("btn-login");
    boton.disabled = true;
    boton.textContent = "Ingresando...";
    try {
      const datos = await llamadaApi("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          usuario: document.getElementById("login-usuario").value.trim(),
          contrasena: document.getElementById("login-contrasena").value
        })
      });
      sessionStorage.setItem("sid", datos.token);
      sesionActual = datos.usuario;
      navegarAlPortal(sesionActual.rol);
    } catch (err) {
      error.textContent = err.message;
    } finally {
      boton.disabled = false;
      boton.textContent = "Ingresar";
    }
  });

  document.querySelectorAll("[data-demo-rol]").forEach(boton => {
    boton.addEventListener("click", async () => {
      const error = document.getElementById("login-error");
      error.textContent = "";
      boton.disabled = true;
      try {
        const datos = await llamadaApi("/api/login-demo", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ rol: boton.dataset.demoRol })
        });
        sessionStorage.setItem("sid", datos.token);
        sesionActual = datos.usuario;
        navegarAlPortal(sesionActual.rol);
      } catch (err) {
        error.textContent = err.message;
      } finally {
        boton.disabled = false;
      }
    });
  });

  document.getElementById("btn-logout").addEventListener("click", async () => {
    try { await llamadaApi("/api/logout", { method: "POST" }); } catch (_) { /* la sesión ya expiró */ }
    cerrarSesionLocal();
  });

  document.getElementById("btn-recargar-maestro").addEventListener("click", () => cargarMiHorario("maestro"));
  document.getElementById("btn-recargar-alumno").addEventListener("click", () => cargarMiHorario("alumno"));
  window.addEventListener("hashchange", () => {
    if (!sesionActual) return;
    const rol = rolDeRuta();
    if (rol === sesionActual.rol) mostrarPortal(rol);
    else navegarAlPortal(sesionActual.rol);
  });
}

// ---------- Init ----------
document.getElementById("btn-generar").addEventListener("click", generarHorario);
document.getElementById("btn-limpiar").addEventListener("click", limpiarTodo);
document.addEventListener("keydown", (e) => { if (e.key === "Escape") cerrarEdicionGrupo(); });
configurarAutenticacion();
iniciarAplicacion();
