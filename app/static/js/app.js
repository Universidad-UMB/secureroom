/**
 * SecureRoom v1 — Client UX Interactions
 * Handles confirmation modals, dynamic availability checks, and double-submit prevention.
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Prevent double submission on all forms
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", (e) => {
      const submitBtn = form.querySelector("button[type='submit']");
      if (submitBtn && !submitBtn.dataset.preventDisabled) {
        submitBtn.disabled = true;
        submitBtn.classList.add("opacity-75", "cursor-not-allowed");
        const originalText = submitBtn.innerText;
        submitBtn.innerText = "Procesando...";
      }
    });
  });

  // 2. Dynamic availability checker on /reservations/new
  const checkBtn = document.getElementById("btn-check-availability");
  if (checkBtn) {
    checkBtn.addEventListener("click", async () => {
      const roomSelect = document.getElementById("room_id");
      const startInput = document.getElementById("start_datetime");
      const endInput = document.getElementById("end_datetime");
      const resultBox = document.getElementById("availability-result");

      if (!roomSelect.value || !startInput.value || !endInput.value) {
        resultBox.className = "p-3 rounded-lg border border-amber-200 bg-amber-50 text-amber-800 text-sm";
        resultBox.innerText = "Por favor seleccione sala, fecha/hora de inicio y de fin.";
        resultBox.classList.remove("hidden");
        return;
      }

      checkBtn.disabled = true;
      checkBtn.innerText = "Comprobando...";

      try {
        const params = new URLSearchParams({
          room_id: roomSelect.value,
          start: new Date(startInput.value).toISOString(),
          end: new Date(endInput.value).toISOString(),
        });

        const response = await fetch(`/api/availability?${params.toString()}`);
        const data = await response.json();

        resultBox.classList.remove("hidden");
        if (data.available) {
          resultBox.className = "p-3 rounded-lg border border-emerald-200 bg-emerald-50 text-emerald-800 text-sm";
          resultBox.innerHTML = "✓ <strong>Disponible:</strong> La sala se encuentra libre en el horario especificado.";
        } else {
          resultBox.className = "p-3 rounded-lg border border-rose-200 bg-rose-50 text-rose-800 text-sm";
          resultBox.innerHTML = "✕ <strong>No disponible:</strong> La sala no está disponible o existe un solapamiento.";
        }
      } catch (err) {
        resultBox.className = "p-3 rounded-lg border border-rose-200 bg-rose-50 text-rose-800 text-sm";
        resultBox.innerText = "Error al consultar disponibilidad.";
        resultBox.classList.remove("hidden");
      } finally {
        checkBtn.disabled = false;
        checkBtn.innerText = "Comprobar disponibilidad";
      }
    });
  }
});

// Modal helpers for sensitive actions
let activeFormToSubmit = null;

function openConfirmModal(title, message, confirmBtnText, formId) {
  const modal = document.getElementById("confirm-modal");
  if (!modal) return;

  document.getElementById("modal-title").innerText = title;
  document.getElementById("modal-message").innerText = message;
  const confirmBtn = document.getElementById("modal-confirm-btn");
  confirmBtn.innerText = confirmBtnText;

  activeFormToSubmit = document.getElementById(formId);
  modal.classList.add("active");
}

function closeConfirmModal() {
  const modal = document.getElementById("confirm-modal");
  if (modal) {
    modal.classList.remove("active");
    activeFormToSubmit = null;
  }
}

function executeConfirmedAction() {
  if (activeFormToSubmit) {
    activeFormToSubmit.submit();
  }
  closeConfirmModal();
}
