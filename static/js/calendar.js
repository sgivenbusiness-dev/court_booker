(() => {
    const calendar = document.querySelector("[data-calendar]");
    if (!calendar) return;

    const bookingDialog = document.querySelector("#booking-dialog");
    const detailsDialog = document.querySelector("#details-dialog");
    const bookingForm = document.querySelector("#booking-form");
    const durationSelect = document.querySelector("#booking-duration");
    const isPro = calendar.dataset.isPro === "true";
    const ownerSelect = document.querySelector("#booking-owner");
    const ownerSearch = document.querySelector("#booking-owner-search");
    const ownerSelected = document.querySelector("#member-owner-selected");
    const ownerCombobox = document.querySelector("#member-owner-combobox");
    const ownerOptions = document.querySelector("#member-owner-options");
    const guestCountFields = document.querySelector("#guest-count-fields");
    const courtInput = document.querySelector("#booking-court");
    const courtIdsInput = document.querySelector("#booking-court-ids");
    const courtOrder = [...calendar.querySelectorAll("[data-court-heading]")]
        .map((heading) => heading.dataset.courtHeading);
    let drag = null;
    let detailBooking = null;

    const allSlots = () => [...calendar.querySelectorAll("[data-slot]")];
    const minutesFromTime = (time) => {
        const [hours, minutes] = time.split(":").map(Number);
        return hours * 60 + minutes;
    };
    const timeFromMinutes = (minutes) => `${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
    const displayTime = (time) => {
        const [hours, minutes] = time.split(":").map(Number);
        return `${hours % 12 || 12}:${String(minutes).padStart(2, "0")} ${hours >= 12 ? "PM" : "AM"}`;
    };

    function updateGuestCountVisibility() {
        if (!guestCountFields) return;
        guestCountFields.hidden = false;
        document.querySelector("#guest-count").required = true;
    }

    function filterOwnerOptions() {
        if (!ownerOptions) return;
        const query = ownerSearch.value.trim().toLowerCase();
        ownerOptions.querySelectorAll("[data-owner-option]").forEach((option) => {
            option.hidden = query !== "" && !option.dataset.search.includes(query);
        });
    }

    function showOwnerOptions() {
        if (!ownerOptions) return;
        filterOwnerOptions();
        ownerOptions.hidden = false;
        ownerSearch.setAttribute("aria-expanded", "true");
    }

    function hideOwnerOptions() {
        if (!ownerOptions) return;
        ownerOptions.hidden = true;
        ownerSearch.setAttribute("aria-expanded", "false");
    }

    function selectOwner(option) {
        if (!option) return;
        ownerSelect.value = option.dataset.value;
        ownerSelected.querySelector("strong").textContent = option.dataset.name;
        ownerSelected.querySelector("span").textContent = `Club #${option.dataset.value}`;
        updateGuestCountVisibility();
    }

    function normalizeCourts(courts) {
        return (Array.isArray(courts) ? courts : [courts]).map(String);
    }

    function selectedCourtsBetween(firstCourt, lastCourt) {
        if (!isPro) return [String(firstCourt)];
        const firstIndex = courtOrder.indexOf(String(firstCourt));
        const lastIndex = courtOrder.indexOf(String(lastCourt));
        if (firstIndex === -1 || lastIndex === -1) return [String(firstCourt)];
        return courtOrder.slice(Math.min(firstIndex, lastIndex), Math.max(firstIndex, lastIndex) + 1);
    }

    function cellsForSelection(courts, start, duration) {
        const startMinutes = minutesFromTime(start);
        return normalizeCourts(courts).flatMap((court) =>
            Array.from({ length: duration / 30 }, (_, index) =>
                calendar.querySelector(`[data-slot][data-court="${court}"][data-time="${timeFromMinutes(startMinutes + index * 30)}"]`)
            )
        );
    }

    function clearPreview() {
        allSlots().forEach((cell) => cell.classList.remove("slot-cell--selecting", "slot-cell--invalid"));
    }

    function preview(courts, start, duration) {
        clearPreview();
        const selectedCourts = normalizeCourts(courts);
        const cells = cellsForSelection(selectedCourts, start, duration);
        const expectedCellCount = selectedCourts.length * duration / 30;
        const valid = cells.length === expectedCellCount && cells.every((cell) => cell && cell.dataset.blocked !== "true");
        cells.filter(Boolean).forEach((cell) => cell.classList.add(valid ? "slot-cell--selecting" : "slot-cell--invalid"));
        return valid;
    }

    function openBooking(courts, start, duration, allowConflict = false) {
        const selectedCourts = normalizeCourts(courts);
        if (!allowConflict && !preview(selectedCourts, start, duration)) return;
        if (allowConflict) clearPreview();
        courtInput.value = selectedCourts[0];
        courtIdsInput.value = selectedCourts.join(",");
        document.querySelector("#booking-start").value = start;
        document.querySelector("#override-confirmed").value = allowConflict ? "yes" : "no";
        document.querySelectorAll("[data-member-number]").forEach((input) => { input.value = ""; });
        document.querySelector("#guest-count").value = "0";
        if (ownerSelect) {
            selectOwner(ownerOptions.querySelector(`[data-value="${ownerSelect.dataset.currentOwner}"]`));
            ownerSearch.value = "";
        }
        updateGuestCountVisibility();
        durationSelect.value = String(duration);
        const timeSummary = `${displayTime(start)}–${displayTime(timeFromMinutes(minutesFromTime(start) + duration))}`;
        document.querySelector("#booking-summary").textContent = selectedCourts.length > 1
            ? `${selectedCourts.length} courts · ${timeSummary}`
            : timeSummary;
        bookingDialog.showModal();
    }

    allSlots().forEach((cell) => {
        if (cell.dataset.blocked === "true") return;
        cell.addEventListener("pointerdown", (event) => {
            if (event.button !== 0) return;
            event.preventDefault();
            drag = {
                anchorCourt: cell.dataset.court,
                courts: [cell.dataset.court],
                start: cell.dataset.time,
                duration: 30,
            };
            cell.setPointerCapture(event.pointerId);
            preview(drag.courts, drag.start, drag.duration);
        });
        cell.querySelector("button")?.addEventListener("keydown", (event) => {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                openBooking(cell.dataset.court, cell.dataset.time, 30);
            }
        });
    });

    document.addEventListener("pointermove", (event) => {
        if (!drag) return;
        const cell = document.elementFromPoint(event.clientX, event.clientY)?.closest("[data-slot]");
        if (!cell || (!isPro && drag.anchorCourt !== cell.dataset.court)) return;
        const duration = minutesFromTime(cell.dataset.time) - minutesFromTime(drag.start) + 30;
        const latestDuration = 20 * 60 - minutesFromTime(drag.start);
        if (duration >= 30 && duration <= (isPro ? latestDuration : 120)) {
            drag.duration = duration;
            drag.courts = selectedCourtsBetween(drag.anchorCourt, cell.dataset.court);
            preview(drag.courts, drag.start, drag.duration);
        }
    });

    document.addEventListener("pointerup", (event) => {
        if (!drag) return;
        event.preventDefault();
        const selection = drag;
        drag = null;
        openBooking(selection.courts, selection.start, selection.duration);
    });

    document.addEventListener("pointercancel", () => {
        drag = null;
        clearPreview();
    });

    durationSelect?.addEventListener("change", () => {
        const selectedCourts = courtIdsInput.value.split(",").filter(Boolean);
        const start = document.querySelector("#booking-start").value;
        const duration = Number(durationSelect.value);
        preview(selectedCourts, start, duration);
        const timeSummary = `${displayTime(start)}–${displayTime(timeFromMinutes(minutesFromTime(start) + duration))}`;
        document.querySelector("#booking-summary").textContent = selectedCourts.length > 1
            ? `${selectedCourts.length} courts · ${timeSummary}`
            : timeSummary;
    });

    ownerSearch?.addEventListener("input", () => {
        ownerSearch.value = ownerSearch.value.replace(/\D/g, "");
        const exactMatch = ownerOptions.querySelector(`[data-value="${ownerSearch.value}"]`);
        if (exactMatch) selectOwner(exactMatch);
        showOwnerOptions();
    });
    ownerSearch?.addEventListener("focus", showOwnerOptions);
    ownerCombobox?.querySelector(".member-combobox-toggle")?.addEventListener("click", () => {
        if (ownerOptions.hidden) {
            showOwnerOptions();
            ownerSearch.focus();
        } else {
            hideOwnerOptions();
        }
    });
    ownerOptions?.querySelectorAll("[data-owner-option]").forEach((option) => {
        option.addEventListener("click", () => {
            selectOwner(option);
            ownerSearch.value = "";
            hideOwnerOptions();
            ownerSearch.focus();
        });
    });
    document.addEventListener("pointerdown", (event) => {
        if (ownerCombobox && !ownerCombobox.contains(event.target)) hideOwnerOptions();
    });
    updateGuestCountVisibility();

    document.querySelectorAll("[data-member-number]").forEach((input) => {
        input.addEventListener("input", () => {
            input.value = input.value.replace(/\D/g, "");
        });
        input.addEventListener("paste", (event) => {
            const pasted = event.clipboardData?.getData("text") || "";
            if (/\D/.test(pasted)) event.preventDefault();
        });
    });

    bookingForm?.addEventListener("submit", (event) => {
        const selectedCourts = courtIdsInput.value.split(",").filter(Boolean);
        const start = document.querySelector("#booking-start").value;
        const duration = Number(durationSelect.value);
        const confirmedOverride = document.querySelector("#override-confirmed").value === "yes";
        if (!confirmedOverride && !preview(selectedCourts, start, duration)) {
            event.preventDefault();
            document.querySelector("#booking-warning").hidden = false;
            return;
        }
        if (isPro && selectionOverlapsBooking(selectedCourts, start, duration)) {
            if (!window.confirm("This will replace a conflicting booking. Continue with the override?")) {
                event.preventDefault();
                return;
            }
            document.querySelector("#override-confirmed").value = "yes";
        }
    });

    function selectionOverlapsBooking(courts, start, duration) {
        const selectedCourts = normalizeCourts(courts);
        const selectedStart = minutesFromTime(start);
        const selectedEnd = selectedStart + duration;
        return [...calendar.querySelectorAll("[data-booking]")].some((booking) => {
            if (!selectedCourts.includes(booking.dataset.court)) return false;
            const bookingStart = minutesFromTime(booking.dataset.start);
            const bookingEnd = bookingStart + Number(booking.dataset.duration);
            return selectedStart < bookingEnd && selectedEnd > bookingStart;
        });
    }

    calendar.querySelectorAll("[data-booking]").forEach((button) => {
        button.addEventListener("click", () => {
            detailBooking = button.dataset;
            document.querySelector("#details-name").textContent = button.dataset.name;
            document.querySelector("#details-time").textContent = button.dataset.time;
            document.querySelector("#details-duration").textContent = `${button.dataset.duration} minutes`;
            const billingDetails = document.querySelector("#billing-details");
            billingDetails.hidden = button.dataset.billingVisible !== "true";
            if (!billingDetails.hidden) {
                document.querySelector("#details-owner").textContent = `${button.dataset.name} · Club #${button.dataset.ownerClubNumber}`;
                document.querySelector("#details-members").textContent = button.dataset.memberRoster;
                document.querySelector("#details-guests").textContent = button.dataset.guestCount;
                document.querySelector("#details-billable").textContent = button.dataset.billablePeople;
            }
            const cancelForm = document.querySelector("#cancel-form");
            cancelForm.action = cancelForm.dataset.actionTemplate.replace("BOOKING_ID", encodeURIComponent(button.dataset.id));
            cancelForm.hidden = button.dataset.own !== "true";
            detailsDialog.showModal();
        });
    });

    document.querySelector("#cancel-form")?.addEventListener("submit", (event) => {
        if (!window.confirm("Cancel this booking?")) event.preventDefault();
    });

    document.querySelector("#override-button")?.addEventListener("click", () => {
        if (!detailBooking || !window.confirm("Override this booking with your own reservation?")) return;
        detailsDialog.close();
        openBooking(detailBooking.court, detailBooking.start, Number(detailBooking.duration), true);
    });

    document.querySelectorAll("[data-close-dialog]").forEach((button) => {
        button.addEventListener("click", () => {
            button.closest("dialog").close();
            clearPreview();
        });
    });
})();
