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
  machines: (includeArchived = false) => request(`/machines?include_archived=${includeArchived}`),
  createMachine: (data) => request("/machines", { method: "POST", body: data }),
  updateMachine: (id, data) => request(`/machines/${id}`, { method: "PATCH", body: data }),
  archiveMachine: (id) => request(`/machines/${id}`, { method: "DELETE" }),
  workouts: ({ dateFrom = null, dateTo = null, limit = 100, offset = 0 } = {}) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    return request(`/workouts?${params}`);
  },
  createWorkout: (data) => request("/workouts", { method: "POST", body: data }),
  updateWorkout: (id, data) => request(`/workouts/${id}`, { method: "PATCH", body: data }),
  deleteWorkout: (id) => request(`/workouts/${id}`, { method: "DELETE" }),
  programs: (includeArchived = false) => request(`/programs?include_archived=${includeArchived}`),
  createProgram: (data) => request("/programs", { method: "POST", body: data }),
  updateProgram: (id, data) => request(`/programs/${id}`, { method: "PATCH", body: data }),
  updateProgramSteps: (id, steps) => request(`/programs/${id}/steps`, { method: "PUT", body: { steps } }),
  archiveProgram: (id) => request(`/programs/${id}`, { method: "DELETE" }),
  activateProgram: (id) => request(`/programs/${id}/activate`, { method: "POST", body: {} }),
  dueProgramStep: () => request("/programs/active/due"),
  advanceProgram: (targetStepId = null) => request("/programs/active/advance", {
    method: "POST",
    body: { target_step_id: targetStepId },
  }),
  stats: () => request("/stats/overview"),
};
