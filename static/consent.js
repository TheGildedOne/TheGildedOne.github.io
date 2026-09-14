/* Cookie consent for Google Analytics.

   Google Analytics is the only thing on this site that sets cookies, and UK and
   EEA law says it may not do that until the visitor agrees. So:

   - Visitors whose device is set to a European time zone are asked first, and
     nothing from Google loads until they say yes. UTC and an unreadable time
     zone count as European, because privacy browsers report UTC.
   - Everyone else gets analytics straight away. As a backstop for a European
     visitor whose time zone does not look European (a traveller, a VPN), Google's
     consent mode is told to store nothing for UK, EEA and Swiss locations, which
     Google works out from the IP address.
   - Anyone can change their mind from "Cookie settings" in the footer.
   - Advertising storage is denied for everyone. No ads run here.

   The choice is kept in localStorage. That needs no consent of its own:
   remembering a refusal is the one thing a site must store to respect it.

   This covers analytics only. AdSense in the UK/EEA needs a Google-certified
   consent platform, and check.py fails the build if ads are switched on. */
(function () {
  var script = document.currentScript;
  var GA_ID = script && script.getAttribute("data-ga");
  if (!GA_ID) return;

  var KEY = "va-consent";
  // EU 27, then Iceland, Liechtenstein, Norway, the UK and Switzerland, then the
  // French outermost regions, which Google codes separately from France.
  var REGIONS = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE",
    "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
    "IS", "LI", "NO", "GB", "CH",
    "GP", "MQ", "GF", "RE", "YT", "MF"
  ];

  window.dataLayer = window.dataLayer || [];
  function gtag() { window.dataLayer.push(arguments); }
  window.gtag = gtag;

  // The region-specific default wins over the general one for visitors Google
  // places in those regions, whichever order they are set in.
  gtag("consent", "default", {
    analytics_storage: "denied", ad_storage: "denied",
    ad_user_data: "denied", ad_personalization: "denied", region: REGIONS
  });
  gtag("consent", "default", {
    analytics_storage: "granted", ad_storage: "denied",
    ad_user_data: "denied", ad_personalization: "denied"
  });

  function readChoice() {
    try { return window.localStorage.getItem(KEY); } catch (e) { return null; }
  }
  function saveChoice(value) {
    try { window.localStorage.setItem(KEY, value); } catch (e) { /* private mode */ }
  }
  function timeZone() {
    try { return Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) { return ""; }
  }

  function asksFirst(tz) {
    return !tz
      || /^(Europe|Arctic)\//.test(tz)
      || /^Atlantic\/(Azores|Madeira|Canary|Reykjavik|Faroe|Faeroe)$/.test(tz)
      || /^Asia\/(Nicosia|Famagusta)$/.test(tz)
      || /^America\/(Guadeloupe|Martinique|Cayenne|Marigot)$/.test(tz)
      || /^Indian\/(Reunion|Mayotte)$/.test(tz)
      || /^(UTC|UCT|GMT|Universal|Zulu|Greenwich|Etc\/.+|WET|CET|MET|EET|GB|GB-Eire|Eire|Iceland|Poland|Portugal)$/.test(tz);
  }

  var loaded = false;
  function load() {
    if (loaded) return;
    loaded = true;
    gtag("js", new Date());
    gtag("config", GA_ID);
    var s = document.createElement("script");
    s.async = true;
    s.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(GA_ID);
    document.head.appendChild(s);
  }

  // Google sets its cookies on the widest domain it can, so try every level.
  function clearCookies() {
    var parts = window.location.hostname.split(".");
    var domains = [""];
    for (var i = 0; i < parts.length - 1; i++) domains.push("." + parts.slice(i).join("."));
    document.cookie.split(";").forEach(function (pair) {
      var name = pair.split("=")[0].trim();
      if (!/^_(ga|gid|gat)(_|$)/.test(name)) return;
      domains.forEach(function (d) {
        document.cookie = name + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/" +
          (d ? "; domain=" + d : "");
      });
    });
  }

  var choice = readChoice();
  var ask = asksFirst(timeZone());

  if (choice === "granted") {
    gtag("consent", "update", { analytics_storage: "granted" });
    load();
  } else if (choice !== "denied" && !ask) {
    load();
  }

  function banner() { return document.getElementById("consent"); }

  function mark() {
    var b = banner();
    if (!b) return;
    var buttons = b.querySelectorAll("[data-consent]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].setAttribute("aria-pressed",
        String(buttons[i].getAttribute("data-consent") === choice));
    }
  }

  function choose(value) {
    choice = value;
    saveChoice(value);
    gtag("consent", "update", { analytics_storage: value });
    if (value === "granted") load(); else clearCookies();
    var b = banner();
    if (b) b.hidden = true;
  }

  function wire() {
    var b = banner();
    if (b) {
      b.addEventListener("click", function (e) {
        var btn = e.target.closest && e.target.closest("[data-consent]");
        if (btn) choose(btn.getAttribute("data-consent"));
      });
    }
    var opener = document.querySelector("[data-consent-open]");
    if (opener && b) {
      opener.hidden = false;
      opener.addEventListener("click", function () {
        mark();
        b.hidden = false;
        var first = b.querySelector("button");
        if (first) first.focus();
      });
    }
    if (b && !choice && ask) b.hidden = false;
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();

  window.vaConsent = { asksFirst: asksFirst };
})();
