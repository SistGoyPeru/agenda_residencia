(function () {
  "use strict";

  var MAPA_CUPONES = {};

  document.addEventListener("DOMContentLoaded", function () {
    leerMapaCupones();
    iniciarFormset();
    iniciarCuponesAuto();
    iniciarConfirmaciones();
    esfumarAvisos();
  });

  function leerMapaCupones() {
    var datos = document.getElementById("datos-cupones");
    if (!datos) return;
    try {
      MAPA_CUPONES = JSON.parse(datos.textContent) || {};
    } catch (error) {
      MAPA_CUPONES = {};
    }
  }

  function iniciarFormset() {
    var contenedor = document.getElementById("filas-formset");
    var plantilla = document.getElementById("plantilla-fila");
    var boton = document.getElementById("anadir-fila");
    var total = document.querySelector('input[name$="-TOTAL_FORMS"]');
    if (!contenedor || !plantilla || !boton || !total) return;

    boton.addEventListener("click", function () {
      var indice = parseInt(total.value, 10) || 0;
      var html = plantilla.innerHTML.replace(/__prefix__/g, indice);
      var envoltorio = document.createElement("div");
      envoltorio.innerHTML = html.trim();
      var fila = envoltorio.firstElementChild;
      if (!fila) return;
      contenedor.appendChild(fila);
      total.value = indice + 1;
      conectarFila(fila);
      var select = fila.querySelector("select");
      if (select) select.focus();
    });

    contenedor.querySelectorAll(".fila-formset").forEach(conectarFila);
  }

  function conectarFila(fila) {
    var borrar = fila.querySelector(".borrar-fila");
    if (borrar) {
      borrar.addEventListener("click", function () {
        var casilla = fila.querySelector('input[name$="-DELETE"]');
        if (casilla) {
          casilla.checked = true;
          fila.classList.add("oculto");
        } else {
          fila.remove();
        }
      });
    }
    actualizarCupones(fila);
  }

  function iniciarCuponesAuto() {
    var contenedor = document.getElementById("filas-formset");
    if (!contenedor) return;
    contenedor.addEventListener("change", function (evento) {
      var fila = evento.target.closest(".fila-formset");
      if (!fila) return;
      if (
        evento.target.classList.contains("campo-producto") ||
        evento.target.classList.contains("campo-cantidad")
      ) {
        actualizarCupones(fila);
      }
    });
    contenedor.addEventListener("input", function (evento) {
      if (evento.target.classList.contains("campo-cupones")) {
        evento.target.dataset.tocado = "1";
      }
    });
  }

  function actualizarCupones(fila) {
    var producto = fila.querySelector(".campo-producto");
    var cantidad = fila.querySelector(".campo-cantidad");
    var cupones = fila.querySelector(".campo-cupones");
    if (!producto || !cantidad || !cupones) return;
    if (cupones.dataset.tocado === "1") return;
    var ratio = parseFloat(MAPA_CUPONES[producto.value] || "1");
    var unidades = parseInt(cantidad.value, 10);
    if (isNaN(unidades)) unidades = 1;
    cupones.value = Math.max(0, Math.round(unidades * ratio));
  }

  function iniciarConfirmaciones() {
    document.querySelectorAll("form.js-confirm").forEach(function (form) {
      form.addEventListener("submit", function (evento) {
        var mensaje =
          form.getAttribute("data-mensaje") || "¿Seguro que quieres continuar?";
        if (!window.confirm(mensaje)) {
          evento.preventDefault();
        }
      });
    });
  }

  function esfumarAvisos() {
    setTimeout(function () {
      document.querySelectorAll(".aviso-flash").forEach(function (aviso) {
        aviso.style.transition = "opacity .5s ease";
        aviso.style.opacity = "0";
        setTimeout(function () {
          aviso.remove();
        }, 500);
      });
    }, 4500);
  }
})();
