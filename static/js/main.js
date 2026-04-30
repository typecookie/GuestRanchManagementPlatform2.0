document.addEventListener("DOMContentLoaded", function () {
    const selects = document.querySelectorAll(".js-searchable-select");

    selects.forEach(function (select) {
        buildSearchableSelect(select);
    });
});

function buildSearchableSelect(select) {
    const wrapper = document.createElement("div");
    wrapper.className = "searchable-select";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "searchable-select-input";
    input.placeholder = "Search clients...";
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

        if (visibleCount === 0) {
            const empty = document.createElement("div");
            empty.className = "searchable-select-empty";
            empty.textContent = "No matching clients found.";
            list.appendChild(empty);
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