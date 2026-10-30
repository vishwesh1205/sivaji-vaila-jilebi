(function () {
  "use strict";

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* Mobile navigation */
  const navToggle = document.querySelector(".nav-toggle");
  const primaryNav = document.getElementById("primary-navigation");
  if (navToggle && primaryNav) {
    navToggle.addEventListener("click", function () {
      const open = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!open));
      primaryNav.classList.toggle("is-open", !open);
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && primaryNav.classList.contains("is-open")) {
        primaryNav.classList.remove("is-open");
        navToggle.setAttribute("aria-expanded", "false");
        navToggle.focus();
      }
    });
  }

  /* Accessible dropdowns */
  const dropdowns = Array.from(document.querySelectorAll(".nav-dropdown"));
  dropdowns.forEach(function (dropdown) {
    const button = dropdown.querySelector(".nav-dropdown__button");
    if (!button) return;
    button.addEventListener("click", function (event) {
      event.stopPropagation();
      const open = dropdown.classList.contains("is-open");
      dropdowns.forEach(function (other) {
        other.classList.remove("is-open");
        const otherButton = other.querySelector(".nav-dropdown__button");
        if (otherButton) otherButton.setAttribute("aria-expanded", "false");
      });
      if (!open) {
        dropdown.classList.add("is-open");
        button.setAttribute("aria-expanded", "true");
      }
    });
    dropdown.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        dropdown.classList.remove("is-open");
        button.setAttribute("aria-expanded", "false");
        button.focus();
      }
    });
  });
  document.addEventListener("click", function () {
    dropdowns.forEach(function (dropdown) {
      dropdown.classList.remove("is-open");
      const button = dropdown.querySelector(".nav-dropdown__button");
      if (button) button.setAttribute("aria-expanded", "false");
    });
  });

  /* Carousel */
  const carousel = document.querySelector("[data-carousel]");
  if (carousel) {
    const slides = Array.from(carousel.querySelectorAll("[data-slide]"));
    const dots = Array.from(carousel.querySelectorAll("[data-carousel-dot]"));
    const previous = carousel.querySelector("[data-carousel-prev]");
    const next = carousel.querySelector("[data-carousel-next]");
    const toggle = carousel.querySelector("[data-carousel-toggle]");
    let current = 0;
    let timer = null;
    let suspended = false;
    let paused = reducedMotion;

    function show(index) {
      if (!slides.length) return;
      current = (index + slides.length) % slides.length;
      slides.forEach(function (slide, i) {
        const active = i === current;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", String(!active));
        slide.toggleAttribute("inert", !active);
      });
      dots.forEach(function (dot, i) {
        const active = i === current;
        dot.classList.toggle("is-active", active);
        dot.setAttribute("aria-current", String(active));
      });
    }

    function stop() {
      if (timer) {
        window.clearInterval(timer);
        timer = null;
      }
    }

    function start() {
      if (paused || slides.length < 2 || suspended) return;
      stop();
      timer = window.setInterval(function () {
        if (!document.hidden) show(current + 1);
      }, 7000);
    }

    function updateToggle() {
      if (!toggle) return;
      toggle.textContent = paused ? "Play" : "Pause";
      toggle.setAttribute("aria-pressed", String(paused));
      toggle.setAttribute("aria-label", paused ? "Start automatic slide rotation" : "Pause automatic slide rotation");
    }

    if (previous) previous.addEventListener("click", function () { show(current - 1); start(); });
    if (next) next.addEventListener("click", function () { show(current + 1); start(); });
    dots.forEach(function (dot, index) {
      dot.addEventListener("click", function () { show(index); start(); });
    });
    if (toggle) {
      toggle.addEventListener("click", function () {
        paused = !paused;
        suspended = false;
        updateToggle();
        if (paused) stop(); else start();
      });
    }
    carousel.addEventListener("mouseenter", function () { suspended = true; stop(); });
    carousel.addEventListener("mouseleave", function () { suspended = false; start(); });
    carousel.addEventListener("focusin", function () { suspended = true; stop(); });
    carousel.addEventListener("focusout", function () { suspended = false; start(); });
    carousel.addEventListener("keydown", function (event) {
      if (event.key === "ArrowLeft") { event.preventDefault(); show(current - 1); }
      if (event.key === "ArrowRight") { event.preventDefault(); show(current + 1); }
    });
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) stop(); else start();
    });
    show(0);
    updateToggle();
    start();
  }

  /* Character counters */
  const counterTargets = ["description", "message", "feedback_text", "inline_message"];
  counterTargets.forEach(function (id) {
    const field = document.getElementById(id);
    const counter = document.getElementById(id + "_count");
    if (!field || !counter) return;
    const max = Number(field.getAttribute("maxlength") || 0);
    const update = function () {
      counter.textContent = field.value.length + (max ? " / " + max : "");
    };
    field.addEventListener("input", update);
    update();
  });

  /* Copy helpers */
  function fallbackCopy(text) {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (error) { ok = false; }
    document.body.removeChild(area);
    return ok;
  }

  function copyText(text, button) {
    const original = button.textContent;
    const done = function (ok) {
      button.textContent = ok ? "Copied" : "Select and copy";
      window.setTimeout(function () { button.textContent = original; }, 2200);
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done(true); }).catch(function () { done(fallbackCopy(text)); });
    } else {
      done(fallbackCopy(text));
    }
  }

  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      const target = document.getElementById(button.getAttribute("data-copy-target"));
      if (target) copyText(target.textContent.trim(), button);
    });
  });
  document.querySelectorAll("[data-copy-pair]").forEach(function (button) {
    button.addEventListener("click", function () {
      const text = "Registration: " + button.getAttribute("data-ref") + "\nVerification: " + button.getAttribute("data-code");
      copyText(text, button);
    });
  });

  /* Print */
  document.querySelectorAll("[data-print]").forEach(function (button) {
    button.addEventListener("click", function () { window.print(); });
  });

  /* Double-submit guard */
  document.querySelectorAll("form").forEach(function (form) {
    form.addEventListener("submit", function () {
      if (form.getAttribute("data-submitting") === "true") return;
      const submit = form.querySelector('button[type="submit"]');
      if (submit) {
        window.setTimeout(function () {
          form.setAttribute("data-submitting", "true");
          submit.setAttribute("aria-disabled", "true");
          submit.disabled = true;
          if (!/…$/.test(submit.textContent)) submit.textContent = submit.textContent.trim() + " …";
        }, 0);
      }
    });
  });

  /* Focus a flash message so assistive technology announces it */
  const flash = document.querySelector(".alert[role='status'], .alert[role='alert']");
  if (flash) {
    window.setTimeout(function () { flash.focus({ preventScroll: true }); }, 80);
  }
})();
