// Profile page: the student's projects (owner: Hasan).
// Add form, list of project cards, inline edit, topic checkboxes.
//
// profile.js calls setupProjects() once it knows the student and the
// student's topics. After every change we ask the API again, because
// the database is the source of truth.

import { createButton, requestJson, showMessage } from "./http.js";

const PROJECT_STATUSES = ["In progress", "Completed"];
const NO_PROJECTS_TEXT = "Hozircha loyihalar yo'q";
const NO_TOPICS_TEXT = "Avval mavzu qo'shing";

const elements = {
    form: document.getElementById("project-form"),
    formTopics: document.getElementById("project-form-topics"),
    error: document.getElementById("project-error"),
    list: document.getElementById("project-list"),
};

// Filled by setupProjects(); every function below reads it.
const state = { studentId: null, topics: [], onChanged: async () => {} };


// ===== API =====

const projectsApi = {
    list: (studentId) => requestJson(`/students/${studentId}/projects`),
    add: (studentId, project) =>
        requestJson(`/students/${studentId}/projects`, {
            method: "POST",
            body: JSON.stringify(project),
        }),
    update: (studentId, projectId, changes) =>
        requestJson(`/students/${studentId}/projects/${projectId}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
        }),
};


// ===== Small builders =====

// One checkbox per topic of this student; value = topic record ID.
function createTopicCheckboxes(selectedIds = []) {
    const box = document.createElement("div");
    box.className = "topic-checkboxes";
    if (state.topics.length === 0) {
        box.textContent = NO_TOPICS_TEXT;
        return box;
    }
    for (const topic of state.topics) {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.value = String(topic.id);
        checkbox.checked = selectedIds.includes(topic.id);
        label.append(checkbox, ` ${topic.name}`);
        box.append(label);
    }
    return box;
}

function readCheckedTopicIds(container) {
    return [...container.querySelectorAll("input[type=checkbox]:checked")]
        .map((checkbox) => Number(checkbox.value));
}

function createStatusSelect(selectedStatus) {
    const select = document.createElement("select");
    for (const status of PROJECT_STATUSES) {
        const option = new Option(status, status);
        option.selected = status === selectedStatus;
        select.append(option);
    }
    return select;
}

function createTextInput(value, placeholder) {
    const input = document.createElement("input");
    input.value = value ?? "";
    input.placeholder = placeholder;
    input.setAttribute("aria-label", placeholder);
    return input;
}

// An empty link box means "no link", which the API expects as null.
function emptyToNull(text) {
    return text.trim() === "" ? null : text;
}

function topicNames(topicIds) {
    return state.topics
        .filter((topic) => topicIds.includes(topic.id))
        .map((topic) => topic.name)
        .join(", ");
}


// ===== Rendering =====

function renderProjects(projects) {
    elements.list.replaceChildren();
    if (projects.length === 0) {
        elements.list.textContent = NO_PROJECTS_TEXT;
        return;
    }
    for (const project of projects) {
        elements.list.append(createProjectCard(project));
    }
}

// textContent (not innerHTML) so user text is never run as HTML (XSS).
function createProjectCard(project) {
    const card = document.createElement("article");
    card.className = "project-card";

    const title = document.createElement("h3");
    title.textContent = `${project.name} — ${project.status}`;

    const description = document.createElement("p");
    description.className = "project-description";
    description.textContent = project.description;

    const contribution = document.createElement("p");
    contribution.textContent = `O'z hissam: ${project.contribution}`;

    const topics = document.createElement("p");
    topics.className = "project-topics";
    topics.textContent = topicNames(project.topic_record_ids);

    card.append(title, description, contribution, topics);
    if (project.link) {
        card.append(createLink(project.link));
    }
    card.append(createButton("Tahrirlash", "button-small", () =>
        card.replaceWith(createEditForm(project))
    ));
    return card;
}

function createLink(url) {
    const link = document.createElement("a");
    link.href = url;  // the backend only accepts http:// or https://
    link.textContent = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
}

function createEditForm(project) {
    const card = document.createElement("article");
    card.className = "project-card editing";

    const nameInput = createTextInput(project.name, "Loyiha nomi");
    const descriptionInput =
        createTextInput(project.description, "Loyiha tavsifi");
    const contributionInput =
        createTextInput(project.contribution, "O'z hissam");
    const linkInput = createTextInput(project.link, "https://...");
    const statusSelect = createStatusSelect(project.status);
    const topicBox = createTopicCheckboxes(project.topic_record_ids);

    const save = () => handleUpdateProject(project.id, {
        name: nameInput.value,
        description: descriptionInput.value,
        contribution: contributionInput.value,
        link: emptyToNull(linkInput.value),
        status: statusSelect.value,
        topic_record_ids: readCheckedTopicIds(topicBox),
    });
    const cancel = () => card.replaceWith(createProjectCard(project));

    card.append(
        nameInput,
        descriptionInput,
        contributionInput,
        linkInput,
        statusSelect,
        topicBox,
        createButton("Saqlash", "button-small", save),
        createButton("Bekor", "button-small button-secondary", cancel),
    );
    return card;
}


// ===== Loading and saving =====

async function loadProjects() {
    try {
        renderProjects(await projectsApi.list(state.studentId));
        showMessage(elements.error, "");
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}

function readProjectForm() {
    const formData = new FormData(elements.form);
    return {
        name: formData.get("name"),
        description: formData.get("description"),
        contribution: formData.get("contribution"),
        link: emptyToNull(formData.get("link")),
        status: formData.get("status"),
        topic_record_ids: readCheckedTopicIds(elements.formTopics),
    };
}

// After a save, profile.js reloads the whole profile: the skills can
// change ("Learned" -> "Applied in a project") and it calls
// setupProjects() again, which redraws this list.
async function refreshAfterChange() {
    await state.onChanged();
}

async function handleAddProject(event) {
    event.preventDefault();  // stop the browser from reloading the page
    showMessage(elements.error, "");
    try {
        await projectsApi.add(state.studentId, readProjectForm());
        elements.form.reset();
        await refreshAfterChange();
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}

async function handleUpdateProject(projectId, changes) {
    showMessage(elements.error, "");
    try {
        await projectsApi.update(state.studentId, projectId, changes);
        await refreshAfterChange();
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}


// ===== Start (called by profile.js) =====

// topics = this student's topic records: [{ id, name }, ...]
// onChanged = function that reloads the profile and its skills.
export async function setupProjects({ studentId, topics, onChanged }) {
    const isFirstSetup = state.studentId === null;
    state.studentId = studentId;
    state.topics = topics;
    state.onChanged = onChanged;
    elements.formTopics.replaceChildren(createTopicCheckboxes());
    if (isFirstSetup) {
        elements.form.addEventListener("submit", handleAddProject);
    }
    await loadProjects();
}
