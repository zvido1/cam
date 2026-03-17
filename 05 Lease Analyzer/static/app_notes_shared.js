(function() {
    "use strict";

    function buildNotesToggleHtml(label, count) {
        const safeLabel = label || "Notes";
        if (count > 0) {
            return `${safeLabel} <span class="res-note-count">${count} note${count > 1 ? "s" : ""}</span>`;
        }
        return safeLabel;
    }

    function renderNotesPanelEntries(panel, notes, inputRow, helpers) {
        if (!panel) return;
        const esc = helpers.esc;
        const formatResTimestamp = helpers.formatResTimestamp;
        const buildDeleteButtonHtml = helpers.buildDeleteButtonHtml || function() { return ""; };

        panel.querySelectorAll(".res-note-entry").forEach((el) => el.remove());
        (notes || []).forEach((note, noteIdx) => {
            const noteDiv = document.createElement("div");
            noteDiv.className = "res-note-entry";
            noteDiv.innerHTML = `<span class="res-note-ts">${formatResTimestamp(note.timestamp)}</span><span class="res-note-text">${esc(note.text)}</span>${buildDeleteButtonHtml(noteIdx)}`;
            if (inputRow) panel.insertBefore(noteDiv, inputRow);
            else panel.appendChild(noteDiv);
        });
    }

    window.CAMNotesShared = {
        buildNotesToggleHtml,
        renderNotesPanelEntries,
    };
})();
