// Frontend logic: talks to the FastAPI backend and updates the page.
// The database is the source of truth, so after every change we ask
// the API again instead of trusting what is already on the screen.

const API_BASE_URL = "/api";
const STUDENT_STATUSES = ["Active", "Paused", "Completed"];
const TOPIC_STATUSES = ["Learning", "Completed"];
const PROJECT_STATUSES = ["In progress", "Completed"];
const NO_SCORES_TEXT = "No scores yet.";
const NO_STUDENTS_TEXT = "Hozircha o'quvchilar yo'q";
const NO_MATCH_TEXT = "Qidiruvga mos o'quvchi topilmadi";
const TABLE_COLUMN_COUNT = 7;

const elements = {
    form: document.getElementById("student-form"),
    formError: document.getElementById("form-error"),
    formSuccess: document.getElementById("form-success"),
    statusFilter: document.getElementById("status-filter"),
    searchInput: document.getElementById("search-input"),
    tableBody: document.getElementById("students-body"),
    tableError: document.getElementById("table-error"),
    totalCount: document.getElementById("total-count"),
    activeCount: document.getElementById("active-count"),
    averageScore: document.getElementById("average-score"),
    listSection: document.getElementById("list-section"),
    addSection: document.getElementById("add-section"),
    filterSection: document.getElementById("filter_section"),
    profileSection: document.getElementById("profile-section"),
    profileHeading: document.getElementById("profile-heading"),
    profileBack: document.getElementById("profile-back"),
    profileError: document.getElementById("profile-error"),
    profileMessage: document.getElementById("profile-message"),
    profileContent: document.getElementById("profile-content"),
};

// Students returned by the last API call; searching filters this in the browser.
let studentsCache = [];
let catalogueCache = [];
let currentProfileId = null;


// ===== API: the only code that calls fetch() =====

async function requestJson(path, options = {}) {
    const response = await fetch(API_BASE_URL + path, {
        headers: { "Content-Type": "application/json" },
        ...options,
    });
    const body = await response.json();
    if (!response.ok) {
        throw new Error(formatErrorDetail(body.detail));
    }
    return body;
}

// FastAPI sends validation errors (422) as a list, other errors as text.
function formatErrorDetail(detail) {
    if (!Array.isArray(detail)) {
        return String(detail);
    }
    return detail
        .map((error) => `${error.loc.at(-1)}: ${error.msg}`)
        .join("; ");
}

const api = {
    listStudents: (status) => {
        const query = status ? `?status=${encodeURIComponent(status)}` : "";
        return requestJson(`/students${query}`);
    },
    addStudent: (student) =>
        requestJson("/students", {
            method: "POST",
            body: JSON.stringify(student),
        }),
    updateStudent: (id, changes) =>
        requestJson(`/students/${id}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
        }),
    getSummary: () => requestJson("/summary"),
    getCatalogue: () => requestJson("/topics/catalogue"),
    addTopic: (studentId, topic) =>
        requestJson(`/students/${studentId}/topics`, {
            method: "POST",
            body: JSON.stringify(topic),
        }),
    updateTopic: (studentId, topicId, changes) =>
        requestJson(`/students/${studentId}/topics/${topicId}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
        }),
    addProject: (studentId, project) =>
        requestJson(`/students/${studentId}/projects`, {
            method: "POST",
            body: JSON.stringify(project),
        }),
    updateProject: (studentId, projectId, changes) =>
        requestJson(`/students/${studentId}/projects/${projectId}`, {
            method: "PATCH",
            body: JSON.stringify(changes),
        }),
    getProfile: (studentId) =>
        requestJson(`/students/${studentId}/profile`),
};


// ===== Small helpers =====

// An empty score box means "no score", which the API expects as null.
function parseScore(rawValue) {
    return rawValue.trim() === "" ? null : Number(rawValue);
}

function formatScore(score) {
    return score === null ? "—" : String(score);
}

function showMessage(element, text) {
    element.textContent = text;  // empty text hides it (see .error:empty)
}

// textContent (not innerHTML) so user text is shown as text, never run as HTML.
function createCell(content) {
    const cell = document.createElement("td");
    if (content instanceof Node) {
        cell.append(content);
    } else {
        cell.textContent = content;
    }
    return cell;
}

