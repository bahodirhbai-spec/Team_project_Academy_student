// Profile page start-up (owners: Hasan and Bahodirjon).
// Loads GET /api/students/{id}/profile, draws the student and the
// skills, and hands the topics to the two section files.

import { requestJson, showMessage } from "./http.js";
import { setupProjects } from "./profile-projects.js";
import { setupTopics } from "./profile-topics.js";

const NO_SKILLS_TEXT =
    "Hali ko'nikma yo'q: mavzuni Completed qiling.";
const MISSING_ID_TEXT = "Manzilda o'quvchi ID'si yo'q (?id=1).";

const elements = {
    name: document.getElementById("student-name"),
    meta: document.getElementById("student-meta"),
    error: document.getElementById("profile-error"),
    skills: document.getElementById("skill-list"),
};

// profile.html?id=3 -> 3. Number("") is 0, which is not a valid ID.
const studentId = Number(new URLSearchParams(location.search).get("id"));


function renderStudent(student) {
    elements.name.textContent = student.name;
    elements.meta.textContent =
        `ID ${student.id} · ${student.topic} · ${student.status}`;
    document.title = `${student.name} — profil`;
}

function createTextLine(text, className = "") {
    const line = document.createElement("span");
    line.className = className;
    line.textContent = text;
    return line;
}

// One finished project behind the skill: its name (a link when the
// project has one) and what THIS student did in it.
function createSkillProject(project) {
    const item = document.createElement("li");
    const title = document.createElement(project.link ? "a" : "strong");
    title.textContent = project.name;
    if (project.link) {
        title.href = project.link;
        title.target = "_blank";
        title.rel = "noopener noreferrer";  // the new tab cannot touch ours
    }
    item.append(title, ` — ${project.contribution}`);
    return item;
}

// "Applied in a project" gets a stronger colour than "Learned".
function createSkillCard(skill) {
    const card = document.createElement("div");
    const isApplied = skill.label === "Applied in a project";
    card.className = isApplied ? "skill-card applied" : "skill-card";

    const name = document.createElement("strong");
    name.textContent = `${skill.name} — ${skill.label}`;
    card.append(
        name,
        createTextLine(`Mavzu: ${skill.topics.join(", ")}`, "skill-evidence"),
    );
    if (skill.projects.length > 0) {
        const projectList = document.createElement("ul");
        projectList.className = "skill-projects";
        projectList.append(...skill.projects.map(createSkillProject));
        card.append(projectList);
    }
    return card;
}

function renderSkills(skills) {
    elements.skills.replaceChildren();
    if (skills.length === 0) {
        elements.skills.textContent = NO_SKILLS_TEXT;
        return;
    }
    elements.skills.append(...skills.map(createSkillCard));
}

// The project form only needs each topic's record ID and name.
function toProjectTopics(records) {
    return records.map((record) => ({
        id: record.id,
        name: record.topic_name,
    }));
}

// Called on start and after every change in the two sections, so
// the skills are always the ones the server just calculated.
async function loadProfile() {
    try {
        const profile = await requestJson(`/students/${studentId}/profile`);
        renderStudent(profile.student);
        renderSkills(profile.skills);
        showMessage(elements.error, "");
        await Promise.all([
            setupTopics({
                studentId,
                records: profile.topics,
                onChanged: loadProfile,
            }),
            setupProjects({
                studentId,
                topics: toProjectTopics(profile.topics),
                onChanged: loadProfile,
            }),
        ]);
    } catch (error) {
        showMessage(elements.error, error.message);
    }
}


// ===== Start =====

if (studentId > 0) {
    loadProfile();
} else {
    elements.name.textContent = "Profil topilmadi";
    showMessage(elements.error, MISSING_ID_TEXT);
}
