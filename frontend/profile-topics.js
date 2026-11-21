// Profile page: the student's topics (owner: Bahodirjon).
// Add a topic from the catalogue, switch Learning <-> Completed.

import { createButton, requestJson, showMessage } from "./http.js";

const STATUS_LEARNING = "Learning";
const STATUS_COMPLETED = "Completed";
const NO_TOPICS_TEXT = "Hozircha mavzular yo'q";
const ALL_ADDED_TEXT = "Hamma mavzu qo'shilgan";
const TABLE_COLUMN_COUNT = 4;

const elements = {
    form: document.getElementById("topic-form"),
    select: document.getElementById("topic-select"),
    error: document.getElementById("topic-error"),
    list: document.getElementById("topic-list"),
};

// Filled by setupTopics(). The catalogue never changes while the
// page is open, so it is loaded only once.
const state = { studentId: null, catalogue: null, onChanged: async () => {} };


// ===== API =====

const topicsApi = {
    catalogue: () => requestJson("/topics"),
    add: (studentId, topicId) =>
        requestJson(`/students/${studentId}/topics`, {
            method: "POST",
            body: JSON.stringify({ topic_id: topicId }),
        }),
    setStatus: (studentId, recordId, status) =>
        requestJson(`/students/${studentId}/topics/${recordId}`, {
            method: "PATCH",
            body: JSON.stringify({ status }),
        }),
};


// ===== Rendering =====

// Offer only the topics the student does not have yet.
function fillCatalogueSelect(records) {
    const takenIds = new Set(records.map((record) => record.topic_id));
    const available = state.catalogue.filter(
        (topic) => !takenIds.has(topic.id)
    );
    elements.select.replaceChildren(
        ...available.map((topic) =>
            new Option(`${topic.name} (${topic.skill})`, topic.id)
        )
    );
    elements.select.disabled = available.length === 0;
    if (available.length === 0) {
        elements.select.append(new Option(ALL_ADDED_TEXT, ""));
    }
}

function nextStatus(status) {
    return status === STATUS_COMPLETED ? STATUS_LEARNING : STATUS_COMPLETED;
}

function createCell(content) {
    const cell = document.createElement("td");
    cell.append(content);  // a string is added as text, never as HTML
    return cell;
}

function createStatusBadge(status) {
    const badge = document.createElement("span");
    badge.className = `badge status-${status}`;
    badge.textContent = status;
    return badge;
}

function createTopicRow(record) {
    const row = document.createElement("tr");
    const target = nextStatus(record.status);
    const toggle = createButton(
        `${target} qilish`,
        "button-small",
        () => handleSetStatus(record.id, target),
    );
    row.append(
        createCell(record.topic_name),
        createCell(record.skill),
        createCell(createStatusBadge(record.status)),
        createCell(toggle),
    );
    return row;
}

function renderTopics(records) {
    elements.list.replaceChildren();
    if (records.length === 0) {
        const row = document.createElement("tr");
        row.className = "empty-row";
        const cell = createCell(NO_TOPICS_TEXT);
        cell.colSpan = TABLE_COLUMN_COUNT;
        row.append(cell);
        elements.list.append(row);
        return;
    }
    elements.list.append(...records.map(createTopicRow));
}


// ===== Event handlers =====

async function handleAddTopic(event) {
    event.preventDefault();  // stop the browser from reloading the page
    showMessage(elements.error, "");
    try {
        await topicsApi.add(state.studentId, Number(elements.select.value));
        await state.onChanged();
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}

async function handleSetStatus(recordId, status) {
    showMessage(elements.error, "");
    try {
        await topicsApi.setStatus(state.studentId, recordId, status);
        await state.onChanged();
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}


// ===== Start (called by profile.js) =====

// records = this student's topics from GET /profile.
// onChanged = function that reloads the profile and its skills.
export async function setupTopics({ studentId, records, onChanged }) {
    const isFirstSetup = state.catalogue === null;
    state.studentId = studentId;
    state.onChanged = onChanged;
    if (isFirstSetup) {
        state.catalogue = await topicsApi.catalogue();
        elements.form.addEventListener("submit", handleAddTopic);
    }
    fillCatalogueSelect(records);
    renderTopics(records);
}