function createStatusBadge(status) {
    const badge = document.createElement("span");
    badge.className = `badge status-${status}`;
    badge.textContent = status;
    return badge;
}

function createButton(label, className, onClick, type = "button") {
    const button = document.createElement("button");
    button.type = type;
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
}

function createSelect(values, selected, multiple = false) {
    const select = document.createElement("select");
    select.multiple = multiple;
    for (const value of values) {
        const option = new Option(value.label, value.value);
        option.selected = multiple
            ? selected.includes(value.value)
            : value.value === selected;
        select.append(option);
    }
    return select;
}

function createStatusSelect(selectedStatus) {
    return createSelect(
        STUDENT_STATUSES.map((status) => ({ label: status, value: status })),
        selectedStatus
    );
}

function createLink(text, url) {
    const link = document.createElement("a");
    link.href = url;
    link.textContent = text;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
}

function createEmptyRow(text, columnCount) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = createCell(text);
    cell.colSpan = columnCount;
    row.append(cell);
    return row;
}

function createCard(titleText) {
    const card = document.createElement("section");
    card.className = "profile-card";
    const heading = document.createElement("h3");
    heading.textContent = titleText;
    card.append(heading);
    return card;
}

function createField(labelText, input) {
    const wrapper = document.createElement("div");
    wrapper.className = "field";
    const label = document.createElement("label");
    label.textContent = labelText;
    label.htmlFor = input.id;
    wrapper.append(label, input);
    return wrapper;
}

function createInput(id, value = "", type = "text", placeholder = "") {
    const input = document.createElement("input");
    input.id = id;
    input.type = type;
    input.value = value;
    input.placeholder = placeholder;
    return input;
}

function createEmptyNote(text) {
    const note = document.createElement("p");
    note.className = "empty-note";
    note.textContent = text;
    return note;
}


// ===== Rendering the student table =====

function renderStudents(students, emptyText = NO_STUDENTS_TEXT) {
    elements.tableBody.replaceChildren();
    if (students.length === 0) {
        elements.tableBody.append(createEmptyRow(emptyText, TABLE_COLUMN_COUNT));
        return;
    }
    for (const student of students) {
        elements.tableBody.append(createStudentRow(student));
    }
}

function createStudentRow(student) {
    const row = document.createElement("tr");
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(
        createButton("View Profile", "button-small", () => {
            window.location.hash = `#profile/${student.id}`;
        }),
        createButton("Tahrirlash", "button-small", () =>
            row.replaceWith(createEditRow(student))
        )
    );
    row.append(
        createCell(String(student.id)),
        createCell(student.name),
        createCell(student.topic),
        createCell(createStatusBadge(student.status)),
        createCell(formatScore(student.score)),
        createCell(actions),
    );
    return row;
}

function createEditRow(student) {
    const row = document.createElement("tr");
    row.className = "editing-row";

    const topicInput = createInput("edit-topic", student.topic);
    const statusSelect = createStatusSelect(student.status);
    const scoreInput = createInput(
        "edit-score", student.score ?? "", "number"
    );
    scoreInput.min = "0";
    scoreInput.max = "100";

    const saveChanges = () =>
        handleUpdateStudent(student.id, {
            topic: topicInput.value,
            status: statusSelect.value,
            score: parseScore(scoreInput.value),
        });
    const cancelEdit = () => row.replaceWith(createStudentRow(student));

    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(
        createButton("Saqlash", "button-small", saveChanges),
        createButton("Bekor", "button-small button-secondary", cancelEdit),
    );

    row.append(
        createCell(String(student.id)),
        createCell(student.name),
        createCell(topicInput),
        createCell(statusSelect),
        createCell(scoreInput),
        createCell(actions),
    );
    return row;
}

function renderSummary(summary) {
    elements.totalCount.textContent = summary.total_students;
    elements.activeCount.textContent = summary.active_students;
    elements.averageScore.textContent =
        summary.average_score === null ? NO_SCORES_TEXT : summary.average_score;
}


// ===== Loading data from the API =====

// Case-insensitive search in the name column.
function matchesSearch(student, query) {
    if (!query) {
        return true;
    }
    const needle = query.toLocaleLowerCase();
    return student.name.toLocaleLowerCase().includes(needle);
}

