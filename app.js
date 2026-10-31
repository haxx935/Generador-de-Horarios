const API_BASE = "http://127.0.0.1:5000";

const DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes"];
const HORAS = ["h_8_10", "h_10_12", "h_12_14", "h_14_16", "h_16_18"];

// Referencias DOM
const btnGenerar = document.getElementById("btn-generar");
const btnLimpiar = document.getElementById("btn-limpiar");
const panelResultado = document.getElementById("panel-resultado");
const contenedorHorario = document.getElementById("contenedor-horario");
const resumenEl = document.getElementById("resumen");
const estadoEl = document.getElementById("estado");

// Estado en memoria (editable por el usuario)
let datosConfig = {
  profesores: [
    { nombre: "ana", materia: "fisica" },
    { nombre: "carlos", materia: "programacion" },
    { nombre: "sofia", materia: "matematicas" },
    { nombre: "miguel", materia: "bases_de_datos" },
  ],
  grupos: [
    { nombre: "grupo_a", alumnos: 25, materia: "fisica" },
    { nombre: "grupo_b", alumnos: 15, materia: "programacion" },
    { nombre: "grupo_c", alumnos: 30, materia: "matematicas" },
    { nombre: "grupo_d", alumnos: 20, materia: "bases_de_datos" },
  ],
  salones: [
    { nombre: "lab_1", capacidad: 20, equipo: "computadoras" },
    { nombre: "aula_101", capacidad: 40, equipo: "proyector" },
    { nombre: "aula_102", capacidad: 35, equipo: "proyector" },
    { nombre: "lab_2", capacidad: 25, equipo: "computadoras" },
  ],
  disponibilidades: [
    { profesor: "ana", dia: "lunes", hora: "h_8_10" },
    { profesor: "carlos", dia: "lunes", hora: "h_8_10" },
    { profesor: "sofia", dia: "martes", hora: "h_10_12" },
    { profesor: "miguel", dia: "miercoles", hora: "h_12_14" },
  ],
};

// ---------------------------------------------------------------------------
// Renderizado de listas
// ---------------------------------------------------------------------------

function renderListas() {
  const render = (id, items, plantilla, onEliminar) => {
    const el = document.getElementById(id);
    el.innerHTML = items.map((item, idx) => {
      return `<li>
        <span>${plantilla(item)}</span>
        <button type="button" class="btn-eliminar" data-idx="${idx}" title="Eliminar">&times;</button>
      </li>`;
    }).join("");

    // Delegaci�n de eventos para eliminar
    el.querySelectorAll(".btn-eliminar").forEach((btn) => {
      btn.addEventListener("click", () => {
        const i = parseInt(btn.dataset.idx, 10);
        onEliminar(i);
      });
    });
  };

  render(
    "lista-profesores",
    datosConfig.profesores,
    (p) => `<strong>${capitalize(p.nombre)}</strong> - ${p.materia}`,
    (i) => { datosConfig.profesores.splice(i, 1); renderListas(); }
  );

  render(
    "lista-grupos",
    datosConfig.grupos,
    (g) => `<strong>${g.nombre}</strong> (${g.alumnos} alumnos) - ${g.materia}`,
    (i) => { datosConfig.grupos.splice(i, 1); renderListas(); }
  );

  render(
    "lista-salones",
    datosConfig.salones,
    (s) => `<strong>${s.nombre}</strong> cap. ${s.capacidad} - ${s.equipo}`,
    (i) => { datosConfig.salones.splice(i, 1); renderListas(); }
  );

  render(
    "lista-disponibilidades",
    datosConfig.disponibilidades,
    (d) => `<strong>${capitalize(d.profesor)}</strong> - ${formatoDia(d.dia)} ${formatoHora(d.hora)}`,
    (i) => { datosConfig.disponibilidades.splice(i, 1); renderListas(); }
  );
}

// ---------------------------------------------------------------------------
// Manejo de formularios de agregar
// ---------------------------------------------------------------------------

function setupFormularios() {
  // Profesor
  document.getElementById("btn-agregar-profesor").addEventListener("click", () => {
    const nombre = document.getElementById("input-prof-nombre").value.trim();
    const materia = document.getElementById("input-prof-materia").value.trim();
    if (!nombre || !materia) return;
    datosConfig.profesores.push({ nombre, materia });
    document.getElementById("input-prof-nombre").value = "";
    document.getElementById("input-prof-materia").value = "";
    renderListas();
  });

  // Grupo
  document.getElementById("btn-agregar-grupo").addEventListener("click", () => {
    const nombre = document.getElementById("input-grupo-nombre").value.trim();
    const alumnos = parseInt(document.getElementById("input-grupo-alumnos").value, 10);
    const materia = document.getElementById("input-grupo-materia").value.trim();
    if (!nombre || !alumnos || !materia) return;
    datosConfig.grupos.push({ nombre, alumnos, materia });
    document.getElementById("input-grupo-nombre").value = "";
    document.getElementById("input-grupo-alumnos").value = "";
    document.getElementById("input-grupo-materia").value = "";
    renderListas();
  });

  // Salon
  document.getElementById("btn-agregar-salon").addEventListener("click", () => {
    const nombre = document.getElementById("input-salon-nombre").value.trim();
    const capacidad = parseInt(document.getElementById("input-salon-capacidad").value, 10);
    const equipo = document.getElementById("input-salon-equipo").value.trim();
    if (!nombre || !capacidad || !equipo) return;
    datosConfig.salones.push({ nombre, capacidad, equipo });
    document.getElementById("input-salon-nombre").value = "";
    document.getElementById("input-salon-capacidad").value = "";
    document.getElementById("input-salon-equipo").value = "";
    renderListas();
  });

  // Disponibilidad
  document.getElementById("btn-agregar-disp").addEventListener("click", () => {
    const profesor = document.getElementById("input-disp-profesor").value.trim();
    const dia = document.getElementById("input-disp-dia").value;
    const hora = document.getElementById("input-disp-hora").value;
    if (!profesor) return;
    datosConfig.disponibilidades.push({ profesor, dia, hora });
    document.getElementById("input-disp-profesor").value = "";
    renderListas();
  });
}

