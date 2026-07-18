import { api, ApiError } from "./api.js";
import { compactNumber, escapeHtml, isoToday, localDate } from "./format.js";

const initialDate = new Date();
const state = {
  user: null,
  agendaMonth: new Date(initialDate.getFullYear(), initialDate.getMonth(), 1),
  agendaWorkouts: [],
  machines: [],
  workouts: [],
  workoutTemplates: [],
  programs: [],
  dueProgram: null,
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

const WEEKDAYS = Object.freeze([
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
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
  const { dateFrom, dateTo } = agendaMonthRange();
  const [machines, workoutPage, agendaPage, stats, workoutTemplates, programs, dueProgram] = await Promise.all([
    api.machines(includeArchived),
    api.workouts(),
    api.workouts({ dateFrom, dateTo }),
    api.stats(),
    api.workoutTemplates(true),
    api.programs(true),
    api.dueProgramStep(),
  ]);
  state.machines = machines;
  state.workouts = workoutPage.items;
  state.agendaWorkouts = agendaPage.items;
  state.stats = stats;
  state.workoutTemplates = workoutTemplates;
  state.programs = programs;
  state.dueProgram = dueProgram;
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
  renderTodayPlan();
  renderMetrics();
  renderChart();
  renderRecords();
  renderWorkoutTemplates();
  renderWorkouts();
  renderAgenda();
  renderPrograms();
  renderMachines();
}

function dueStepLabel(step) {
  if (!step) return "No plan due";
  return step.label || (step.step_type === "rest" ? "Rest day" : "Workout");
}

function musclePills(groups = []) {
  return groups.map((group) => `<span>${escapeHtml(group)}</span>`).join("");
}

function activeWorkoutTemplates() {
  return state.workoutTemplates.filter((template) => !template.archived_at);
}

function findWorkoutTemplate(templateId) {
  return state.workoutTemplates.find((template) => template.id === templateId) || null;
}

function renderTodayPlan() {
  const due = state.dueProgram;
  if (!due) {
    $("#today-plan").innerHTML = `
      <div class="today-plan-copy">
        <span class="plan-symbol">≋</span>
        <div><p class="eyebrow">Today's plan</p><h2>No active program</h2><small>Create a rotating split and FORGE will keep your next session due.</small></div>
      </div>
      <button class="button secondary compact" data-go-view="programs">Set up a program</button>`;
    return;
  }

  const step = due.step;
  if (!due.is_started) {
    $("#today-plan").innerHTML = `
      <div class="today-plan-copy">
        <span class="plan-symbol rest">◷</span>
        <div>
          <p class="eyebrow">Program scheduled · ${escapeHtml(due.program_name)}</p>
          <h2>Starts ${escapeHtml(localDate(due.starts_on))}</h2>
          <small>First step: ${escapeHtml(dueStepLabel(step))}. Nothing advances before this date.</small>
        </div>
      </div>
      <button class="text-button" data-go-view="programs">Manage</button>`;
    return;
  }
  const rest = step.step_type === "rest";
  $("#today-plan").innerHTML = `
    <div class="today-plan-copy">
      <span class="plan-symbol ${rest ? "rest" : ""}">${rest ? "○" : "↗"}</span>
      <div>
        <p class="eyebrow">Today's plan · ${escapeHtml(due.program_name)}</p>
        <h2>${escapeHtml(dueStepLabel(step))}</h2>
        <div class="plan-muscles">${rest
          ? "<span>Recovery</span>"
          : step.linked_workout_template_name
            ? `<span>Saved workout · ${escapeHtml(step.linked_workout_template_name)}</span>`
            : musclePills(step.muscle_groups || []) || "<span>Any muscle group</span>"}</div>
      </div>
    </div>
    <div class="today-plan-actions">
      ${rest ? "" : '<button class="button primary compact js-new-workout">Log this workout</button>'}
      <button class="button ghost compact" data-action="skip-program-step">Skip step</button>
      <button class="text-button" data-go-view="programs">Manage</button>
    </div>`;
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

function workoutTemplateCard(template) {
  const archived = Boolean(template.archived_at);
  const exercises = template.exercises.map((exercise, index) => `
    <li>
      <b>${String(index + 1).padStart(2, "0")}</b>
      <strong>${escapeHtml(exercise.machine_name)}</strong>
      <span>${escapeHtml(exercise.muscle_group)}</span>
    </li>`).join("");
  return `<article class="workout-template-card ${archived ? "archived" : ""}">
    <div class="workout-template-head">
      <div><p class="eyebrow">${archived ? "Archived workout" : "Reusable workout"}</p><h3>${escapeHtml(template.name)}</h3></div>
      <span class="workout-template-status">${template.exercises.length} ${template.exercises.length === 1 ? "exercise" : "exercises"}</span>
    </div>
    <p class="workout-template-notes">${escapeHtml(template.notes || "Ready to add to your Agenda.")}</p>
    <ol class="template-exercise-preview">${exercises}</ol>
    <div class="workout-template-actions">
      ${archived ? "" : `<button class="button primary compact" data-action="log-workout-template" data-id="${template.id}">Log session</button>`}
      ${archived ? "" : `<button class="button ghost compact" data-action="edit-workout-template" data-id="${template.id}">Edit</button>`}
      ${archived ? "" : `<button class="text-button danger-text" data-action="archive-workout-template" data-id="${template.id}">Archive</button>`}
    </div>
  </article>`;
}

function renderWorkoutTemplates() {
  const templates = [...state.workoutTemplates].sort((left, right) =>
    Number(Boolean(left.archived_at)) - Number(Boolean(right.archived_at))
      || left.name.localeCompare(right.name)
  );
  $("#workout-template-grid").innerHTML = templates.length
    ? templates.map(workoutTemplateCard).join("")
    : `<div class="empty-state"><span>↗</span><h3>No saved workouts yet</h3><p>Build a reusable exercise list once, then record different sets and weights each day.</p><button class="button primary compact" data-action="new-workout-template">Build your first workout</button></div>`;
}

function workoutCard(workout) {
  const machineNames = workout.entries.map((entry) => entry.machine_name);
  const tags = machineNames.slice(0, 3).map((name) => `<span>${escapeHtml(name)}</span>`).join("");
  const extra = machineNames.length > 3 ? `<span>+${machineNames.length - 3}</span>` : "";
  return `<article class="workout-card">
    <div class="workout-date-block"><strong>${new Date(`${workout.workout_date}T12:00:00`).getDate()}</strong><span>${new Intl.DateTimeFormat(undefined, { month: "short" }).format(new Date(`${workout.workout_date}T12:00:00`))}</span></div>
    <div class="workout-main">
      <div class="workout-title-line"><h3>${escapeHtml(workout.title)}</h3><time>${localDate(workout.workout_date, { year: undefined, weekday: "short" })}</time></div>
      ${workout.template_name ? `<small class="session-source">From ${escapeHtml(workout.template_name)} · customized snapshot</small>` : ""}
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

function findWorkout(workoutId) {
  return state.workouts.find((workout) => workout.id === workoutId)
    || state.agendaWorkouts.find((workout) => workout.id === workoutId);
}

function isoDate(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function agendaMonthRange() {
  const year = state.agendaMonth.getFullYear();
  const month = state.agendaMonth.getMonth();
  return {
    dateFrom: isoDate(new Date(year, month, 1)),
    dateTo: isoDate(new Date(year, month + 1, 0)),
  };
}

async function loadAgendaMonth() {
  const { dateFrom, dateTo } = agendaMonthRange();
  const page = await api.workouts({ dateFrom, dateTo });
  state.agendaWorkouts = page.items;
  renderAgenda();
}

async function moveAgendaMonth(offset) {
  const previousMonth = state.agendaMonth;
  state.agendaMonth = new Date(
    previousMonth.getFullYear(),
    previousMonth.getMonth() + offset,
    1,
  );
  try {
    await loadAgendaMonth();
  } catch (error) {
    state.agendaMonth = previousMonth;
    showToast(error.message, "error");
  }
}

function renderAgenda() {
  const year = state.agendaMonth.getFullYear();
  const month = state.agendaMonth.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstWeekday = (new Date(year, month, 1).getDay() + 6) % 7;
  const workoutsByDate = new Map();
  state.agendaWorkouts.forEach((workout) => {
    const workouts = workoutsByDate.get(workout.workout_date) || [];
    workouts.push(workout);
    workoutsByDate.set(workout.workout_date, workouts);
  });
  $("#agenda-month-label").textContent = new Intl.DateTimeFormat(undefined, {
    month: "long",
    year: "numeric",
  }).format(state.agendaMonth);
  $("#agenda-calendar").innerHTML = Array.from({ length: daysInMonth }, (_, index) => {
    const day = index + 1;
    const date = new Date(year, month, day, 12);
    const dateValue = isoDate(date);
    const workouts = workoutsByDate.get(dateValue) || [];
    const weekday = WEEKDAYS[(date.getDay() + 6) % 7];
    const isToday = dateValue === isoToday();
    const planDate = state.dueProgram
      ? state.dueProgram.is_started ? isoToday() : state.dueProgram.starts_on
      : null;
    const programBadge = dateValue === planDate && state.dueProgram
      ? `<div class="calendar-plan-badge ${state.dueProgram.step.step_type === "rest" ? "rest" : ""}"><span>${state.dueProgram.is_started ? "Today's plan" : "Program starts"}</span><strong>${escapeHtml(dueStepLabel(state.dueProgram.step))}</strong></div>`
      : "";
    const startStyle = day === 1 ? ` style="--calendar-start:${firstWeekday + 1}"` : "";
    return `<article class="calendar-day ${workouts.length ? "has-workouts" : ""} ${isToday ? "today" : ""}"${startStyle}>
      <div class="calendar-date">
        <span>${day}</span>
        <div><strong>${weekday}</strong><time datetime="${dateValue}">${new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" }).format(date)}</time></div>
      </div>
      <div class="calendar-workouts">
        ${programBadge}
        ${workouts.length
          ? workouts.map((workout) => `<button type="button" class="calendar-workout" data-action="edit-workout" data-id="${workout.id}">
              <strong>${escapeHtml(workout.title)}</strong>
              <span>${workout.total_sets} ${workout.total_sets === 1 ? "set" : "sets"} · ${compactNumber(workout.total_volume_kg, 1)} kg</span>
            </button>`).join("")
          : '<p class="calendar-empty">No workout logged</p>'}
      </div>
      <button type="button" class="calendar-add" data-action="log-calendar-day" data-date="${dateValue}" aria-label="Log workout on ${weekday}, ${dateValue}">+</button>
    </article>`;
  }).join("");
}

function programCard(program) {
  const archived = Boolean(program.archived_at);
  const currentStepId = program.cycle_state?.current_step_id;
  const programStarted = !program.is_active
    || state.dueProgram?.program_id !== program.id
    || state.dueProgram.is_started;
  const steps = program.steps.map((step) => `
    <li class="program-cycle-step ${step.id === currentStepId && program.is_active ? "due" : ""}">
      <span class="cycle-position">${String(step.position + 1).padStart(2, "0")}</span>
      <span class="cycle-type">${step.step_type === "rest" ? "○" : "↗"}</span>
      <div><strong>${escapeHtml(dueStepLabel(step))}</strong><small>${step.step_type === "rest" ? "Rest" : step.linked_workout_template_name ? `Saved · ${escapeHtml(step.linked_workout_template_name)}` : (step.muscle_groups || []).join(" · ") || "Any muscle"}</small></div>
      ${program.is_active && programStarted && step.id !== currentStepId
        ? `<button class="text-button" data-action="jump-program-step" data-id="${step.id}">Jump here</button>`
        : step.id === currentStepId && program.is_active ? `<b>${programStarted ? "Due" : "First"}</b>` : ""}
    </li>`).join("");
  return `<article class="program-card ${program.is_active ? "active" : ""} ${archived ? "archived" : ""}">
    <div class="program-card-head">
      <div><p class="eyebrow">${archived ? "Archived program" : program.is_active ? "Active program" : "Saved program"}</p><h2>${escapeHtml(program.name)}</h2></div>
      <span class="program-status">${program.is_active ? programStarted ? "In rotation" : "Scheduled" : archived ? "Archived" : `${program.steps.length} steps`}</span>
    </div>
    <p class="program-rule"><strong>Starts ${escapeHtml(localDate(program.starts_on))}.</strong> ${program.advance_on_any_workout ? "Any logged session advances a workout step." : "A linked saved workout must match; otherwise every planned muscle group must be logged."}</p>
    <ol class="program-cycle">${steps}</ol>
    <div class="program-card-actions">
      ${archived ? "" : `<button class="button secondary compact" data-action="edit-program" data-id="${program.id}">Edit</button>`}
      ${archived || program.is_active ? "" : `<button class="button primary compact" data-action="activate-program" data-id="${program.id}">Set active</button>`}
      ${archived ? "" : `<button class="text-button danger-text" data-action="archive-program" data-id="${program.id}">Archive</button>`}
    </div>
  </article>`;
}

function renderPrograms() {
  $("#program-list").innerHTML = state.programs.length
    ? state.programs.map(programCard).join("")
    : emptyState("No programs yet", "Create any ordered cycle of workouts and rest days.", false);
}

function programMuscleChoices(selected = []) {
  return MUSCLE_GROUPS.map((group) => `
    <label class="muscle-choice"><input type="checkbox" value="${group}" ${selected.includes(group) ? "checked" : ""}><span>${group}</span></label>
  `).join("");
}

function programTemplateOptions(selectedId = "") {
  const selectedTemplate = findWorkoutTemplate(selectedId);
  const templates = activeWorkoutTemplates();
  if (selectedTemplate?.archived_at && !templates.some((item) => item.id === selectedId)) {
    templates.push(selectedTemplate);
  }
  return `<option value="">No linked saved workout</option>${templates.map((template) =>
    `<option value="${template.id}" ${template.id === selectedId ? "selected" : ""}>${escapeHtml(template.name)}${template.archived_at ? " · archived" : ""}</option>`
  ).join("")}`;
}

function programStepRow(step = { step_type: "workout" }) {
  const rest = step.step_type === "rest";
  return `<article class="program-step-row ${rest ? "rest" : ""}" draggable="true" data-id="${step.id || ""}">
    <div class="program-step-order"><span class="drag-handle" title="Drag to reorder">⠿</span><b class="program-step-number"></b></div>
    <div class="program-step-fields">
      <div class="program-step-primary">
        <label>Type<select class="program-step-type"><option value="workout" ${rest ? "" : "selected"}>Workout</option><option value="rest" ${rest ? "selected" : ""}>Rest</option></select></label>
        <label>Label<input class="program-step-label" maxlength="100" value="${escapeHtml(step.label || "")}" placeholder="${rest ? "Recovery day" : "Chest + Back"}" ${rest ? "" : "required"}></label>
      </div>
      <label class="program-step-template">Saved workout (optional)<select>${programTemplateOptions(step.linked_workout_template_id || "")}</select></label>
      <div class="program-step-muscles"><span>Planned muscles (optional)</span><div>${programMuscleChoices(step.muscle_groups || [])}</div></div>
    </div>
    <div class="program-step-actions">
      <button class="icon-button" type="button" data-action="move-program-step-up" aria-label="Move step up">↑</button>
      <button class="icon-button" type="button" data-action="move-program-step-down" aria-label="Move step down">↓</button>
      <button class="icon-button danger" type="button" data-action="remove-program-step" aria-label="Remove step">×</button>
    </div>
  </article>`;
}

function renumberProgramSteps() {
  $$(".program-step-row", $("#program-step-list")).forEach((row, index) => {
    $(".program-step-number", row).textContent = String(index + 1).padStart(2, "0");
  });
}

function syncProgramStepRow(row) {
  const rest = $(".program-step-type", row).value === "rest";
  row.classList.toggle("rest", rest);
  const label = $(".program-step-label", row);
  label.required = !rest;
  label.placeholder = rest ? "Recovery day" : "Chest + Back";
  $(".program-step-template select", row).disabled = rest;
  $$(".program-step-muscles input", row).forEach((input) => { input.disabled = rest; });
}

function appendProgramStep(step) {
  $("#program-step-list").insertAdjacentHTML("beforeend", programStepRow(step));
  const row = $(".program-step-row:last-child", $("#program-step-list"));
  syncProgramStepRow(row);
  renumberProgramSteps();
}

function openProgramDialog(program = null) {
  const form = $("#program-form");
  form.reset();
  form.dataset.id = program?.id || "";
  $("#program-modal-title").textContent = program ? "Edit program" : "New program";
  $("#program-name").value = program?.name || "";
  $("#program-start-date").value = program?.starts_on || isoToday();
  $("#program-advance-any").checked = program?.advance_on_any_workout ?? true;
  $("#program-step-list").innerHTML = "";
  const steps = program?.steps?.length ? program.steps : [
    { step_type: "workout", label: "Workout" },
    { step_type: "rest", label: "Rest day" },
  ];
  steps.forEach(appendProgramStep);
  $("#program-dialog").showModal();
}

function collectProgramSteps() {
  return $$(".program-step-row", $("#program-step-list")).map((row) => {
    const stepType = $(".program-step-type", row).value;
    return {
      ...(row.dataset.id ? { id: row.dataset.id } : {}),
      step_type: stepType,
      label: $(".program-step-label", row).value.trim() || null,
      muscle_groups: stepType === "workout"
        ? $$(".program-step-muscles input:checked", row).map((input) => input.value)
        : null,
      linked_workout_template_id: stepType === "workout"
        ? $(".program-step-template select", row).value || null
        : null,
    };
  });
}

function renderMachines() {
  if (!state.machines.length) {
    $("#machine-grid").innerHTML = emptyState("Your gym floor is empty", "Add the machines and movements you train with.", false);
    return;
  }
  const groupedMachines = MUSCLE_GROUPS.map((muscleGroup) => ({
    muscleGroup,
    machines: state.machines
      .filter((machine) => machine.muscle_group === muscleGroup)
      .sort((left, right) => left.name.localeCompare(right.name)),
  })).filter((group) => group.machines.length);

  const collapseByDefault = window.matchMedia("(max-width: 700px)").matches;
  $("#machine-grid").innerHTML = groupedMachines.map(({ muscleGroup, machines }) => {
    const slug = muscleGroup.toLowerCase().replaceAll(" ", "-");
    return `
    <section class="muscle-section ${collapseByDefault ? "collapsed" : ""}" aria-labelledby="muscle-${slug}">
      <button class="muscle-section-heading" type="button" data-action="toggle-muscle" aria-expanded="${!collapseByDefault}" aria-controls="muscle-grid-${slug}">
        <div>
          <p class="eyebrow">Muscle group</p>
          <h2 id="muscle-${slug}">${escapeHtml(muscleGroup)}</h2>
        </div>
        <span class="muscle-summary"><span>${machines.length} ${machines.length === 1 ? "exercise" : "exercises"}</span><i aria-hidden="true">⌄</i></span>
      </button>
      <div id="muscle-grid-${slug}" class="machine-grid">
        ${machines.map(machineCard).join("")}
      </div>
    </section>
  `;
  }).join("");
}

function machineCard(machine) {
  return `
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
  `;
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

function renumberTemplateExercises() {
  $$(".template-exercise-row", $("#workout-template-exercise-list")).forEach((row, index) => {
    $(".template-exercise-number", row).textContent = String(index + 1).padStart(2, "0");
  });
}

function templateExerciseRow(exercise = {}) {
  const selectedMachine = state.machines.find((machine) => machine.id === exercise.machine_id);
  const selectedGroup = exercise.muscle_group || selectedMachine?.muscle_group || defaultMuscleGroup();
  return `<article class="template-exercise-row" draggable="true" data-id="${exercise.id || ""}">
    <div class="template-exercise-order"><span class="drag-handle" title="Drag to reorder">⠿</span><b class="template-exercise-number"></b></div>
    <div class="template-exercise-fields">
      <label>Muscle<select class="template-exercise-muscle" required>${muscleOptions(selectedGroup)}</select></label>
      <label>Exercise<select class="template-exercise-machine" required>${machineOptions(selectedGroup, exercise.machine_id)}</select></label>
      <label>Notes<input class="template-exercise-notes" maxlength="1000" value="${escapeHtml(exercise.notes || "")}" placeholder="Optional cues"></label>
    </div>
    <div class="template-exercise-actions">
      <button class="icon-button" type="button" data-action="move-template-exercise-up" aria-label="Move exercise up">↑</button>
      <button class="icon-button" type="button" data-action="move-template-exercise-down" aria-label="Move exercise down">↓</button>
      <button class="icon-button danger" type="button" data-action="remove-template-exercise" aria-label="Remove exercise">×</button>
    </div>
  </article>`;
}

function appendTemplateExercise(exercise = {}) {
  $("#workout-template-exercise-list").insertAdjacentHTML("beforeend", templateExerciseRow(exercise));
  renumberTemplateExercises();
}

function openWorkoutTemplateDialog(template = null) {
  if (!state.machines.some((machine) => machine.active)) {
    showToast("Add your first exercise before building a workout", "notice");
    openMachineDialog();
    return;
  }
  const form = $("#workout-template-form");
  form.reset();
  form.dataset.id = template?.id || "";
  $("#workout-template-modal-title").textContent = template ? "Edit workout" : "Build workout";
  $("#workout-template-name").value = template?.name || "";
  $("#workout-template-notes").value = template?.notes || "";
  $("#workout-template-exercise-list").innerHTML = "";
  (template?.exercises?.length ? template.exercises : [{}]).forEach(appendTemplateExercise);
  $("#workout-template-dialog").showModal();
}

function collectWorkoutTemplateExercises() {
  return $$(".template-exercise-row", $("#workout-template-exercise-list")).map((row) => ({
    ...(row.dataset.id ? { id: row.dataset.id } : {}),
    machine_id: $(".template-exercise-machine", row).value,
    notes: $(".template-exercise-notes", row).value.trim() || null,
  }));
}

function pickerExerciseSummary(template) {
  const names = template.exercises.map((exercise) => exercise.machine_name);
  return names.slice(0, 3).join(" · ") + (names.length > 3 ? ` · +${names.length - 3}` : "");
}

function openWorkoutPicker(workoutDate = null) {
  const selectedDate = workoutDate || isoToday();
  const due = state.dueProgram;
  const dueTemplate = selectedDate === isoToday() && due?.is_started
    && due.step.step_type === "workout"
    ? findWorkoutTemplate(due.step.linked_workout_template_id)
    : null;
  if (dueTemplate && !dueTemplate.archived_at) {
    openWorkoutDialog(null, { workoutDate: selectedDate, template: dueTemplate });
    return;
  }

  const templates = activeWorkoutTemplates();
  const dialog = $("#workout-picker-dialog");
  dialog.dataset.workoutDate = selectedDate;
  $("#workout-picker-date").textContent = localDate(selectedDate, { weekday: "long" });
  $("#workout-picker-list").innerHTML = `
    ${templates.map((template) => `<button class="workout-picker-option" type="button" data-action="select-workout-template" data-id="${template.id}">
      <span>↗</span><div><strong>${escapeHtml(template.name)}</strong><small>${escapeHtml(pickerExerciseSummary(template))}</small></div><b>→</b>
    </button>`).join("")}
    <button class="workout-picker-option" type="button" data-action="select-blank-workout">
      <span>＋</span><div><strong>Blank / custom session</strong><small>Start empty and choose today's exercises manually.</small></div><b>→</b>
    </button>`;
  dialog.showModal();
}

function defaultMuscleGroup() {
  return state.machines.find((machine) => machine.active)?.muscle_group || MUSCLE_GROUPS[0];
}

function dueMuscleGroup(workoutDate = null) {
  const due = state.dueProgram;
  const isToday = !workoutDate || workoutDate === isoToday();
  if (!isToday || !due?.is_started || due.step.step_type !== "workout") return null;
  return (due.step.muscle_groups || []).find((group) =>
    state.machines.some((machine) => machine.active && machine.muscle_group === group)
  ) || null;
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

function openWorkoutDialog(
  workout = null,
  { repeat = false, workoutDate = null, template = null } = {},
) {
  if (!state.machines.some((machine) => machine.active)) {
    showToast("Add your first machine before logging a workout", "notice");
    openMachineDialog();
    return;
  }
  const form = $("#workout-form");
  form.reset();
  form.dataset.id = repeat ? "" : workout?.id || "";
  form.dataset.mode = repeat ? "repeat" : workout ? "edit" : "create";
  const historicalTemplate = workout?.template_id ? findWorkoutTemplate(workout.template_id) : null;
  const sourceTemplate = template
    || (repeat && historicalTemplate && !historicalTemplate.archived_at ? historicalTemplate : null);
  form.dataset.templateId = sourceTemplate?.id || "";
  $("#workout-modal-title").textContent = repeat ? "Repeat workout" : workout ? "Edit workout" : "Log workout";
  const useDuePlan = !workout && !repeat && (!workoutDate || workoutDate === isoToday())
    && state.dueProgram?.is_started && state.dueProgram.step.step_type === "workout";
  const plannedGroup = useDuePlan ? dueMuscleGroup(workoutDate) : null;
  const hint = $("#workout-plan-hint");
  const sourceForDisplay = sourceTemplate || historicalTemplate;
  hint.classList.toggle("hidden", !useDuePlan && !sourceForDisplay);
  hint.innerHTML = [
    useDuePlan ? `<strong>Due now:</strong> ${escapeHtml(dueStepLabel(state.dueProgram.step))}${plannedGroup ? ` · ${escapeHtml(plannedGroup)} preselected` : ""}` : "",
    sourceForDisplay ? `<strong>Started from ${escapeHtml(sourceForDisplay.name)}.</strong> Changes here affect only this dated session.` : "",
  ].filter(Boolean).join("<br>");
  $("#workout-date").value = repeat
    ? isoToday()
    : workout?.workout_date || workoutDate || isoToday();
  $("#workout-title").value = workout?.title || sourceTemplate?.name || (useDuePlan ? dueStepLabel(state.dueProgram.step) : "Workout");
  $("#workout-duration").value = workout?.duration_minutes || "";
  $("#workout-notes").value = workout?.notes || "";
  const sourceEntries = workout?.entries?.length
    ? workout.entries
    : sourceTemplate?.exercises?.map((exercise) => ({
        machine_id: exercise.machine_id,
        muscle_group: exercise.muscle_group,
        notes: exercise.notes,
      }));
  $("#entry-list").innerHTML = sourceEntries?.length
    ? sourceEntries.map(entryRow).join("")
    : entryRow(plannedGroup ? { muscle_group: plannedGroup } : {});
  renumberSets($("#entry-list"));
  $("#workout-dialog").showModal();
}

function collectWorkout() {
  return {
    ...($("#workout-form").dataset.templateId
      ? { template_id: $("#workout-form").dataset.templateId }
      : {}),
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

$("#workout-template-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const exercises = collectWorkoutTemplateExercises();
  if (!exercises.length) {
    showToast("A saved workout needs at least one exercise", "error");
    return;
  }
  const machineIds = exercises.map((exercise) => exercise.machine_id);
  if (new Set(machineIds).size !== machineIds.length) {
    showToast("Each exercise can appear only once in a saved workout", "error");
    return;
  }
  setBusy(form, true);
  const metadata = {
    name: $("#workout-template-name").value.trim(),
    notes: $("#workout-template-notes").value.trim() || null,
  };
  try {
    if (form.dataset.id) {
      await api.updateWorkoutTemplate(form.dataset.id, metadata);
      await api.updateWorkoutTemplateExercises(form.dataset.id, exercises);
    } else {
      await api.createWorkoutTemplate({ ...metadata, exercises });
    }
    $("#workout-template-dialog").close();
    await refreshAfterMutation(form.dataset.id ? "Saved workout updated" : "Saved workout created");
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

$("#program-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  if (!form.reportValidity()) return;
  const steps = collectProgramSteps();
  if (!steps.length) {
    showToast("A program needs at least one step", "error");
    return;
  }
  setBusy(form, true);
  const metadata = {
    name: $("#program-name").value.trim(),
    advance_on_any_workout: $("#program-advance-any").checked,
    starts_on: $("#program-start-date").value,
  };
  try {
    if (form.dataset.id) {
      await api.updateProgram(form.dataset.id, metadata);
      await api.updateProgramSteps(form.dataset.id, steps);
    } else {
      await api.createProgram({ ...metadata, steps });
    }
    $("#program-dialog").close();
    await refreshAfterMutation(form.dataset.id ? "Program updated" : "Program created");
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
  if (button.matches(".js-new-workout")) openWorkoutPicker();
  if (button.id === "new-workout-template-button" || button.dataset.action === "new-workout-template") openWorkoutTemplateDialog();
  if (button.id === "new-machine-button") openMachineDialog();
  if (button.id === "new-program-button") openProgramDialog();
  if (button.dataset.closeDialog) $(`#${button.dataset.closeDialog}`).close();

  const { action, id } = button.dataset;
  if (action === "select-workout-template") {
    const picker = $("#workout-picker-dialog");
    const workoutDate = picker.dataset.workoutDate || isoToday();
    picker.close();
    openWorkoutDialog(null, { workoutDate, template: findWorkoutTemplate(id) });
  }
  if (action === "select-blank-workout") {
    const picker = $("#workout-picker-dialog");
    const workoutDate = picker.dataset.workoutDate || isoToday();
    picker.close();
    openWorkoutDialog(null, { workoutDate });
  }
  if (action === "log-workout-template") {
    openWorkoutDialog(null, { workoutDate: isoToday(), template: findWorkoutTemplate(id) });
  }
  if (action === "edit-workout-template") {
    openWorkoutTemplateDialog(findWorkoutTemplate(id));
  }
  if (action === "archive-workout-template") {
    if (!window.confirm("Archive this saved workout? Logged session snapshots will stay intact.")) return;
    try {
      await api.archiveWorkoutTemplate(id);
      await refreshAfterMutation("Saved workout archived");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "remove-template-exercise") {
    const rows = $$(".template-exercise-row", $("#workout-template-exercise-list"));
    if (rows.length === 1) showToast("A saved workout needs at least one exercise", "notice");
    else {
      button.closest(".template-exercise-row").remove();
      renumberTemplateExercises();
    }
  }
  if (action === "move-template-exercise-up" || action === "move-template-exercise-down") {
    const row = button.closest(".template-exercise-row");
    const sibling = action.endsWith("up") ? row.previousElementSibling : row.nextElementSibling;
    if (sibling) {
      if (action.endsWith("up")) sibling.before(row);
      else sibling.after(row);
      renumberTemplateExercises();
    }
  }
  if (action === "add-program-workout") appendProgramStep({ step_type: "workout", label: "Workout" });
  if (action === "add-program-rest") appendProgramStep({ step_type: "rest", label: "Rest day" });
  if (action === "remove-program-step") {
    const rows = $$(".program-step-row", $("#program-step-list"));
    if (rows.length === 1) showToast("A program needs at least one step", "notice");
    else {
      button.closest(".program-step-row").remove();
      renumberProgramSteps();
    }
  }
  if (action === "move-program-step-up" || action === "move-program-step-down") {
    const row = button.closest(".program-step-row");
    const sibling = action.endsWith("up") ? row.previousElementSibling : row.nextElementSibling;
    if (sibling) {
      if (action.endsWith("up")) sibling.before(row);
      else sibling.after(row);
      renumberProgramSteps();
    }
  }
  if (action === "edit-program") {
    openProgramDialog(state.programs.find((program) => program.id === id));
  }
  if (action === "activate-program") {
    const program = state.programs.find((item) => item.id === id);
    if (!program) return;
    if (!window.confirm(`Set this program active from ${localDate(program.starts_on)}? Its cycle will restart at step 1.`)) return;
    try {
      await api.activateProgram(id, program.starts_on);
      await refreshAfterMutation(`Program activated from ${localDate(program.starts_on)}`);
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "archive-program") {
    if (!window.confirm("Archive this program? Its steps and cycle history will be kept.")) return;
    try {
      await api.archiveProgram(id);
      await refreshAfterMutation("Program archived");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "skip-program-step") {
    if (!window.confirm("Skip the currently due step?")) return;
    try {
      await api.advanceProgram();
      await refreshAfterMutation("Moved to the next program step");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "jump-program-step") {
    if (!window.confirm("Jump the active cycle to this step?")) return;
    try {
      await api.advanceProgram(id);
      await refreshAfterMutation("Program cycle realigned");
    } catch (error) { showToast(error.message, "error"); }
  }
  if (action === "toggle-muscle") {
    const section = button.closest(".muscle-section");
    const collapsed = section.classList.toggle("collapsed");
    button.setAttribute("aria-expanded", String(!collapsed));
  }
  if (action === "previous-month") await moveAgendaMonth(-1);
  if (action === "next-month") await moveAgendaMonth(1);
  if (action === "log-calendar-day") {
    openWorkoutPicker(button.dataset.date);
  }
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
    openWorkoutDialog(findWorkout(id), { repeat: true });
  }
  if (action === "edit-workout") openWorkoutDialog(findWorkout(id));
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
  if (event.target.matches(".entry-muscle")) {
    const entry = event.target.closest(".entry-card");
    $(".entry-machine", entry).innerHTML = machineOptions(event.target.value);
  }
  if (event.target.matches(".template-exercise-muscle")) {
    const row = event.target.closest(".template-exercise-row");
    $(".template-exercise-machine", row).innerHTML = machineOptions(event.target.value);
  }
  if (event.target.matches(".program-step-type")) {
    syncProgramStepRow(event.target.closest(".program-step-row"));
  }
  if (event.target.matches(".program-step-template select")) {
    const row = event.target.closest(".program-step-row");
    const template = findWorkoutTemplate(event.target.value);
    const label = $(".program-step-label", row);
    if (template && (!label.value.trim() || label.value.trim() === "Workout")) {
      label.value = template.name;
    }
  }
});

$("#add-exercise-button").addEventListener("click", () => {
  $("#entry-list").insertAdjacentHTML("beforeend", entryRow());
  renumberSets($("#entry-list"));
});

$("#add-template-exercise-button").addEventListener("click", () => {
  appendTemplateExercise();
});

$("#show-archived").addEventListener("change", async (event) => {
  try {
    state.machines = await api.machines(event.target.checked);
    renderMachines();
  } catch (error) { showToast(error.message, "error"); }
});

let draggedProgramStep = null;
$("#program-step-list").addEventListener("dragstart", (event) => {
  draggedProgramStep = event.target.closest(".program-step-row");
  if (!draggedProgramStep) return;
  draggedProgramStep.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
});

$("#program-step-list").addEventListener("dragover", (event) => {
  if (!draggedProgramStep) return;
  event.preventDefault();
  const rows = $$(".program-step-row:not(.dragging)", $("#program-step-list"));
  const next = rows.find((row) => event.clientY < row.getBoundingClientRect().top + row.offsetHeight / 2);
  if (next) $("#program-step-list").insertBefore(draggedProgramStep, next);
  else $("#program-step-list").append(draggedProgramStep);
});

$("#program-step-list").addEventListener("drop", (event) => {
  event.preventDefault();
  renumberProgramSteps();
});

$("#program-step-list").addEventListener("dragend", () => {
  draggedProgramStep?.classList.remove("dragging");
  draggedProgramStep = null;
  renumberProgramSteps();
});

let draggedTemplateExercise = null;
$("#workout-template-exercise-list").addEventListener("dragstart", (event) => {
  draggedTemplateExercise = event.target.closest(".template-exercise-row");
  if (!draggedTemplateExercise) return;
  draggedTemplateExercise.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
});

$("#workout-template-exercise-list").addEventListener("dragover", (event) => {
  if (!draggedTemplateExercise) return;
  event.preventDefault();
  const rows = $$(".template-exercise-row:not(.dragging)", $("#workout-template-exercise-list"));
  const next = rows.find((row) => event.clientY < row.getBoundingClientRect().top + row.offsetHeight / 2);
  if (next) $("#workout-template-exercise-list").insertBefore(draggedTemplateExercise, next);
  else $("#workout-template-exercise-list").append(draggedTemplateExercise);
});

$("#workout-template-exercise-list").addEventListener("drop", (event) => {
  event.preventDefault();
  renumberTemplateExercises();
});

$("#workout-template-exercise-list").addEventListener("dragend", () => {
  draggedTemplateExercise?.classList.remove("dragging");
  draggedTemplateExercise = null;
  renumberTemplateExercises();
});

$$('dialog').forEach((dialog) => dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
}));

initialize();
