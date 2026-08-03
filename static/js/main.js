document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll(".js-searchable-select");

    selects.forEach(function (select) {
        buildSearchableSelect(select);
    });
});

function buildSearchableSelect(select) {
    const wrapper = document.createElement("div");
    wrapper.className = "searchable-select";

    const placeholder = select.dataset.placeholder || "Search...";
    const emptyMessage = select.dataset.emptyMessage || "No matching items found.";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "searchable-select-input";
    input.placeholder = placeholder;
    input.autocomplete = "off";

    const list = document.createElement("div");
    list.className = "searchable-select-list";

    const selectedOption = select.options[select.selectedIndex];

    if (selectedOption && selectedOption.value) {
        input.value = selectedOption.textContent;
    }

    select.style.display = "none";

    select.parentNode.insertBefore(wrapper, select);
    wrapper.appendChild(input);
    wrapper.appendChild(list);
    wrapper.appendChild(select);

    function renderOptions(filterText) {
        list.innerHTML = "";

        const normalizedFilter = filterText.toLowerCase().trim();
        let visibleCount = 0;

        Array.from(select.options).forEach(function (option) {
            if (!option.value) {
                return;
            }

            const optionText = option.textContent.trim();
            const normalizedOption = optionText.toLowerCase();

            if (normalizedFilter && !normalizedOption.includes(normalizedFilter)) {
                return;
            }

            const item = document.createElement("button");
            item.type = "button";
            item.className = "searchable-select-item";
            item.textContent = optionText;

            item.addEventListener("click", function () {
                select.value = option.value;
                input.value = optionText;
                list.classList.remove("is-open");

                select.dispatchEvent(new Event("change", { bubbles: true }));
            });

            list.appendChild(item);
            visibleCount += 1;
        });

        if (visibleCount === 0 && !select.dataset.quickAddUrl) {
            const empty = document.createElement("div");
            empty.className = "searchable-select-empty";
            empty.textContent = emptyMessage;
            list.appendChild(empty);
        }

        if (normalizedFilter && select.dataset.quickAddUrl) {
            const quickAddItem = document.createElement("button");
            quickAddItem.type = "button";
            quickAddItem.className = "searchable-select-item";
            quickAddItem.style.color = "var(--color-success)";
            quickAddItem.style.fontWeight = "800";
            quickAddItem.textContent = `+ Quick Add "${filterText}"`;

            quickAddItem.addEventListener("click", function () {
                const url = select.dataset.quickAddUrl;
                const csrfToken = getCsrfToken();
                const formData = new FormData();
                formData.append("name", filterText);

                // Add contextual data from other fields
                const contextFieldsStr = select.dataset.contextFields;
                if (contextFieldsStr) {
                    const contextFields = contextFieldsStr.split(",");
                    const form = select.form;
                    if (form) {
                        contextFields.forEach((fieldName) => {
                            const field = form.elements[fieldName.trim()];
                            if (field && field.value) {
                                formData.append(`${fieldName.trim()}_id`, field.value);
                            }
                        });
                    }
                }

                // Add contextual data from data-context-value-* attributes
                for (const key in select.dataset) {
                    if (key.startsWith("contextValue")) {
                        // contextValueTravelGroup -> travel_group
                        const fieldName = key
                            .substring(12)
                            .replace(/([A-Z])/g, (match, p1, offset) =>
                                offset > 0 ? "_" + match.toLowerCase() : match.toLowerCase()
                            );
                        formData.append(`${fieldName}_id`, select.dataset[key]);
                    }
                }

                quickAddItem.disabled = true;

                fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": csrfToken,
                    },
                    body: formData,
                })
                    .then((response) => response.json())
                    .then((data) => {
                        if (data.id) {
                            // Add new option to the original select
                            const newOption = new Option(data.name, data.id, true, true);
                            select.add(newOption);
                            
                            // Update the input and value
                            select.value = data.id;
                            input.value = data.name;
                            list.classList.remove("is-open");

                            // Dispatch change event
                            select.dispatchEvent(new Event("change", { bubbles: true }));
                        } else if (data.error) {
                            alert(data.error);
                        }
                    })
                    .catch((error) => {
                        console.error("Error during quick add:", error);
                        alert("An error occurred while adding. Please try again.");
                    });
            });
            list.appendChild(quickAddItem);
        }

        if (select.dataset.createUrl) {
            const createItem = document.createElement("a");
            createItem.href = select.dataset.createUrl;
            createItem.target = "_blank";
            createItem.className = "searchable-select-item";
            createItem.style.color = "var(--color-accent)";
            createItem.style.fontWeight = "800";
            createItem.textContent = "+ Create New...";
            list.appendChild(createItem);
        }
    }

    input.addEventListener("focus", function () {
        renderOptions(input.value);
        list.classList.add("is-open");
    });

    input.addEventListener("input", function () {
        select.value = "";
        renderOptions(input.value);
        list.classList.add("is-open");
    });

    input.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            list.classList.remove("is-open");
            input.blur();
        }
    });

    document.addEventListener("click", function (event) {
        if (!wrapper.contains(event.target)) {
            list.classList.remove("is-open");
        }
    });
}