// ---------------------------------------------------------------------------
// Generaci�n de horario
// ---------------------------------------------------------------------------

async function generarHorario() {
  btnGenerar.disabled = true;
  btnGenerar.textContent = "Generando...";
  estadoEl.textContent = "Enviando configuraci�n al backend...";
  estadoEl.className = "estado cargando";

  try {
    const respuesta = await fetch(`${API_BASE}/generar-horario`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(datosConfig),
    });

    if (!respuesta.ok) {
      const errData = await respuesta.json().catch(() => ({}));
      throw new Error(errData.error || `Error ${respuesta.status}`);
    }

    const data = await respuesta.json();
    const horario = data.horario || [];

    if (!horario || horario.length === 0) {
      throw new Error("No se pudo generar un horario v\u00e1lido con las restricciones actuales.");
    }

    resumenEl.textContent = `Se generaron ${horario.length} clases para el horario acad�mico.`;
    renderizarTabla(horario);
    panelResultado.hidden = false;
    estadoEl.textContent = "Horario generado correctamente.";
    estadoEl.className = "estado exito";
    panelResultado.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    estadoEl.textContent = error.message;
    estadoEl.className = "estado error";
    console.error(error);
  } finally {
    btnGenerar.disabled = false;
    btnGenerar.textContent = "Generar Horario";
  }
}

// ---------------------------------------------------------------------------
// Renderizado de tabla
// ---------------------------------------------------------------------------

function renderizarTabla(horario) {
  const matriz = {};
  DIAS.forEach((dia) => {
    matriz[dia] = {};
    HORAS.forEach((hora) => {
      matriz[dia][hora] = null;
    });
  });

  horario.forEach((clase) => {
    const dia = clase.Dia || clase.dia;
    const hora = clase.Hora || clase.hora;
    if (matriz[dia] && matriz[dia][hora] === null) {
      matriz[dia][hora] = clase;
    }
  });

  let html = `<table>
    <thead>
      <tr>
        <th>D\u00eda \\ Hora</th>
        ${HORAS.map((h) => `<th>${formatoHora(h)}</th>`).join("")}
      </tr>
    </thead>
    <tbody>
  `;

  DIAS.forEach((dia) => {
    html += `<tr><th>${formatoDia(dia)}</th>`;
    HORAS.forEach((hora) => {
      const clase = matriz[dia][hora];
      if (clase) {
        const prof = clase.Prof || clase.profesor;
        const mat = clase.Materia || clase.materia;
        const grupo = clase.Grupo || clase.grupo;
        const salon = clase.Salon || clase.salon;
        html += `
          <td>
            <div class="clase">
              <strong>${capitalize(mat)}</strong>
              <small>${capitalize(prof)} &bull; ${grupo.replace(/_/g, " ").toUpperCase()}</small>
              <small>${salon.replace(/_/g, " ").toUpperCase()}</small>
            </div>
          </td>
        `;
      } else {
        html += `<td class="empty">-</td>`;
      }
    });
    html += `</tr>`;
  });

  html += `</tbody></table>`;
  contenedorHorario.innerHTML = html;
}

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

function formatoDia(dia) {
  const map = {
    lunes: "Lunes",
    martes: "Martes",
    miercoles: "Mi\u00e9rcoles",
    jueves: "Jueves",
    viernes: "Viernes",
  };
  return map[dia] || capitalize(dia);
}

function formatoHora(hora) {
  const map = {
    h_8_10: "08:00 - 10:00",
    h_10_12: "10:00 - 12:00",
    h_12_14: "12:00 - 14:00",
    h_14_16: "14:00 - 16:00",
    h_16_18: "16:00 - 18:00",
  };
  return map[hora] || hora;
}

function capitalize(texto) {
  if (!texto) return "";
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

// ---------------------------------------------------------------------------
// Eventos globales
// ---------------------------------------------------------------------------

btnGenerar.addEventListener("click", generarHorario);

btnLimpiar.addEventListener("click", () => {
  datosConfig = {
    profesores: [],
    grupos: [],
    salones: [],
    disponibilidades: [],
  };
  renderListas();
  panelResultado.hidden = true;
  contenedorHorario.innerHTML = "";
  resumenEl.textContent = "";
  estadoEl.textContent = "";
  estadoEl.className = "estado";
});

// ---------------------------------------------------------------------------
// Inicializaci�n
// ---------------------------------------------------------------------------

renderListas();
setupFormularios();
