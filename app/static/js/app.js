import { api, ApiError } from "./api.js";
import { compactNumber, escapeHtml, isoToday, localDate } from "./format.js";

const state = {
  user: null,
  machines: [],
  workouts: [],
  stats: null,
  activeView: "dashboard",
};

const MUSCLE_GROUPS = Object.freeze([
  "Chest",
  "Back",
  "Shoulders",
  "Biceps",
  "Triceps",
  "Forearms",
  "Legs",
  "Core",
  "Cardio",
  "Other",
]);

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function showToast(message, tone = "success") {
  const toast = $("#toast");
  toast.textContent = message;
  toast.dataset.tone = tone;
  toast.classList.add("visible");
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove("visible"), 3200);
}

function setBusy(form, busy) {
  const button = $("button[type='submit']", form);
  if (!button) return;
  button.disabled = busy;
  button.dataset.label ||= button.textContent;
  button.textContent = busy ? "Saving…" : button.dataset.label;
}

async function initialize() {
  $("#today-label").textContent = new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  }).format(new Date()).toUpperCase();

  try {
    state.user = await api.me();
    await loadApplication();
    showApplication();
  } catch (error) {
    const message = error instanceof ApiError && error.status === 401
      ? "Caddy did not provide an authorized user. Verify the proxy authentication header."
      : "The application is unavailable. Check the service and try again shortly.";
    showAccessError(message);
  }
}

async function loadApplication(includeArchived = false) {
  const [machines, workoutPage, stats] = await Promise.all([
    api.machines(includeArchived),
    api.workouts(),
    api.stats(),
  ]);
  state.machines = machines;
  state.workouts = workoutPage.items;
  state.stats = stats;
  renderAll();
}

function showApplication() {
  $("#loading-screen").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");
  $("#user-name").textContent = state.user.username;
  $("#user-avatar").textContent = state.user.username.charAt(0).toUpperCase();
}

function showAccessError(message) {
  $("#loader-mark").classList.add("hidden");
  $("#access-error-message").textContent = message;
  $("#access-error").classList.remove("hidden");
}

function renderAll() {
  renderMetrics();
  renderChart();
  renderRecords();
  renderWorkouts();
  renderMachines();
}

function renderMetrics() {
  const stats = state.stats;
  const cards = [
    { label: "Current streak", value: stats.current_streak, suffix: stats.current_streak === 1 ? "day" : "days", accent: true, icon: "↟" },
    { label: "Last 30 days", value: stats.workouts_last_30_days, suffix: "sessions", icon: "↗" },
    { label: "Lifetime volume", value: compactNumber(stats.total_volume_kg, 1), suffix: "kg", icon: "◆" },
    { label: "Longest streak", value: stats.longest_streak, suffix: stats.longest_streak === 1 ? "day" : "days", icon: "⌁" },
  ];
  $("#metric-grid").innerHTML = cards.map((card) => `
    <article class="metric-card ${card.accent ? "accent" : ""}">
      <div class="metric-top"><span>${card.label}</span><i>${card.icon}</i></div>
      <div class="metric-value">${escapeHtml(card.value)} <small>${card.suffix}</small></div>
    </article>
  `).join("");
}

function renderChart() {
  const weekly = state.stats.weekly;
  const max = Math.max(...weekly.map((item) => Number(item.volume_kg)), 1);
  $("#volume-chart").innerHTML = weekly.map((item, index) => {
    const height = Number(item.volume_kg) ? Math.max(7, (Number(item.volume_kg) / max) * 100) : 2;
    const label = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" })
      .format(new Date(`${item.week_start}T12:00:00`));
    return `<div class="chart-column" title="${compactNumber(item.volume_kg, 1)} kg · ${item.workouts} workouts">
      <div class="chart-track"><span style="height:${height}%"></span></div>
      <small>${index % 2 === 0 ? label : ""}</small>
    </div>`;
  }).join("");
}

function renderRecords() {
  const records = state.stats.personal_records.slice(0, 5);
  if (!records.length) {
    $("#records-list").innerHTML = emptyState("No records yet", "Log weighted sets to establish your first PR.", false);
    return;
  }
  $("#records-list").innerHTML = records.map((record, index) => `
    <div class="record-row">
      <span class="record-rank">${String(index + 1).padStart(2, "0")}</span>
      <div><strong>${escapeHtml(record.machine_name)}</strong><small>Best weight</small></div>
      <b>${compactNumber(record.max_weight_kg, 2)}<small> kg</small></b>
    </div>
  `).join("");
}

