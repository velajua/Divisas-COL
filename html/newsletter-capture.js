const NEWSLETTER_CAPTURE_ENDPOINT = "https://script.google.com/macros/s/AKfycbwTK47Jy1wBSyfz6zw6Ds-cJuXBXIUFgge4xGlD5tw-8njLH6Yv9rZWc8HhRPtfB54K/exec";

function getNewsletterPageContext() {
  const pathParts = (window.location.pathname || "/").split("/").filter(Boolean);
  const locale = document.documentElement.dataset.locale || pathParts[0] || "es";
  const country = document.documentElement.dataset.country || pathParts[1] || "";
  const city = document.documentElement.dataset.city || "";

  return {
    locale,
    page: window.location.pathname || "/",
    country,
    city,
    source: city ? "city-floating-helper" : "newsletter-page",
  };
}

function newsletterCopy() {
  const locale = document.documentElement.dataset.locale || "es";
  if (locale === "en") {
    return {
      ariaLabel: "Newsletter signup",
      close: "Close",
      kicker: "Currency alerts",
      title: "Want to stay up to date?",
      body: "Get rate updates and the newsletter.",
      emailLabel: "Email",
      honeypot: "Website",
      submit: "Send",
      consent: "You can unsubscribe anytime.",
      invalidEmail: "Enter a valid email.",
      success: "Done. We will let you know when there are updates.",
      missingEndpoint: "Newsletter capture endpoint is not connected.",
      saving: "Saving email...",
      failure: "Could not save the email. Try again.",
    };
  }

  return {
    ariaLabel: "Suscripcion al newsletter",
    close: "Cerrar",
    kicker: "Alertas de divisas",
    title: "¿Quieres estar al día?",
    body: "Recibe novedades de tasas y el newsletter.",
    emailLabel: "Correo electronico",
    honeypot: "Sitio web",
    submit: "Enviar",
    consent: "Puedes darte de baja cuando quieras.",
    invalidEmail: "Escribe un correo valido.",
    success: "Listo. Te avisaremos cuando haya novedades.",
    missingEndpoint: "Falta conectar el endpoint de captura.",
    saving: "Guardando correo...",
    failure: "No se pudo guardar el correo. Intenta de nuevo.",
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

  const copy = newsletterCopy();
  const wrapper = document.createElement("aside");
  wrapper.className = "newsletter-helper";
  wrapper.setAttribute("data-newsletter-capture", "floating");
  wrapper.setAttribute("aria-label", copy.ariaLabel);
  wrapper.innerHTML = `
    <button class="newsletter-helper-close" type="button" aria-label="${copy.close}">×</button>
    <div class="newsletter-helper-kicker">${copy.kicker}</div>
    <h2>${copy.title}</h2>
    <p>${copy.body}</p>
    <form class="newsletter-form" data-newsletter-form>
      <label class="sr-only" for="floatingNewsletterEmail">${copy.emailLabel}</label>
      <label class="newsletter-hp" aria-hidden="true">
        ${copy.honeypot}
        <input name="website" type="text" tabindex="-1" autocomplete="off">
      </label>
      <div class="newsletter-input-row">
        <input id="floatingNewsletterEmail" name="email" type="email" autocomplete="email" placeholder="tu@email.com" required>
        <button type="submit">${copy.submit}</button>
      </div>
      <div class="newsletter-consent">
        ${copy.consent}
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
  const copy = newsletterCopy();
  const emailInput = form.querySelector('input[name="email"]');
  const submitButton = form.querySelector('button[type="submit"]');
  const email = emailInput?.value.trim() || "";
  const honeypot = form.querySelector('input[name="website"]')?.value.trim() || "";

  if (!isValidEmail(email)) {
    setNewsletterMessage(form, copy.invalidEmail, true);
    emailInput?.focus();
    return;
  }

  if (honeypot) {
    form.reset();
    setNewsletterMessage(form, copy.success, false);
    return;
  }

  if (!NEWSLETTER_CAPTURE_ENDPOINT) {
    setNewsletterMessage(form, copy.missingEndpoint, true);
    return;
  }

  const context = getNewsletterPageContext();
  const payload = {
    email,
    website: honeypot,
    country: context.country,
    city: context.city,
    page: context.page,
    source: form.closest("[data-newsletter-capture]")?.dataset.newsletterCapture || context.source,
    submittedAt: new Date().toISOString(),
  };

  submitButton.disabled = true;
  setNewsletterMessage(form, copy.saving, false);

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
    setNewsletterMessage(form, copy.success, false);
  } catch (error) {
    console.error(error);
    setNewsletterMessage(form, copy.failure, true);
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