function renderFilteredStudents() {
    const query = elements.searchInput.value.trim();
    const filtered = studentsCache.filter((student) =>
        matchesSearch(student, query)
    );
    renderStudents(filtered, query ? NO_MATCH_TEXT : NO_STUDENTS_TEXT);
}

async function loadStudents() {
    try {
        studentsCache = await api.listStudents(elements.statusFilter.value);
        renderFilteredStudents();
        showMessage(elements.tableError, "");
    } catch (error) {
        showMessage(elements.tableError, error.message);
    }
}

async function loadSummary() {
    try {
        renderSummary(await api.getSummary());
    } catch (error) {
        showMessage(elements.tableError, error.message);
    }
}

async function loadCatalogue() {
    try {
        catalogueCache = await api.getCatalogue();
    } catch (error) {
        showMessage(elements.profileError, error.message);
    }
}

async function refreshPage() {
    await Promise.all([
        loadStudents(),
        loadSummary(),
        loadCatalogue(),
    ]);
}


// ===== Profile page =====

function setProfileRoute(isProfile) {
    for (const section of [
        elements.listSection,
        elements.addSection,
        elements.filterSection,
    ]) {
        section.hidden = isProfile;
    }
    elements.profileSection.hidden = !isProfile;
}

async function loadProfile(studentId) {
    currentProfileId = studentId;
    showMessage(elements.profileError, "");
    showMessage(elements.profileMessage, "");
    try {
        const result = await api.getProfile(studentId);
        if (currentProfileId !== studentId) {
            return;  // the user navigated away while the request was running
        }
        renderProfile(result);
    } catch (error) {
        elements.profileContent.replaceChildren();
        showMessage(elements.profileError, error.message);
    }
}

async function reloadProfile() {
    if (currentProfileId !== null) {
        await loadProfile(currentProfileId);
        await refreshPage();
    }
}

async function handleRouteChange() {
    const match = /^#profile\/(\d+)$/.exec(window.location.hash);
    if (!match) {
        const wasProfile = currentProfileId !== null;
        currentProfileId = null;
        setProfileRoute(false);
        if (wasProfile) {
            await refreshPage();
        }
        return;
    }
    setProfileRoute(true);
    await loadProfile(Number(match[1]));
}

function renderProfile(result) {
    elements.profileHeading.textContent =
        `${result.student.name} · ID ${result.student.id}`;
    elements.profileContent.replaceChildren(
        createProfileInfo(result),
        createSkillsCard(result.skills),
        createTopicsCard(result),
        createProjectsCard(result),
    );
}

function createProfileInfo(result) {
    const card = createCard("O'quvchi ma'lumotlari");
    const grid = document.createElement("div");
    grid.className = "profile-grid";
    const summary = result.summary;
    const lines = [
        `Ism: ${result.student.name}`,
        `Joriy mavzu: ${result.student.topic}`,
        `Holat: ${result.student.status}`,
        `Baho: ${formatScore(result.student.score)}`,
        `Tugatilgan mavzular: ${summary.completed_topics}`,
        `Tugatilgan loyihalar: ${summary.completed_projects}`,
        `O'rgangan ko'nikmalar: ${summary.learned_skills}`,
    ];
    for (const line of lines) {
        const item = document.createElement("div");
        item.className = "profile-card";
        const text = document.createElement("p");
        text.textContent = line;
        item.append(text);
        grid.append(item);
    }
    card.append(grid);
    return card;
}

function createSkillsCard(skills) {
    const card = createCard("Generatsiya qilingan ko'nikmalar");
    if (skills.length === 0) {
        card.append(createEmptyNote("Tugatilgan mavzu hali yo'q."));
        return card;
    }
    const grid = document.createElement("div");
    grid.className = "profile-grid";
    for (const skill of skills) {
        const item = document.createElement("div");
        item.className = "profile-card";
        const label = document.createElement("span");
        label.className = `skill-label${skill.label.startsWith("Applied") ? " applied" : ""}`;
        label.textContent = skill.label;
        const title = document.createElement("p");
        title.textContent = skill.name;
        const topics = document.createElement("ul");
        for (const topic of skill.topics) {
            const li = document.createElement("li");
            li.textContent = `${topic.name} (${topic.status})`;
            topics.append(li);
        }
        item.append(label, title, topics);
        if (skill.projects.length > 0) {
            const projectsTitle = document.createElement("p");
            projectsTitle.textContent = "Loyihalar:";
            const projects = document.createElement("ul");
            for (const project of skill.projects) {
                const li = document.createElement("li");
                li.append(
                    createLink(project.title, project.repository_link),
                    document.createTextNode(` — ${project.contribution}`)
                );
                projects.append(li);
            }
            item.append(projectsTitle, projects);
        }
        grid.append(item);
    }
    card.append(grid);
    return card;
}

