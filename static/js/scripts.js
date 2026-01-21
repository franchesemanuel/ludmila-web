/*!
* Start Bootstrap - Grayscale v7.0.6 (https://startbootstrap.com/theme/grayscale)
* Copyright 2013-2023 Start Bootstrap
* Licensed under MIT (https://github.com/StartBootstrap/startbootstrap-grayscale/blob/master/LICENSE)
*/
//
// Scripts
// 

window.addEventListener('DOMContentLoaded', event => {

    // Navbar shrink function
    var navbarShrink = function () {
        const navbarCollapsible = document.body.querySelector('#mainNav');
        if (!navbarCollapsible) {
            return;
        }
        if (window.scrollY === 0) {
            navbarCollapsible.classList.remove('navbar-shrink')
        } else {
            navbarCollapsible.classList.add('navbar-shrink')
        }

    };

    // Shrink the navbar 
    navbarShrink();

    // Shrink the navbar when page is scrolled
    document.addEventListener('scroll', navbarShrink);

    // Activate Bootstrap scrollspy on the main nav element
    const mainNav = document.body.querySelector('#mainNav');
    if (mainNav) {
        new bootstrap.ScrollSpy(document.body, {
            target: '#mainNav',
            rootMargin: '0px 0px -40%',
        });
    };

    // Collapse responsive navbar when toggler is visible
    const navbarToggler = document.body.querySelector('.navbar-toggler');
    const responsiveNavItems = [].slice.call(
        document.querySelectorAll('#navbarResponsive .nav-link')
    );
    responsiveNavItems.map(function (responsiveNavItem) {
        responsiveNavItem.addEventListener('click', () => {
            if (window.getComputedStyle(navbarToggler).display !== 'none') {
                navbarToggler.click();
            }
        });
    });

});

document.addEventListener("DOMContentLoaded", function () {
    const fechaInput = document.getElementById("fecha");
    const horaSelect = document.getElementById("hora");

    fechaInput.addEventListener("change", function () {
        const fecha = this.value;
        horaSelect.innerHTML = "<option>Cargando...</option>";

        fetch(`/reservar/horas-disponibles/?fecha=${fecha}`)
            .then(response => response.json())
            .then(data => {
                horaSelect.innerHTML = "";

                if (data.horas.length === 0) {
                    horaSelect.innerHTML = "<option>No hay horarios disponibles</option>";
                } else {
                    data.horas.forEach(hora => {
                        const option = document.createElement("option");
                        option.value = hora;
                        option.textContent = hora;
                        horaSelect.appendChild(option);
                    });
                }
            });
    });
});

document.addEventListener("DOMContentLoaded", function () {
  const fechaInput = document.getElementById("fecha");
  const horaSelect = document.getElementById("hora");

  if (!fechaInput || !horaSelect) return;

  fechaInput.addEventListener("change", async function () {
    const fecha = this.value;

    horaSelect.innerHTML = `<option value="">Cargando...</option>`;
    horaSelect.disabled = true;

    try {
      const resp = await fetch(`/reservar/horas-disponibles/?fecha=${fecha}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      const data = await resp.json();

      horaSelect.innerHTML = "";

      if (!data.horas || data.horas.length === 0) {
        horaSelect.innerHTML = `<option value="">No hay horarios disponibles</option>`;
        horaSelect.disabled = true;
        return;
      }

      horaSelect.insertAdjacentHTML(
        "beforeend",
        `<option value="">Seleccioná una hora</option>`
      );

      data.horas.forEach((h) => {
        horaSelect.insertAdjacentHTML(
          "beforeend",
          `<option value="${h}">${h}</option>`
        );
      });

      horaSelect.disabled = false;
    } catch (e) {
      horaSelect.innerHTML = `<option value="">Error cargando horarios</option>`;
      horaSelect.disabled = true;
      console.error(e);
    }
  });
});

