// Frontend logic: talks to the FastAPI backend and updates the page.
// The database is the source of truth, so after every change we ask
// the API again instead of trusting what is already on the screen.

const API_BASE_URL = "/api";
const STUDENT_STATUSES = ["Active", "Paused", "Completed"];
const NO_SCORES_TEXT = "No scores yet.";
const NO_STUDENTS_TEXT = "Hozircha o'quvchilar yo'q";
const NO_MATCH_TEXT = "Qidiruvga mos o'quvchi topilmadi";
const TABLE_COLUMN_COUNT = 7;
const NO_SKILLS_TEXT = "Hali hech kimda ko'nikma yo'q";
const NO_DATA_TEXT = "Hozircha ma'lumot yo'q";
const PERCENT = 100;

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
    overviewError: document.getElementById("overview-error"),
    progressBody: document.getElementById("progress-body"),
    skillChart: document.getElementById("skill-chart"),
    skillMatrix: document.getElementById("skill-matrix"),
    summaryError: document.getElementById("summary-error"),
    learnedSkillsBody: document.getElementById("learned-skills-body"),
    studentsPerSkill: document.getElementById("students-per-skill"),
    appliedSkills: document.getElementById("applied-skills"),
};

// Search is sent to the API, so the table and /docs use the same rules.
// Only the newest request is allowed to update the table.
let loadStudentsRequest = 0;
let searchDebounce = null;


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
    listStudents: (status, search) => {
        const params = new URLSearchParams();
        if (status) {
            params.set("status", status);
        }
        if (search) {
            params.set("search", search);
        }
        const query = params.toString();
        return requestJson(`/students${query ? `?${query}` : ""}`);
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
    getSkillOverview: () => requestJson("/skills/overview"),
    getSkillSummary: () => requestJson("/skills/summary"),
    getProjectSummary: () => requestJson("/projects/summary"),
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

// textContent (not innerHTML) so a name like "<b>" is shown as text,
// never run as HTML. This protects against XSS attacks.
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

function createButton(label, className, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
}

function createProfileLink(studentId) {
    const link = document.createElement("a");
    link.href = `profile.html?id=${studentId}`;
    link.className = "button-small button-link";
    link.textContent = "Profil";
    return link;
}

function createStatusSelect(selectedStatus) {
    const select = document.createElement("select");
    for (const status of STUDENT_STATUSES) {
        const option = new Option(status, status);
        option.selected = status === selectedStatus;
        select.append(option);
    }
    return select;
}


// ===== Rendering the table =====

function renderStudents(students, emptyText = NO_STUDENTS_TEXT) {
    elements.tableBody.replaceChildren();
    if (students.length === 0) {
        elements.tableBody.append(createEmptyRow(emptyText));
        return;
    }
    for (const student of students) {
        elements.tableBody.append(createStudentRow(student));
    }
}

function createEmptyRow(text) {
    const row = document.createElement("tr");
    row.className = "empty-row";
    const cell = createCell(text);
    cell.colSpan = TABLE_COLUMN_COUNT;
    row.append(cell);
    return row;
}

function createStudentRow(student) {
    const row = document.createElement("tr");
    const editButton = createButton("Tahrirlash", "button-small", () =>
        row.replaceWith(createEditRow(student))
    );
    row.append(
        createCell(String(student.id)),
        createCell(student.name),
        createCell(student.topic),
        createCell(createStatusBadge(student.status)),
        createCell(formatScore(student.score)),
        createCell(editButton),
        createCell(createProfileLink(student.id)),
    );
    return row;
}

function createEditRow(student) {
    const row = document.createElement("tr");
    row.className = "editing-row";

    const topicInput = document.createElement("input");
    topicInput.value = student.topic;

    const statusSelect = createStatusSelect(student.status);

    const scoreInput = document.createElement("input");
    scoreInput.type = "number";
    scoreInput.min = "0";
    scoreInput.max = "100";
    scoreInput.value = student.score ?? "";

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
        createCell(""),
    );
    return row;
}

function renderSummary(summary) {
    elements.totalCount.textContent = summary.total_students;
    elements.activeCount.textContent = summary.active_students;
    elements.averageScore.textContent =
        summary.average_score === null ? NO_SCORES_TEXT : summary.average_score;
}


// ===== Rendering the skills overview =====

function renderOverview(overview) {
    renderProgressTable(overview.students);
    renderSkillChart(overview.skill_counts, overview.students.length);
    renderSkillMatrix(overview);
}

function renderProgressTable(students) {
    elements.progressBody.replaceChildren();
    for (const student of students) {
        const row = document.createElement("tr");
        row.append(
            createCell(student.name),
            createCell(String(student.completed_topics)),
            createCell(String(student.completed_projects)),
            createCell(String(student.skill_count)),
        );
        elements.progressBody.append(row);
    }
}

