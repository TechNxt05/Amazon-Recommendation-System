const BACKEND = "http://127.0.0.1:5000";

export async function sendLog(level = "info", message = "", meta = {}) {
  try {
    const tag = `[Front][${level.toUpperCase()}]`;
    if (level === "error") console.error(tag, message, meta);
    else if (level === "warn") console.warn(tag, message, meta);
    else console.log(tag, message, meta);

    // Send to backend (non-blocking)
    fetch(`${BACKEND}/api/log`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ level, message, meta, ts: new Date().toISOString() }),
    }).catch(() => {});
  } catch (e) {
    console.error("[sendLog error]", e);
  }
}