document.addEventListener("DOMContentLoaded", function () {
    initializeGuestCabinDragAndDrop();
});

function initializeGuestCabinDragAndDrop() {
    const guestCards = document.querySelectorAll(".js-guest-card");
    const dropZones = document.querySelectorAll(".js-guest-drop-zone");

    if (!guestCards.length || !dropZones.length) {
        return;
    }

    guestCards.forEach(function (card) {
        card.addEventListener("dragstart", function (event) {
            event.dataTransfer.setData("text/plain", card.dataset.guestId);
            card.classList.add("is-dragging");
        });

        card.addEventListener("dragend", function () {
            card.classList.remove("is-dragging");
        });
    });

    dropZones.forEach(function (zone) {
        zone.addEventListener("dragover", function (event) {
            event.preventDefault();
            zone.classList.add("is-drag-over");
        });

        zone.addEventListener("dragleave", function () {
            zone.classList.remove("is-drag-over");
        });

        zone.addEventListener("drop", function (event) {
            event.preventDefault();
            zone.classList.remove("is-drag-over");

            const guestId = event.dataTransfer.getData("text/plain");
            const card = document.querySelector(`.js-guest-card[data-guest-id="${guestId}"]`);

            if (!card) {
                return;
            }

            const cabinId = zone.dataset.cabinId;
            const targetList = zone.querySelector(".guest-assignment-list");

            if (!targetList) {
                return;
            }

            const emptyMessage = targetList.querySelector(".empty-drop-message");

            if (emptyMessage) {
                emptyMessage.remove();
            }

            targetList.appendChild(card);

            if (cabinId) {
                assignGuestToCabin(card, cabinId);
            } else {
                unassignGuestFromCabin(card);
            }
        });
    });
}

function assignGuestToCabin(card, cabinId) {
    const url = card.dataset.assignUrl;
    const csrfToken = getCsrfToken();

    const formData = new FormData();
    formData.append("cabin", cabinId);

    fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
        },
        body: formData,
    }).then(function (response) {
        if (!response.ok) {
            window.location.reload();
        }
    }).catch(function () {
        window.location.reload();
    });
}

function unassignGuestFromCabin(card) {
    const url = card.dataset.unassignUrl;
    const csrfToken = getCsrfToken();

    fetch(url, {
        method: "POST",
        headers: {
            "X-CSRFToken": csrfToken,
        },
    }).then(function (response) {
        if (!response.ok) {
            window.location.reload();
        }
    }).catch(function () {
        window.location.reload();
    });
}

function getCsrfToken() {
    const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']");

    if (csrfInput) {
        return csrfInput.value;
    }

    const csrfCookie = document.cookie
        .split("; ")
        .find(function (row) {
            return row.startsWith("csrftoken=");
        });

    if (csrfCookie) {
        return csrfCookie.split("=")[1];
    }

    return "";
}