function workoutCard(workout) {
  const machineNames = workout.entries.map((entry) => entry.machine_name);
  const tags = machineNames.slice(0, 3).map((name) => `<span>${escapeHtml(name)}</span>`).join("");
  const extra = machineNames.length > 3 ? `<span>+${machineNames.length - 3}</span>` : "";
  return `<article class="workout-card">
    <div class="workout-date-block"><strong>${new Date(`${workout.workout_date}T12:00:00`).getDate()}</strong><span>${new Intl.DateTimeFormat(undefined, { month: "short" }).format(new Date(`${workout.workout_date}T12:00:00`))}</span></div>
    <div class="workout-main">
      <div class="workout-title-line"><h3>${escapeHtml(workout.title)}</h3><time>${localDate(workout.workout_date, { year: undefined, weekday: "short" })}</time></div>
      <div class="machine-tags">${tags}${extra || (!tags ? "<span>No machines</span>" : "")}</div>
    </div>
    <div class="workout-numbers">
      <div><strong>${workout.total_sets}</strong><span>sets</span></div>
      ${workout.drop_sets ? `<div><strong>${workout.drop_sets}</strong><span>drop sets</span></div>` : ""}
      <div><strong>${compactNumber(workout.total_volume_kg, 1)}</strong><span>kg volume</span></div>
      ${workout.duration_minutes ? `<div><strong>${workout.duration_minutes}</strong><span>minutes</span></div>` : ""}
    </div>
    <div class="card-actions">
      <button class="icon-button repeat-action" data-action="repeat-workout" data-id="${workout.id}" aria-label="Repeat ${escapeHtml(workout.title)}"><span aria-hidden="true">↻</span> Repeat</button>
      <button class="icon-button" data-action="edit-workout" data-id="${workout.id}" aria-label="Edit ${escapeHtml(workout.title)}">✎</button>
      <button class="icon-button danger" data-action="delete-workout" data-id="${workout.id}" aria-label="Delete ${escapeHtml(workout.title)}">×</button>
    </div>
  </article>`;
}

function renderWorkouts() {
  const content = state.workouts.length
    ? state.workouts.map(workoutCard).join("")
    : emptyState("No workouts logged", "Your next session starts the story.", true);
  $("#all-workouts").innerHTML = content;
  $("#recent-workouts").innerHTML = state.workouts.length
    ? state.workouts.slice(0, 4).map(workoutCard).join("")
    : emptyState("No workouts logged", "Add machines, then record your first session.", true);
}

function renderMachines() {
  if (!state.machines.length) {
    $("#machine-grid").innerHTML = emptyState("Your gym floor is empty", "Add the machines and movements you train with.", false);
    return;
  }
  $("#machine-grid").innerHTML = state.machines.map((machine) => `
    <article class="machine-card ${machine.active ? "" : "archived"}">
      <div class="machine-symbol">${escapeHtml(machine.name.charAt(0).toUpperCase())}</div>
      <div class="machine-copy">
        <span class="group-pill">${escapeHtml(machine.muscle_group)}</span>
        <h3>${escapeHtml(machine.name)}</h3>
        <p>${escapeHtml(machine.notes || "Ready for your next session.")}</p>
      </div>
      <div class="machine-actions">
        <button class="text-button" data-action="edit-machine" data-id="${machine.id}">Edit</button>
        ${machine.active
          ? `<button class="text-button danger-text" data-action="archive-machine" data-id="${machine.id}">Archive</button>`
          : `<button class="text-button" data-action="restore-machine" data-id="${machine.id}">Restore</button>`}
      </div>
    </article>
  `).join("");
}

function emptyState(title, copy, withAction) {
  return `<div class="empty-state"><span>◇</span><h3>${title}</h3><p>${copy}</p>${withAction ? '<button class="button secondary compact js-new-workout">Log workout</button>' : ""}</div>`;
}