function createTopicsCard(profile) {
    const card = createCard("O'rganilayotgan mavzular");
    card.append(createTopicForm(profile));
    if (profile.topics.length === 0) {
        card.append(createEmptyNote("Hozircha mavzu qo'shilmagan."));
        return card;
    }
    const list = document.createElement("ul");
    list.className = "profile-list";
    for (const topic of profile.topics) {
        const li = document.createElement("li");
        const name = document.createElement("span");
        name.className = "grow";
        name.textContent = `${topic.topic_name} → ${topic.skill}`;
        const select = createSelect(
            TOPIC_STATUSES.map((status) => ({ label: status, value: status })),
            topic.status
        );
        select.addEventListener("change", () =>
            handleUpdateTopic(profile.student.id, topic.id, select.value)
        );
        li.append(name, select);
        list.append(li);
    }
    card.append(list);
    return card;
}

function createTopicForm(profile) {
    const available = catalogueCache.filter(
        (item) => !profile.topics.some((topic) => topic.topic_key === item.key)
    );
    if (available.length === 0) {
        return createEmptyNote("Katalogdagi barcha mavzular qo'shilgan.");
    }
    const form = document.createElement("form");
    form.className = "profile-form";
    const topicSelect = createSelect(
        available.map((item) => ({ label: item.name, value: item.key })),
        available[0].key
    );
    topicSelect.id = "new-topic-key";
    const statusSelect = createSelect(
        TOPIC_STATUSES.map((status) => ({ label: status, value: status })),
        "Learning"
    );
    statusSelect.id = "new-topic-status";
    const addButton = createButton(
        "Mavzu qo'shish",
        "button-small",
        () => {},
        "submit"
    );
    form.append(
        createField("Mavzu", topicSelect),
        createField("Holat", statusSelect),
        addButton
    );
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        handleAddTopic(profile.student.id, {
            topic_key: topicSelect.value,
            status: statusSelect.value,
        });
    });
    return form;
}

function createProjectsCard(profile) {
    const card = createCard("Loyihalar");
    card.append(createProjectForm(profile));
    if (profile.projects.length === 0) {
        card.append(createEmptyNote("Hozircha loyiha qo'shilmagan."));
        return card;
    }
    const list = document.createElement("ul");
    list.className = "profile-list";
    for (const project of profile.projects) {
        const li = document.createElement("li");
        const details = document.createElement("div");
        details.className = "grow";
        const title = document.createElement("strong");
        title.textContent = project.title;
        const description = document.createElement("p");
        description.textContent = project.description;
        const contribution = document.createElement("p");
        contribution.textContent = `Mening qilgan ishim: ${project.contribution}`;
        const status = document.createElement("p");
        status.textContent = `Holat: ${project.status}`;
        details.append(
            title,
            description,
            contribution,
            status,
            createLink("Repository", project.repository_link)
        );
        const editButton = createButton("Tahrirlash", "button-small", () =>
            li.replaceChildren(createProjectForm(profile, project))
        );
        li.append(details, editButton);
        list.append(li);
    }
    card.append(list);
    return card;
}

