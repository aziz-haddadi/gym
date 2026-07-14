export function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}
export function localDate(value, options = {}) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    ...options,
  }).format(new Date(`${value}T12:00:00`));
}

export function compactNumber(value, maximumFractionDigits = 0) {
  return new Intl.NumberFormat(undefined, {
    notation: Number(value) >= 10000 ? "compact" : "standard",
    maximumFractionDigits,
  }).format(Number(value || 0));
}

export function isoToday() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}