// One bar per skill; its length is the share of all students.
function renderSkillChart(skillCounts, studentCount) {
    elements.skillChart.replaceChildren();
    if (skillCounts.length === 0) {
        elements.skillChart.textContent = NO_SKILLS_TEXT;
        return;
    }
    for (const { skill, student_count: count } of skillCounts) {
        elements.skillChart.append(
            createBarRow(skill, count, (count / studentCount) * PERCENT)
        );
    }
}

function createBarRow(label, value, percent) {
    const row = document.createElement("div");
    row.className = "bar-row";

    const name = document.createElement("span");
    name.className = "bar-label";
    name.textContent = label;

    const track = document.createElement("div");
    track.className = "bar-track";
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.style.width = `${percent}%`;
    track.append(bar);

    const number = document.createElement("span");
    number.className = "bar-value";
    number.textContent = String(value);

    row.append(name, track, number);
    return row;
}

// Header row = skill names; then one row per student with 1 or 0.
function renderSkillMatrix({ skills, students, matrix }) {
    if (skills.length === 0) {
        elements.skillMatrix.replaceChildren();  // the chart says why
        return;
    }
    const header = document.createElement("tr");
    header.append(document.createElement("th"));
    for (const skill of skills) {
        const cell = document.createElement("th");
        cell.textContent = skill;
        header.append(cell);
    }
    const head = document.createElement("thead");
    head.append(header);

    const body = document.createElement("tbody");
    students.forEach((student, rowIndex) => {
        const row = document.createElement("tr");
        row.append(createCell(student.name));
        for (const value of matrix[rowIndex]) {
            const cell = createCell(String(value));
            cell.className = value ? "has-skill" : "no-skill";
            row.append(cell);
        }
        body.append(row);
    });
    elements.skillMatrix.replaceChildren(head, body);
}


// ===== Rendering the restored summary tables (PR #6) =====

function renderSkillSummary(summary) {
    elements.learnedSkillsBody.replaceChildren();
    if (summary.progress_per_student.length === 0) {
        const row = document.createElement("tr");
        const cell = createCell(NO_DATA_TEXT);
        cell.colSpan = 4;
        row.append(cell);
        elements.learnedSkillsBody.append(row);
    } else {
        for (const student of summary.progress_per_student) {
            const row = document.createElement("tr");
            row.append(
                createCell(student.name),
                createCell(String(student.completed_topics)),
                createCell(String(student.completed_projects)),
                createCell(String(student.skill_count)),
            );
            elements.learnedSkillsBody.append(row);
        }
    }
    renderCountBars(
        elements.studentsPerSkill,
        summary.students_per_skill,
    );
}

function renderCountBars(container, counts) {
    container.replaceChildren();
    const visible = counts.filter((item) => item.student_count > 0);
    if (visible.length === 0) {
        container.textContent = NO_DATA_TEXT;
        return;
    }
    const largest = Math.max(...visible.map((item) => item.student_count));
    for (const { skill, student_count: count } of visible) {
        container.append(
            createBarRow(skill, count, (count / largest) * PERCENT)
        );
    }
}

function renderProjectSummary(summary) {
    renderCountBars(
        elements.appliedSkills,
        summary.students_per_applied_skill,
    );
}


// ===== Loading data from the API =====

async function loadStudents() {
    const requestId = ++loadStudentsRequest;
    const search = elements.searchInput.value.trim();
    try {
        const students = await api.listStudents(
            elements.statusFilter.value,
            search
        );
        // A slower earlier request must not overwrite a newer result.
        if (requestId !== loadStudentsRequest) {
            return;
        }
        renderStudents(students, search ? NO_MATCH_TEXT : NO_STUDENTS_TEXT);
        showMessage(elements.tableError, "");
    } catch (error) {
        if (requestId === loadStudentsRequest) {
            showMessage(elements.tableError, error.message);
        }
    }
}

// Wait for a short pause in typing before calling the API.
function scheduleStudentsReload() {
    window.clearTimeout(searchDebounce);
    searchDebounce = window.setTimeout(loadStudents, 200);
}

async function loadSummary() {
    try {
        renderSummary(await api.getSummary());
    } catch (error) {
        showMessage(elements.tableError, error.message);
    }
}

async function loadOverview() {
    try {
        renderOverview(await api.getSkillOverview());
        showMessage(elements.overviewError, "");
    } catch (error) {
        showMessage(elements.overviewError, error.message);
    }
}

async function loadSummaryTables() {
    try {
        const [skillSummary, projectSummary] = await Promise.all([
            api.getSkillSummary(),
            api.getProjectSummary(),
        ]);
        renderSkillSummary(skillSummary);
        renderProjectSummary(projectSummary);
        showMessage(elements.summaryError, "");
    } catch (error) {
        showMessage(elements.summaryError, error.message);
    }
}

async function refreshPage() {
    await Promise.all([
        loadStudents(),
        loadSummary(),
        loadOverview(),
        loadSummaryTables(),
    ]);
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
elements.searchInput.addEventListener("input", scheduleStudentsReload);
refreshPage();  // on every page load, ask the API for saved students
