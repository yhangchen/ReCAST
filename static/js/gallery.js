/* Builds the qualitative gallery from static/data/gallery.json, so adding or
   removing a pair is a data edit rather than an HTML edit. No dependencies.

   gallery.json is regenerated from the paper's appendix gallery by
   scripts/extract_gallery.py. */

(function () {
  "use strict";

  var GRID = document.getElementById("gallery-grid");
  var TABS = document.getElementById("gallery-tabs");
  if (!GRID || !TABS) return;

  var LB = document.getElementById("lightbox");
  var LB_STATIC = document.getElementById("lb-static");
  var LB_RECAST = document.getElementById("lb-recast");
  var LB_PROMPT = document.getElementById("lb-prompt");

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function lambdaTitle(order, lam) {
    // "(1,1,1,2)" + [ClipScore, HPSv2, PickScore, OCR] -> a readable tooltip,
    // because the tuple alone does not say which reward got the extra budget.
    var vals = lam.replace(/[()]/g, "").split(",");
    if (!order || order.length !== vals.length) return "reward budget " + lam;
    return order.map(function (name, i) { return name + "=" + vals[i]; }).join(", ");
  }

  function comparison(setting, pair) {
    var dir = "static/images/gallery/" + setting.key + "/";
    var box = el("div", "cmp");

    var base = el("img");
    base.src = dir + pair.static;
    base.alt = "Static weighting: " + pair.prompt;
    base.loading = "lazy";
    base.decoding = "async";

    var ours = el("img", "top");
    ours.src = dir + pair.recast;
    ours.alt = "ReCAST: " + pair.prompt;
    ours.loading = "lazy";
    ours.decoding = "async";

    var divider = el("div", "divider");

    var slider = document.createElement("input");
    slider.type = "range";
    slider.min = 0;
    slider.max = 100;
    slider.value = 50;
    slider.step = 0.1;
    slider.setAttribute("aria-label",
      "Reveal ReCAST versus static weighting for: " + pair.prompt);

    slider.addEventListener("input", function () {
      box.style.setProperty("--split", slider.value + "%");
    });

    // Dragging anywhere in the frame should move the divider, not just the
    // (invisible) native thumb.
    function track(ev) {
      if (ev.buttons === 0 && ev.type === "pointermove") return;
      var r = box.getBoundingClientRect();
      var pct = ((ev.clientX - r.left) / r.width) * 100;
      slider.value = Math.max(0, Math.min(100, pct));
      box.style.setProperty("--split", slider.value + "%");
    }
    box.addEventListener("pointerdown", track);
    box.addEventListener("pointermove", track);

    box.appendChild(base);
    box.appendChild(ours);
    box.appendChild(divider);
    box.appendChild(el("span", "tag left", "static"));
    box.appendChild(el("span", "tag right", "ReCAST"));
    box.appendChild(slider);
    return box;
  }

  function card(setting, pair) {
    var fig = el("figure", "pair");
    fig.appendChild(comparison(setting, pair));

    var cap = el("figcaption");
    var lam = el("span", "lam", "λ = " + pair.lambda);
    lam.title = lambdaTitle(setting.lambda_order, pair.lambda);
    cap.appendChild(lam);
    cap.appendChild(el("span", "prompt", pair.prompt));

    var zoom = el("button", "zoom", "View full size");
    zoom.addEventListener("click", function () { openLightbox(setting, pair); });
    cap.appendChild(zoom);

    fig.appendChild(cap);
    return fig;
  }

  function openLightbox(setting, pair) {
    var dir = "static/images/gallery/" + setting.key + "/";
    LB_STATIC.src = dir + pair.static;
    LB_RECAST.src = dir + pair.recast;
    LB_PROMPT.textContent = "λ = " + pair.lambda + " — " + pair.prompt;
    LB.hidden = false;
    document.body.style.overflow = "hidden";
  }

  function closeLightbox() {
    LB.hidden = true;
    document.body.style.overflow = "";
  }

  if (LB) {
    LB.querySelector(".lb-close").addEventListener("click", closeLightbox);
    LB.addEventListener("click", function (ev) {
      if (ev.target === LB) closeLightbox();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && !LB.hidden) closeLightbox();
    });
  }

  function render(data, setting) {
    GRID.textContent = "";
    (data.pairs[setting.key] || []).forEach(function (pair) {
      GRID.appendChild(card(setting, pair));
    });
    Array.prototype.forEach.call(TABS.children, function (tab) {
      tab.setAttribute("aria-selected", String(tab.dataset.key === setting.key));
    });
  }

  fetch("static/data/gallery.json")
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (data) {
      data.settings.forEach(function (setting) {
        var tab = el("button", "tab", setting.label);
        tab.dataset.key = setting.key;
        tab.setAttribute("role", "tab");
        tab.addEventListener("click", function () { render(data, setting); });
        TABS.appendChild(tab);
      });
      render(data, data.settings[0]);
    })
    .catch(function (err) {
      // fetch() is blocked on file:// in Chrome, so say so rather than showing
      // an empty section: `python3 -m http.server` is the fix.
      GRID.appendChild(el("p", "caveat",
        "Could not load static/data/gallery.json (" + err.message + "). " +
        "If you opened this file directly, serve it instead: " +
        "python3 -m http.server 8000"));
    });
})();
