// BSG Adventure — browser client.
// Talks to the local server via SSE (server→browser) and POST (browser→server).
// Vanilla JS, no dependencies, no external fetches. LAN-only.

(function () {
  "use strict";

  const out    = document.getElementById("output");
  const form   = document.getElementById("form");
  const input  = document.getElementById("input");
  const status = document.getElementById("status");

  let sessionId = null;
  let es        = null;     // EventSource
  let sessionEnded = false;

  // ─── DOM helpers ──────────────────────────────────────────────────────────

  function append(text, className) {
    if (text === undefined || text === null) return;
    const span = document.createElement("span");
    if (className) span.className = className;
    // Preserve newlines as-is; the <pre> container does the rest.
    span.textContent = text + "\n";
    out.appendChild(span);
    // Auto-scroll iff we were already near the bottom.
    out.scrollTop = out.scrollHeight;
  }

  function setStatus(text) {
    status.textContent = text || "";
  }

  // ─── session lifecycle ────────────────────────────────────────────────────

  async function spawn() {
    setStatus("Hailing Galactica…");
    const r = await fetch("/spawn", { method: "POST" });
    if (!r.ok) {
      setStatus("Could not start session (HTTP " + r.status + ").");
      return false;
    }
    const data = await r.json();
    sessionId = data.session_id;
    return true;
  }

  function connectEvents() {
    if (es) { try { es.close(); } catch (e) {} }
    es = new EventSource("/events?session=" + encodeURIComponent(sessionId));
    es.onmessage = function (ev) {
      let parsed;
      try { parsed = JSON.parse(ev.data); }
      catch (e) { append(ev.data); return; }
      if (parsed && typeof parsed.text === "string") {
        append(parsed.text);
      }
    };
    es.addEventListener("end", function () {
      sessionEnded = true;
      setStatus("Session ended. Refresh to begin again.");
      input.disabled = true;
      try { es.close(); } catch (e) {}
    });
    es.onerror = function () {
      if (sessionEnded) return;
      setStatus("Connection blip. Reconnecting…");
      // EventSource auto-reconnects; if the server has GC'd our session
      // we'll get a 404 and the next onerror will keep firing. That's
      // fine — the player can refresh.
    };
    es.onopen = function () {
      setStatus("");
    };
  }

  async function sendLine(line) {
    if (sessionId === null) return;
    try {
      await fetch("/input?session=" + encodeURIComponent(sessionId), {
        method: "POST",
        headers: { "Content-Type": "text/plain; charset=utf-8" },
        body: line,
      });
    } catch (e) {
      setStatus("Send failed: " + e.message);
    }
  }

  function closeOnUnload() {
    if (!sessionId) return;
    try {
      // sendBeacon is fire-and-forget; perfect for tab close.
      navigator.sendBeacon(
        "/close?session=" + encodeURIComponent(sessionId),
        new Blob([""], { type: "text/plain" })
      );
    } catch (e) {}
  }

  // ─── input handling ───────────────────────────────────────────────────────

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    if (sessionEnded) return;
    const line = input.value;
    input.value = "";
    // Echo the user's input dimly so the transcript reads like a terminal.
    append("> " + line, "echo");
    sendLine(line);
  });

  // Keep focus in the input box.
  document.addEventListener("click", function () {
    if (!sessionEnded) input.focus();
  });
  window.addEventListener("load", function () { input.focus(); });

  window.addEventListener("beforeunload", closeOnUnload);
  window.addEventListener("pagehide", closeOnUnload);

  // ─── start ────────────────────────────────────────────────────────────────

  (async function start() {
    const ok = await spawn();
    if (!ok) return;
    connectEvents();
  })();
})();