function navigate(view) {
  state.activeView = view;
  $$(".view").forEach((element) => element.classList.toggle("active-view", element.id === `view-${view}`));
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function openMachineDialog(machine = null) {
  const dialog = $("#machine-dialog");
  const form = $("#machine-form");
  form.reset();
  form.dataset.id = machine?.id || "";
  $("#machine-modal-title").textContent = machine ? "Edit machine" : "Add machine";
  if (machine) {
    $("#machine-name").value = machine.name;
    $("#machine-group").value = machine.muscle_group;
    $("#machine-notes").value = machine.notes || "";
  }
  dialog.showModal();
}

function defaultMuscleGroup() {
  return state.machines.find((machine) => machine.active)?.muscle_group || MUSCLE_GROUPS[0];
}

function muscleOptions(selectedGroup = "") {
  return MUSCLE_GROUPS.map((group) =>
    `<option value="${group}" ${group === selectedGroup ? "selected" : ""}>${group}</option>`
  ).join("");
}

function machineOptions(muscleGroup, selectedId = "") {
  const machines = state.machines.filter((machine) =>
    machine.muscle_group === muscleGroup && (machine.active || machine.id === selectedId)
  );
  if (!machines.length) return '<option value="" disabled selected>No active machines for this muscle</option>';
  return machines.map((machine) =>
    `<option value="${machine.id}" ${machine.id === selectedId ? "selected" : ""}>${escapeHtml(machine.name)}${machine.active ? "" : " · archived"}</option>`
  ).join("");
}

function setRow(item = {}) {
  return `<div class="set-row">
    <span class="set-index"></span>
    <label><span>kg</span><input class="set-weight" type="number" min="0" max="100000" step="0.01" value="${item.weight_kg ?? ""}" required inputmode="decimal"></label>
    <label><span>reps</span><input class="set-reps" type="number" min="1" max="1000" step="1" value="${item.reps ?? ""}" required inputmode="numeric"></label>
    <label><span>RPE</span><input class="set-rpe" type="number" min="1" max="10" step="0.5" value="${item.rpe ?? ""}" inputmode="decimal"></label>
    <label class="drop-check"><input class="set-drop" type="checkbox" ${item.is_drop_set ? "checked" : ""}><span>Drop</span></label>
    <button class="remove-set" type="button" data-action="remove-set" aria-label="Remove set">×</button>
  </div>`;
}

function entryRow(entry = {}) {
  const sets = entry.sets?.length ? entry.sets : [{}];
  const selectedMachine = state.machines.find((machine) => machine.id === entry.machine_id);
  const selectedGroup = entry.muscle_group || selectedMachine?.muscle_group || defaultMuscleGroup();
  return `<article class="entry-card">
    <div class="entry-head">
      <label>Muscle<select class="entry-muscle" required>${muscleOptions(selectedGroup)}</select></label>
      <label>Machine<select class="entry-machine" required>${machineOptions(selectedGroup, entry.machine_id)}</select></label>
      <button class="text-button danger-text" type="button" data-action="remove-entry">Remove</button>
    </div>
    <div class="sets-head"><span>Set</span><span>Weight</span><span>Reps</span><span>Effort</span><span>Drop</span><i></i></div>
    <div class="sets-list">${sets.map(setRow).join("")}</div>
    <div class="entry-foot">
      <button class="text-button" type="button" data-action="add-set">+ Add set</button>
      <input class="entry-notes" maxlength="1000" value="${escapeHtml(entry.notes || "")}" placeholder="Exercise notes (optional)">
    </div>
  </article>`;
}

function renumberSets(root = document) {
  $$(".entry-card", root).forEach((entry) => {
    $$(".set-row", entry).forEach((row, index) => {
      $(".set-index", row).textContent = String(index + 1).padStart(2, "0");
    });
  });
}

function openWorkoutDialog(workout = null, { repeat = false } = {}) {
  if (!state.machines.some((machine) => machine.active)) {
    showToast("Add your first machine before logging a workout", "notice");
    openMachineDialog();
    return;
  }
  const form = $("#workout-form");
  form.reset();
  form.dataset.id = repeat ? "" : workout?.id || "";
  form.dataset.mode = repeat ? "repeat" : workout ? "edit" : "create";
  $("#workout-modal-title").textContent = repeat ? "Repeat workout" : workout ? "Edit workout" : "Log workout";
  $("#workout-date").value = repeat ? isoToday() : workout?.workout_date || isoToday();
  $("#workout-title").value = workout?.title || "Workout";
  $("#workout-duration").value = workout?.duration_minutes || "";
  $("#workout-notes").value = workout?.notes || "";
  $("#entry-list").innerHTML = workout?.entries?.length
    ? workout.entries.map(entryRow).join("")
    : entryRow();
  renumberSets($("#entry-list"));
  $("#workout-dialog").showModal();
}

function collectWorkout() {
  return {
    workout_date: $("#workout-date").value,
    title: $("#workout-title").value.trim(),
    duration_minutes: $("#workout-duration").value ? Number($("#workout-duration").value) : null,
    notes: $("#workout-notes").value.trim() || null,
    entries: $$(".entry-card", $("#entry-list")).map((entry) => ({
      machine_id: $(".entry-machine", entry).value,
      notes: $(".entry-notes", entry).value.trim() || null,
      sets: $$(".set-row", entry).map((row) => ({
        weight_kg: Number($(".set-weight", row).value),
        reps: Number($(".set-reps", row).value),
        rpe: $(".set-rpe", row).value ? Number($(".set-rpe", row).value) : null,
        is_drop_set: $(".set-drop", row).checked,
      })),
    })),
  };
}

async function refreshAfterMutation(message) {
  await loadApplication($("#show-archived").checked);
  showToast(message);
}

$("#machine-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  setBusy(form, true);
  const payload = {
    name: $("#machine-name").value.trim(),
    muscle_group: $("#machine-group").value,
    notes: $("#machine-notes").value.trim() || null,
  };
  try {
    if (form.dataset.id) await api.updateMachine(form.dataset.id, payload);
    else await api.createMachine(payload);
    $("#machine-dialog").close();
    await refreshAfterMutation(form.dataset.id ? "Machine updated" : "Machine added");
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(form, false);
  }
});

