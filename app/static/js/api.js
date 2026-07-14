export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request(path, options = {}) {
  const headers = { Accept: "application/json", ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`/api${path}`, {
    credentials: "same-origin",
    ...options,
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = body.detail || "Something went wrong";
    if (Array.isArray(message)) message = message.map((item) => item.msg).join(" · ");
    throw new ApiError(message, response.status);
  }
  return body;
}

export const api = {
  me: () => request("/auth/me"),
  agenda: () => request("/agenda"),
  saveAgendaDay: (dayOfWeek, data) => request(`/agenda/${dayOfWeek}`, { method: "PUT", body: data }),
  deleteAgendaDay: (dayOfWeek) => request(`/agenda/${dayOfWeek}`, { method: "DELETE" }),
  machines: (includeArchived = false) => request(`/machines?include_archived=${includeArchived}`),
  createMachine: (data) => request("/machines", { method: "POST", body: data }),
  updateMachine: (id, data) => request(`/machines/${id}`, { method: "PATCH", body: data }),
  archiveMachine: (id) => request(`/machines/${id}`, { method: "DELETE" }),
  workouts: () => request("/workouts?limit=100"),
  createWorkout: (data) => request("/workouts", { method: "POST", body: data }),
  updateWorkout: (id, data) => request(`/workouts/${id}`, { method: "PATCH", body: data }),
  deleteWorkout: (id) => request(`/workouts/${id}`, { method: "DELETE" }),
  stats: () => request("/stats/overview"),
};