function createProjectForm(profile, project = null) {
    const form = document.createElement("form");
    form.className = "profile-form";
    const title = createInput("project-title", project?.title || "", "text", "Loyiha nomi");
    const description = createInput(
        "project-description", project?.description || "", "text", "Qisqa tavsif"
    );
    const contribution = createInput(
        "project-contribution", project?.contribution || "", "text", "Shaxsiy hissam"
    );
    const link = createInput(
        "project-link", project?.repository_link || "", "url", "https://..."
    );
    const status = createSelect(
        PROJECT_STATUSES.map((value) => ({ label: value, value })),
        project?.status || "In progress"
    );
    const topics = createSelect(
        profile.topics.map((topic) => ({
            label: topic.topic_name,
            value: String(topic.id),
        })),
        project ? project.topic_ids.map(String) : [],
        true
    );
    topics.id = "project-topic-ids";
    topics.multiple = true;

    const submit = createButton(
        project ? "Saqlash" : "Loyiha qo'shish",
        "button-small",
        () => {},
        "submit"
    );
    const actions = document.createElement("div");
    actions.className = "row-actions";
    actions.append(submit);
    if (project) {
        actions.append(
            createButton("Bekor", "button-small button-secondary", () =>
                reloadProfile()
            )
        );
    }

    form.append(
        createField("Sarlavha", title),
        createField("Tavsif", description),
        createField("Shaxsiy hissam", contribution),
        createField("Repository havolasi", link),
        createField("Holat", status),
        createField("Bog'liq mavzular", topics),
        actions
    );
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const payload = {
            title: title.value,
            description: description.value,
            contribution: contribution.value,
            repository_link: link.value,
            status: status.value,
            topic_ids: Array.from(topics.selectedOptions).map(Number),
        };
        if (project) {
            handleUpdateProject(profile.student.id, project.id, payload);
        } else {
            handleAddProject(profile.student.id, payload);
        }
    });
    return form;
}

async function handleAddTopic(studentId, topic) {
    showMessage(elements.profileError, "");
    try {
        await api.addTopic(studentId, topic);
        showMessage(elements.profileMessage, "Mavzu saqlandi.");
        await reloadProfile();
    } catch (error) {
        showMessage(elements.profileError, error.message);
    }
}

async function handleUpdateTopic(studentId, topicId, status) {
    showMessage(elements.profileError, "");
    try {
        await api.updateTopic(studentId, topicId, { status });
        showMessage(elements.profileMessage, "Mavzu holati yangilandi.");
        await reloadProfile();
    } catch (error) {
        showMessage(elements.profileError, error.message);
    }
}

async function handleAddProject(studentId, project) {
    showMessage(elements.profileError, "");
    try {
        await api.addProject(studentId, project);
        showMessage(elements.profileMessage, "Loyiha saqlandi.");
        await reloadProfile();
    } catch (error) {
        showMessage(elements.profileError, error.message);
    }
}

async function handleUpdateProject(studentId, projectId, changes) {
    showMessage(elements.profileError, "");
    try {
        await api.updateProject(studentId, projectId, changes);
        showMessage(elements.profileMessage, "Loyiha yangilandi.");
        await reloadProfile();
    } catch (error) {
        showMessage(elements.profileError, error.message);
    }
}


// ===== Event handlers =====

async function handleFormSubmit(event) {
    event.preventDefault();  // stop the browser from reloading the page
    showMessage(elements.formError, "");
    showMessage(elements.formSuccess, "");

    const formData = new FormData(elements.form);
    const newStudent = {
        name: formData.get("name"),
        topic: formData.get("topic"),
        status: formData.get("status"),
        score: parseScore(formData.get("score")),
    };

    try {
        const savedStudent = await api.addStudent(newStudent);
        showMessage(
            elements.formSuccess,
            `Saqlandi: ${savedStudent.name} (ID ${savedStudent.id})`,
        );
        elements.form.reset();
        await refreshPage();
    } catch (error) {
        showMessage(elements.formError, error.message);
    }
}

async function handleUpdateStudent(studentId, changes) {
    showMessage(elements.tableError, "");
    try {
        await api.updateStudent(studentId, changes);
        await refreshPage();
    } catch (error) {
        showMessage(elements.tableError, error.message);
    }
}


// ===== Start =====

elements.form.addEventListener("submit", handleFormSubmit);
elements.statusFilter.addEventListener("change", loadStudents);
elements.searchInput.addEventListener("input", renderFilteredStudents);
elements.profileBack.addEventListener("click", () => {
    window.location.hash = "";
});
window.addEventListener("hashchange", handleRouteChange);
refreshPage();  // on every page load, ask the API for saved students
handleRouteChange();