$("#workout-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  setBusy(form, true);
  try {
    const payload = collectWorkout();
    if (form.dataset.id) await api.updateWorkout(form.dataset.id, payload);
    else await api.createWorkout(payload);
    $("#workout-dialog").close();
    const message = form.dataset.mode === "repeat"
      ? "Workout repeated"
      : form.dataset.id ? "Workout updated" : "Workout logged";
    await refreshAfterMutation(message);
  } catch (error) {
    showToast(error.message, "error");
  } finally {
    setBusy(form, false);
  }
});

document.addEventListener("click", async (event) => {
  const button = event.target.closest("button");
  if (!button) return;

  if (button.dataset.view) navigate(button.dataset.view);
  if (button.dataset.goView) navigate(button.dataset.goView);
  if (button.matches(".js-new-workout")) openWorkoutDialog();
  if (button.id === "new-machine-button") openMachineDialog();
  if (button.dataset.closeDialog) $(`#${button.dataset.closeDialog}`).close();

  const { action, id } = button.dataset;
  if (action === "add-set") {
    $(".sets-list", button.closest(".entry-card")).insertAdjacentHTML("beforeend", setRow());
    renumberSets(button.closest(".entry-card"));
  }
  if (action === "remove-set") {
    const entry = button.closest(".entry-card");
    button.closest(".set-row").remove();
    renumberSets(entry);
  }
  if (action === "remove-entry") button.closest(".entry-card").remove();
  if (action === "repeat-workout") {
    openWorkoutDialog(state.workouts.find((item) => item.id === id), { repeat: true });
  }
  if (action === "edit-workout") openWorkoutDialog(state.workouts.find((item) => item.id === id));
  if (action === "delete-workout") {
    if (!window.confirm("Delete this workout and all of its sets?")) return;
    try {
      await api.deleteWorkout(id);
      await refreshAfterMutation("Workout deleted");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "edit-machine") openMachineDialog(state.machines.find((item) => item.id === id));
  if (action === "archive-machine") {
    if (!window.confirm("Archive this machine? Existing workout history stays intact.")) return;
    try {
      await api.archiveMachine(id);
      await refreshAfterMutation("Machine archived");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "restore-machine") {
    try {
      await api.updateMachine(id, { active: true });
      await refreshAfterMutation("Machine restored");
    } catch (error) { showToast(error.message, "error"); }
  }
});

document.addEventListener("change", (event) => {
  if (!event.target.matches(".entry-muscle")) return;
  const entry = event.target.closest(".entry-card");
  $(".entry-machine", entry).innerHTML = machineOptions(event.target.value);
});

$("#add-exercise-button").addEventListener("click", () => {
  $("#entry-list").insertAdjacentHTML("beforeend", entryRow());
  renumberSets($("#entry-list"));
});

$("#show-archived").addEventListener("change", async (event) => {
  try {
    state.machines = await api.machines(event.target.checked);
    renderMachines();
  } catch (error) { showToast(error.message, "error"); }
});

$$('dialog').forEach((dialog) => dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
}));

initialize();
