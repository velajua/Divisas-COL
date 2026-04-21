const NEWSLETTER_CAPTURE_ENDPOINT = "https://script.google.com/macros/s/AKfycbwTK47Jy1wBSyfz6zw6Ds-cJuXBXIUFgge4xGlD5tw-8njLH6Yv9rZWc8HhRPtfB54K/exec";

function getNewsletterPageContext() {
  return {
    page: window.location.pathname || "/",
    city: document.documentElement.dataset.city || "",
    source: document.documentElement.dataset.city ? "city-floating-helper" : "newsletter-page",
  };
}

function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value || "").trim());
}

function newsletterStorageKey(suffix) {
  return `divisas-newsletter-${suffix}`;
}

function shouldForceNewsletterHelper() {
  const params = new URLSearchParams(window.location.search);
  return params.get("showNewsletter") === "1";
}

function wasNewsletterHelperDismissed() {
  const dismissedAt = Number(localStorage.getItem(newsletterStorageKey("dismissedAt")) || "0");
  const sevenDays = 7 * 24 * 60 * 60 * 1000;
  return dismissedAt > 0 && Date.now() - dismissedAt < sevenDays;
}

function createFloatingNewsletterCapture() {
  if (!document.documentElement.dataset.city) return null;
  if (document.querySelector("[data-newsletter-capture]")) return null;
  if (!shouldForceNewsletterHelper() && localStorage.getItem(newsletterStorageKey("subscribed")) === "1") return null;
  if (!shouldForceNewsletterHelper() && wasNewsletterHelperDismissed()) return null;

  const wrapper = document.createElement("aside");
  wrapper.className = "newsletter-helper";
  wrapper.setAttribute("data-newsletter-capture", "floating");
  wrapper.setAttribute("aria-label", "Suscripcion al newsletter");
  wrapper.innerHTML = `
    <button class="newsletter-helper-close" type="button" aria-label="Cerrar">×</button>
    <div class="newsletter-helper-kicker">Alertas de divisas</div>
    <h2>¿Quieres estar al día?</h2>
    <p>Recibe novedades de tasas y el newsletter.</p>
    <form class="newsletter-form" data-newsletter-form>
      <label class="sr-only" for="floatingNewsletterEmail">Correo electronico</label>
      <label class="newsletter-hp" aria-hidden="true">
        Sitio web
        <input name="website" type="text" tabindex="-1" autocomplete="off">
      </label>
      <div class="newsletter-input-row">
        <input id="floatingNewsletterEmail" name="email" type="email" autocomplete="email" placeholder="tu@email.com" required>
        <button type="submit">Enviar</button>
      </div>
      <div class="newsletter-consent">
        Puedes darte de baja cuando quieras.
      </div>
      <div class="newsletter-message" data-newsletter-message aria-live="polite"></div>
    </form>
  `;

  document.body.appendChild(wrapper);

  const closeButton = wrapper.querySelector(".newsletter-helper-close");
  closeButton?.addEventListener("click", () => {
    localStorage.setItem(newsletterStorageKey("dismissedAt"), String(Date.now()));
    wrapper.remove();
  });

  return wrapper;
}

function setNewsletterMessage(form, message, isError) {
  const messageEl = form.querySelector("[data-newsletter-message]");
  if (!messageEl) return;

  messageEl.textContent = message || "";
  messageEl.classList.toggle("error", Boolean(isError));
}

async function submitNewsletterEmail(form) {
  const emailInput = form.querySelector('input[name="email"]');
  const submitButton = form.querySelector('button[type="submit"]');
  const email = emailInput?.value.trim() || "";
  const honeypot = form.querySelector('input[name="website"]')?.value.trim() || "";

  if (!isValidEmail(email)) {
    setNewsletterMessage(form, "Escribe un correo valido.", true);
    emailInput?.focus();
    return;
  }

  if (honeypot) {
    form.reset();
    setNewsletterMessage(form, "Listo. Te avisaremos cuando haya novedades.", false);
    return;
  }

  if (!NEWSLETTER_CAPTURE_ENDPOINT) {
    setNewsletterMessage(form, "Falta conectar el endpoint de captura.", true);
    return;
  }

  const context = getNewsletterPageContext();
  const payload = {
    email,
    website: honeypot,
    city: context.city,
    page: context.page,
    source: form.closest("[data-newsletter-capture]")?.dataset.newsletterCapture || context.source,
    submittedAt: new Date().toISOString(),
  };

  submitButton.disabled = true;
  setNewsletterMessage(form, "Guardando correo...", false);

  try {
    await fetch(NEWSLETTER_CAPTURE_ENDPOINT, {
      method: "POST",
      mode: NEWSLETTER_CAPTURE_ENDPOINT.includes("script.google.com") ? "no-cors" : "cors",
      headers: {
        "Content-Type": "text/plain;charset=utf-8",
      },
      body: JSON.stringify(payload),
    });

    localStorage.setItem(newsletterStorageKey("subscribed"), "1");
    form.reset();
    setNewsletterMessage(form, "Listo. Te avisaremos cuando haya novedades.", false);
  } catch (error) {
    console.error(error);
    setNewsletterMessage(form, "No se pudo guardar el correo. Intenta de nuevo.", true);
  } finally {
    submitButton.disabled = false;
  }
}

function initNewsletterCapture() {
  createFloatingNewsletterCapture();

  document.querySelectorAll("[data-newsletter-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      submitNewsletterEmail(form);
    });
  });
}

document.addEventListener("DOMContentLoaded", initNewsletterCapture);
