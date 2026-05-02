(function () {
  const forms = document.querySelectorAll("[data-auth-form]");
  const visual = document.querySelector("[data-auth-visual] .scan-card");
  let typingTimer = null;

  document.querySelectorAll("[data-toggle-password]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.parentElement.querySelector("input");
      if (!input) return;
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      button.textContent = showing ? "Show" : "Hide";
    });
  });

  function validateField(field) {
    const input = field.querySelector("input, select");
    const hint = field.querySelector("[data-field-hint]");
    if (!input) return true;

    const value = input.value.trim();
    let ok = true;
    let message = hint ? hint.dataset.default || hint.textContent : "";
    if (hint && !hint.dataset.default) hint.dataset.default = hint.textContent;

    if (input.name === "username") {
      ok = value.length >= 3;
      message = ok ? "Username looks ready." : "Username needs at least 3 characters.";
    }

    if (input.name === "email" && value) {
      ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
      message = ok ? "Email format is valid." : "Enter a valid email address.";
    }

    if (input.type === "password" || input.name === "password" || input.name === "password2") {
      ok = value.length >= 6;
      message = ok ? "Password strength accepted." : "Use at least 6 characters.";
    }

    field.classList.toggle("is-valid", ok && value.length > 0);
    field.classList.toggle("is-invalid", !ok && value.length > 0);
    if (hint) hint.textContent = message;
    return ok;
  }

  forms.forEach((form) => {
    const fields = form.querySelectorAll(".auth-field");
    fields.forEach((field) => {
      const input = field.querySelector("input, select");
      if (!input) return;
      input.addEventListener("input", () => validateField(field));
      input.addEventListener("input", () => {
        if (!visual) return;
        visual.classList.add("is-typing");
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => visual.classList.remove("is-typing"), 650);
      });
      input.addEventListener("blur", () => validateField(field));
    });

    form.addEventListener("submit", (event) => {
      const ok = Array.from(fields).every(validateField);
      const password = form.querySelector('input[name="password"]');
      const password2 = form.querySelector('input[name="password2"]');
      if (password && password2 && password.value !== password2.value) {
        event.preventDefault();
        const field = password2.closest(".auth-field");
        field.classList.add("is-invalid");
        const hint = field.querySelector("[data-field-hint]");
        if (hint) hint.textContent = "Passwords must match.";
        return;
      }
      if (!ok) event.preventDefault();
    });
  });
})();
