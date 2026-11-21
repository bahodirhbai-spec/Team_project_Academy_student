// Shared helpers for the profile page (owners: Hasan and Bahodirjon).
// The only place on the profile page that calls fetch().

const API_BASE_URL = "/api";

export async function requestJson(path, options = {}) {
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

// FastAPI sends validation errors (422) as a list, our own errors
// (404, 409, 422 from errors.py) as one text.
export function formatErrorDetail(detail) {
    if (!Array.isArray(detail)) {
        return String(detail);
    }
    return detail
        .map((error) => `${error.loc.at(-1)}: ${error.msg}`)
        .join("; ");
}

export function showMessage(element, text) {
    element.textContent = text;  // empty text hides it (see .error:empty)
}

export function createButton(label, className, onClick) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = className;
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
}
