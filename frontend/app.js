// Frontend logic: talks to the FastAPI backend and updates the page.
// The database is the source of truth, so after every change we ask
// the API again instead of trusting what is already on the screen.

const API_BASE_URL = "/api";
const STUDENT_STATUSES = ["Active", "Paused", "Completed"];
const NO_SCORES_TEXT = "No scores yet.";
const NO_STUDENTS_TEXT = "Hozircha o'quvchilar yo'q";
const NO_MATCH_TEXT = "Qidiruvga mos o'quvchi topilmadi";
const TABLE_COLUMN_COUNT = 6;

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
};

// Students returned by the last API call; searching filters this in the browser.
let studentsCache = [];


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

// Case-insensitive search in the name and topic columns.
function matchesSearch(student, query) {
    if (!query) {
        return true;
    }
    const needle = query.toLocaleLowerCase();
    return (
        student.name.toLocaleLowerCase().includes(needle) ||
        student.topic.toLocaleLowerCase().includes(needle)
    );
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

async function refreshPage() {
    await Promise.all([loadStudents(), loadSummary()]);
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
refreshPage();  // on every page load, ask the API for saved students
