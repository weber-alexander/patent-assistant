"""Streamlit user interface of the Patent Assistant.

Start with:  uv run streamlit run src/patent_assistant/app.py
"""

from __future__ import annotations

import html
import time
from pathlib import Path

import streamlit as st

from patent_assistant import (
    document_export,
    file_import,
    knowledge_base,
    llm,
    projects,
    user_state,
)
from patent_assistant.claim_checker import Finding, check_claims
from patent_assistant.config import MODEL_LABELS, settings
from patent_assistant.prompts import (
    CLAIM_FIX_PROMPT,
    DESCRIPTION_PARTS,
    LOOKUP_PROMPT,
    PRIOR_ART_PLACEHOLDER,
    PROOFREAD_PROMPT,
    SECTIONS,
    SYSTEM_PROMPT,
)

PAGES = {
    "invention": "💡  Erfindung",
    "claims": "⚖️  Patentansprüche",
    "description": "📝  Beschreibung",
    "questions": "❓  Erfinderfragen",
    "document": "📄  Dokumentansicht",
    "knowledge": "📚  Wissensbasis",
}
SEVERITY_LABEL = {"error": "Fehler", "warning": "Warnung", "info": "Hinweis"}
ABSTRACT_MAX_CHARS = 1500
LOGO = Path(__file__).parent / "assets" / "logo.png"

CSS = """
<style>
footer {visibility: hidden;}
.block-container {padding-top: 4rem; max-width: 1100px;}
h1, h2, h3 {color: #2C4A66;}
section[data-testid="stSidebar"] {background-color: #E2E7EC;}
.nav-title {font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
            color: #5B6B7A; margin: 0.8rem 0 0.2rem 0;}
.st-key-paper {background: #FFFFFF; max-width: 840px; margin: 0 auto;
               padding: 56px 72px !important; border-radius: 2px;
               box-shadow: 0 2px 14px rgba(31, 41, 51, 0.14);}
.st-key-paper [data-baseweb="textarea"], .st-key-paper [data-baseweb="base-input"] {
    border: none !important; background: transparent !important;}
.st-key-paper [data-baseweb="textarea"]:hover {background: #F6F8FA !important;}
.st-key-paper textarea {font-family: Arial, sans-serif; font-size: 15px; line-height: 1.6;
                        color: #1F2933; padding: 4px 2px !important; resize: none;}
.st-key-paper textarea:focus {background: #F0F4F8 !important;}
.st-key-doc_title textarea {font-size: 24px !important; font-weight: 700;
                            color: #2C4A66 !important;}
.doc-h1 {font-family: Arial, sans-serif; font-size: 19px; font-weight: 700;
         color: #2C4A66; margin: 18px 0 4px 0;}
.doc-h2 {font-family: Arial, sans-serif; font-size: 15px; font-weight: 700;
         color: #3B5B7A; margin: 12px 0 0 0;}
.doc-break {text-align: center; color: #9AA5B1; font-size: 12px; padding-top: 4px;
            border-top: 1px dashed #C5CDD5; margin: 28px 0 12px 0;}
.page-header {margin: 0 0 0.6rem 0;}
.page-header .page-kicker {font-size: 0.8rem !important; font-weight: 600;
              letter-spacing: 0.08em; color: #5B6B7A !important;
              margin: 0 !important; line-height: 1.4;}
.page-header .page-title {font-size: 2.6rem !important; font-weight: 700;
              color: #1F2933 !important; margin: 0.1rem 0 0 0 !important;
              line-height: 1.2;}
/* Text areas grow with their content (Chrome, Edge, Opera) */
@supports (field-sizing: content) {
    [data-testid="stTextArea"] textarea {
        field-sizing: content;
        height: auto !important;
        min-height: 6lh;
        max-height: 70vh;
        overflow-y: auto;
    }
    [data-testid="stTextArea"] [data-baseweb="textarea"] {height: auto !important;}
    .st-key-w_invention_invention textarea {min-height: 12lh;}
    .st-key-w_invention_known_prior_art textarea {min-height: 6lh;}
    .st-key-paper textarea {min-height: 2lh; max-height: none;}
}
section[data-testid="stSidebar"] .block-container,
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {padding-top: 1rem;}
</style>
"""


# ======================================================================
# State
# ======================================================================


def format_duration(seconds: float) -> str:
    """Format a duration as '2 Min. 40 Sek.' or '24 Sek.'."""
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes} Min. {secs} Sek." if minutes else f"{secs} Sek."


def init_state() -> None:
    if "data" not in st.session_state:
        st.session_state.data = projects.empty_project()
    st.session_state.setdefault("backup", {})
    st.session_state.setdefault("sources", {})
    st.session_state.setdefault("durations", {})
    st.session_state.setdefault("current_file", None)
    if "model" not in st.session_state:
        last = user_state.load().get("last_model")
        st.session_state.model = last if last in settings.chat_models else settings.chat_models[0]


def data() -> dict[str, str]:
    return st.session_state.data


def notify(message: str) -> None:
    """Show a toast after the next rerun."""
    st.session_state.toast = message


# ======================================================================
# Environment check (Ollama running, models installed)
# ======================================================================


def ensure_environment() -> None:
    """Stop rendering and show a setup page if Ollama or models are missing."""
    if st.session_state.get("environment_ok"):
        return

    if not llm.is_server_running():
        st.title("Einrichtung")
        st.error(
            "Ollama ist nicht erreichbar. Bitte die Ollama-App starten "
            f"(erwartet unter {settings.ollama_host}) und die Seite neu laden."
        )
        st.stop()

    missing = llm.missing_models()
    if missing:
        st.title("Einrichtung")
        st.info(
            "Für den ersten Start werden folgende KI-Modelle benötigt: "
            f"**{', '.join(missing)}**. Der Download (bei Erstinstallation "
            "insgesamt ca. 9 GB) erfolgt einmalig und kann je nach "
            "Internetverbindung 10 bis 30 Minuten dauern. Andere Modelle "
            "lassen sich über die Einstellung PA_CHAT_MODELS verwenden "
            "(siehe README)."
        )
        if st.button("Modelle jetzt herunterladen", type="primary"):
            for name in missing:
                bar = st.progress(0.0, text=f"{name} ... 0 %")
                llm.pull_model(
                    name,
                    lambda value, n=name, b=bar: b.progress(
                        value, text=f"{n} ... {int(value * 100)} %"
                    ),
                )
            st.rerun()
        st.stop()

    st.session_state.environment_ok = True


# ======================================================================
# Text fields bound to the central data store
# ======================================================================


def _estimate_height(text: str, minimum: int, chars_per_line: int) -> int:
    """Fallback height for browsers without CSS field-sizing support."""
    lines = sum(len(line) // chars_per_line + 1 for line in (text or "").split("\n"))
    return max(minimum, min(600, lines * 24 + 24))


def _sync(field: str, widget_key: str) -> None:
    data()[field] = st.session_state[widget_key]


def text_field(
    field: str,
    label: str,
    page: str,
    *,
    minimum: int = 80,
    hide_label: bool = True,
    placeholder: str = "",
    chars_per_line: int = 140,
) -> None:
    """Text area that reads from and writes to the central data store."""
    widget_key = f"w_{page}_{field}"
    st.session_state[widget_key] = data()[field]
    st.text_area(
        label,
        key=widget_key,
        height=_estimate_height(data()[field], minimum, chars_per_line),
        on_change=_sync,
        args=(field, widget_key),
        label_visibility="collapsed" if hide_label else "visible",
        placeholder=placeholder,
    )


# ======================================================================
# AI operations
# ======================================================================


def _context() -> str:
    d = data()
    parts = [
        "Erfindungsbeschreibung:\n" + d["invention"],
        "Bekannter Stand der Technik:\n"
        + (d["known_prior_art"].strip() or "(keine Angaben vorhanden)"),
    ]
    if d["claims"].strip():
        parts.append("Bereits formulierte Patentansprüche:\n" + d["claims"])
    return "\n\n".join(parts)


def _rules_addition(key: str) -> str:
    """Retrieve curated rules for a section if RAG is enabled."""
    section = SECTIONS[key]
    if not st.session_state.get("use_rag") or not section["search"]:
        st.session_state.sources.pop(key, None)
        return ""
    passages = knowledge_base.rules_for(f"[{section['label']}] {section['search']}")
    st.session_state.sources[key] = passages
    if not passages:
        return ""
    rules = "\n".join(f"- {p.text}" for p in passages)
    return f"\n\nBEACHTE ZUSÄTZLICH DIESE REGELN (nicht zitieren, nur befolgen):\n{rules}"


def _generate(system: str, user: str, expected: int, on_progress) -> str:
    return llm.generate(st.session_state.model, system, user, expected, on_progress)


def draft_section(key: str, on_progress) -> str:
    """Create the text of one section (without storing it)."""
    if key == "prior_art" and not data()["known_prior_art"].strip():
        return PRIOR_ART_PLACEHOLDER
    system = SYSTEM_PROMPT + "\n\n" + SECTIONS[key]["prompt"] + _rules_addition(key)
    return _generate(system, _context(), SECTIONS[key]["expected_length"], on_progress)


def fix_claims(findings: list[Finding], on_progress) -> str:
    listing = "\n".join(f"- Anspruch {f.claim}: {f.message}" for f in findings)
    d = data()
    user = (
        f"Erfindungsbeschreibung:\n{d['invention']}\n\n"
        f"Anspruchssatz:\n{d['claims']}\n\nPrüfbefunde:\n{listing}"
    )
    return _generate(SYSTEM_PROMPT + "\n\n" + CLAIM_FIX_PROMPT, user, len(d["claims"]), on_progress)


def run_with_progress(key: str, task, label: str = "KI schreibt") -> None:
    """Run a single AI task with a progress bar, store result and duration."""
    bar = st.progress(0.0, text=f"{label} ... 0 %")
    start = time.perf_counter()
    text = task(lambda v: bar.progress(v, text=f"{label} ... {int(v * 100)} %"))
    st.session_state.durations[key] = time.perf_counter() - start
    st.session_state.backup[key] = data()[key]
    data()[key] = text
    st.rerun()


def generate_all(include_questions: bool) -> None:
    """Create the complete draft in one run (without proofreading)."""
    steps = ["claims", "checker", "title", *DESCRIPTION_PARTS, "abstract"]
    if include_questions:
        steps.append("questions")
    bar = st.progress(0.0, text="Starte ...")
    durations = st.session_state.durations
    total_start = time.perf_counter()

    for i, step in enumerate(steps):
        name = "Anspruchs-Checker" if step == "checker" else SECTIONS[step]["label"]

        def progress(value: float, i: int = i, name: str = name) -> None:
            total = min((i + value) / len(steps), 1.0)
            bar.progress(
                total, text=f"Schritt {i + 1}/{len(steps)}: {name} ... {int(total * 100)} %"
            )

        progress(0.0)
        step_start = time.perf_counter()

        if step == "checker":
            findings = check_claims(data()["claims"])
            if findings:
                fixed = fix_claims(findings, progress)
                # Only accept the correction if it actually reduces the findings
                if len(check_claims(fixed)) < len(findings):
                    st.session_state.backup["claims"] = data()["claims"]
                    data()["claims"] = fixed
            # Checker time counts towards the claims
            durations["claims"] = durations.get("claims", 0) + time.perf_counter() - step_start
            continue

        st.session_state.backup[step] = data()[step]
        data()[step] = draft_section(step, progress)
        durations[step] = time.perf_counter() - step_start

    total = time.perf_counter() - total_start
    durations["__all__"] = total
    bar.progress(1.0, text="Fertig")
    notify(f"Gesamtentwurf erstellt in {format_duration(total)}. Bitte prüfen!")
    st.session_state.next_page = "document"
    st.rerun()


# ======================================================================
# Reusable UI blocks
# ======================================================================


def ai_toolbar(key: str, page: str) -> None:
    col_create, col_proof, col_undo = st.columns(3)

    if col_create.button("Mit KI erstellen", key=f"gen_{page}_{key}", use_container_width=True):
        if not data()["invention"].strip():
            st.warning(
                "Bitte zuerst auf der Seite 'Erfindung' eine Erfindungsbeschreibung eingeben."
            )
        else:
            run_with_progress(key, lambda p: draft_section(key, p))

    if col_proof.button("Korrekturlesen", key=f"proof_{page}_{key}", use_container_width=True):
        text = data()[key]
        if not text.strip():
            st.warning("Das Feld ist leer.")
        else:
            run_with_progress(
                key, lambda p: _generate(PROOFREAD_PROMPT, text, len(text), p), "KI korrigiert"
            )

    if key in st.session_state.backup and col_undo.button(
        "Rückgängig", key=f"undo_{page}_{key}", use_container_width=True
    ):
        data()[key] = st.session_state.backup.pop(key)
        st.session_state.durations.pop(key, None)
        st.rerun()


def section_editor(key: str, page: str) -> None:
    section = SECTIONS[key]
    st.markdown(f"#### {section['label']}")
    text_field(key, section["label"], page, minimum=section["min_height"])

    if key == "abstract" and data()[key].strip():
        chars = len(data()[key])
        if chars > ABSTRACT_MAX_CHARS:
            st.error(f"{chars} Zeichen. Erlaubt sind höchstens 1.500 (§ 13 PatV).")
        else:
            st.caption(f"{chars} / 1.500 Zeichen (§ 13 PatV)")

    passages = st.session_state.sources.get(key)
    if passages:
        with st.expander(f"Berücksichtigte Regeln ({len(passages)})"):
            for p in passages:
                st.markdown(f"**{p.source}** (Ähnlichkeit {p.score:.2f})")
                st.caption(p.text)

    ai_toolbar(key, page)
    if key in st.session_state.durations:
        st.caption(f"Benötigte Zeit: {format_duration(st.session_state.durations[key])}")


def show_findings(findings: list[Finding]) -> None:
    counts = {s: sum(f.severity == s for f in findings) for s in SEVERITY_LABEL}
    st.write(
        f"{counts['error']} Fehler · {counts['warning']} Warnungen · {counts['info']} Hinweise"
    )
    for f in findings:
        location = f"**Anspruch {f.claim}:** " if f.claim else "**Gesamt:** "
        {"error": st.error, "warning": st.warning}.get(f.severity, st.info)(location + f.message)


def page_header(page_label: str, caption: str = "") -> None:
    """Show the project name as title and the current page above it."""
    name = data()["project_name"].strip() or st.session_state.current_file or "Neues Projekt"
    st.markdown(
        '<div class="page-header">'
        f'<div class="page-kicker">{html.escape(page_label.upper())}</div>'
        f'<div class="page-title">{html.escape(name)}</div>'
        "</div>",
        unsafe_allow_html=True,
    )
    if caption:
        st.caption(caption)


def export_button(key: str) -> None:
    st.download_button(
        "Als Word exportieren",
        data=document_export.build_docx(data()),
        file_name=projects.safe_filename(data()["project_name"] or "Anmeldung") + ".docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True,
        type="primary",
        key=key,
    )


# ======================================================================
# Sidebar
# ======================================================================


def _remember_model() -> None:
    """Store the selected model in the project and as global preference."""
    data()["model"] = st.session_state.model
    user_state.save(last_model=st.session_state.model)


def _open_project(content: dict[str, str], filename: str | None) -> None:
    st.session_state.data = content
    st.session_state.backup = {}
    st.session_state.sources = {}
    st.session_state.durations = {}
    st.session_state.current_file = filename
    if content.get("model") in settings.chat_models:
        st.session_state.next_model = content["model"]
    st.rerun()


def _save(filename: str) -> None:
    data()["model"] = st.session_state.model
    projects.save_project(filename, data())
    st.session_state.current_file = filename
    notify(f"Gespeichert: {filename}")
    st.rerun()


def sidebar() -> str:
    with st.sidebar:
        st.image(str(LOGO), width=120)
        st.markdown("## Patent-Assistent")
        st.caption("Lokal · vertraulich · kein Rechtsrat")

        st.markdown('<p class="nav-title">PROJEKT</p>', unsafe_allow_html=True)
        current = st.session_state.current_file
        st.caption(
            f"Geöffnet: **{current}**" if current else "Neues, noch nicht gespeichertes Projekt"
        )

        name_key = "w_sidebar_project_name"
        st.session_state[name_key] = data()["project_name"]
        st.text_input(
            "Projektname",
            key=name_key,
            placeholder="Projektname",
            label_visibility="collapsed",
            on_change=_sync,
            args=("project_name", name_key),
        )

        col_save, col_save_as = st.columns(2)
        if col_save.button("💾 Speichern", use_container_width=True):
            _save(current or projects.safe_filename(data()["project_name"]))
        if col_save_as.button("📝 Speichern unter", use_container_width=True):
            target = projects.safe_filename(data()["project_name"])
            if target != current and projects.exists(target):
                st.error(f"'{target}' existiert bereits.")
            else:
                _save(target)

        available = projects.list_projects()
        if available:
            index = available.index(current) if current in available else 0
            choice = st.selectbox(
                "Projekt öffnen", available, index=index, label_visibility="collapsed"
            )
            col_load, col_new = st.columns(2)
            if col_load.button("📂 Laden", use_container_width=True):
                _open_project(projects.load_project(choice), choice)
            if col_new.button("🆕 Neu", use_container_width=True):
                _open_project(projects.empty_project(), None)
        elif st.button("🆕 Neues Projekt", use_container_width=True):
            _open_project(projects.empty_project(), None)

        st.markdown('<p class="nav-title">BEARBEITEN</p>', unsafe_allow_html=True)
        if "next_page" in st.session_state:
            st.session_state.page = st.session_state.pop("next_page")
        page = st.radio(
            "Navigation",
            list(PAGES),
            format_func=PAGES.get,
            key="page",
            label_visibility="collapsed",
        )

        st.markdown('<p class="nav-title">EINSTELLUNGEN</p>', unsafe_allow_html=True)
        with st.expander("⚙️ KI-Einstellungen"):
            if "next_model" in st.session_state:
                st.session_state.model = st.session_state.pop("next_model")
            st.selectbox(
                "Modell",
                settings.chat_models,
                key="model",
                on_change=_remember_model,
                format_func=lambda name: MODEL_LABELS.get(name, name),
                help="Das größere Modell liefert bessere Texte, braucht aber "
                "mehr Zeit und Arbeitsspeicher (empfohlen ab 16 GB RAM).",
            )
            st.toggle(
                "Richtlinien berücksichtigen (RAG)",
                key="use_rag",
                help="Gibt der KI beim Erstellen passende Regeln aus der Wissensbasis mit.",
            )
    return page


# ======================================================================
# Pages
# ======================================================================


def page_invention() -> None:
    page_header("Erfindung", "Grundlage für alle weiteren Texte. Je genauer, desto besser.")

    st.markdown("#### Erfindungsmeldung hochladen")
    st.caption(
        "Word (.docx), PDF oder Text. Die Datei wird nur lokal verarbeitet und nicht "
        "gespeichert. Gescannte PDFs ohne Textebene und .doc werden nicht unterstützt."
    )
    upload = st.file_uploader(
        "Datei auswählen", type=list(file_import.SUPPORTED_TYPES), label_visibility="collapsed"
    )
    if upload:
        preview_key = f"preview_{upload.name}_{upload.size}"
        if preview_key not in st.session_state:
            try:
                st.session_state[preview_key] = file_import.extract_text(
                    upload.name, upload.getvalue()
                )
            except Exception as error:  # show any parser problem to the user
                st.session_state[preview_key] = ""
                st.error(f"Die Datei konnte nicht gelesen werden: {error}")

        if not st.session_state[preview_key].strip():
            st.warning("Kein Text gefunden. Handelt es sich um ein gescanntes PDF?")
        else:
            st.text_area(
                "Vorschau (bearbeitbar, z. B. Erfindernamen oder Formularfelder entfernen)",
                key=preview_key,
                height=250,
            )
            text = st.session_state[preview_key].strip()
            st.caption(f"{len(text):,} Zeichen".replace(",", "."))
            if len(text) > 15000:
                st.warning("Sehr langer Text. Am besten auf die technisch relevanten Teile kürzen.")
            target = st.radio(
                "Übernehmen in",
                ["invention", "known_prior_art"],
                horizontal=True,
                format_func={
                    "invention": "Erfindungsbeschreibung",
                    "known_prior_art": "Bekannter Stand der Technik",
                }.get,
            )
            col_replace, col_append = st.columns(2)
            if col_replace.button("Ersetzen", use_container_width=True, type="primary"):
                data()[target] = text
                notify("Text übernommen.")
                st.rerun()
            if col_append.button("Anhängen", use_container_width=True):
                data()[target] = (data()[target].rstrip() + "\n\n" + text).strip()
                notify("Text angehängt.")
                st.rerun()
    st.divider()

    st.markdown("#### Erfindungsbeschreibung")
    text_field(
        "invention",
        "Erfindungsbeschreibung",
        "invention",
        minimum=250,
        placeholder="Merkmale, Funktionsweise, Zahlenwerte, Varianten, Vorteile ...",
    )
    st.markdown("#### Bekannter Stand der Technik")
    text_field(
        "known_prior_art",
        "Bekannter Stand der Technik",
        "invention",
        minimum=120,
        placeholder="Was gibt es bisher, und was sind die Nachteile? Leer lassen, wenn unbekannt.",
    )
    st.info(
        "**Empfohlener Ablauf:** Erfindung beschreiben → Erfinderfragen erzeugen → Antworten "
        "ergänzen → Ansprüche → Beschreibung → Dokumentansicht prüfen → Word exportieren."
    )

    st.divider()
    st.markdown("#### Gesamtentwurf")
    st.caption(
        "Erstellt nacheinander Ansprüche, Checker-Korrektur, Titel, Beschreibung und "
        "Zusammenfassung. Korrekturlesen danach gezielt pro Abschnitt. Dauer: einige Minuten."
    )
    include_questions = st.checkbox("Erfinderfragen mit erstellen", value=False)
    if any(data()[key].strip() for key in SECTIONS):
        st.warning(
            "Vorhandene Texte werden überschrieben. Jeder Abschnitt lässt sich danach "
            "einzeln per 'Rückgängig' wiederherstellen."
        )
    if st.button(
        "Gesamten Entwurf erstellen",
        type="primary",
        use_container_width=True,
        disabled=not data()["invention"].strip(),
    ):
        generate_all(include_questions)


def page_claims() -> None:
    page_header(
        "Patentansprüche", "Zuerst die Ansprüche erstellen, denn die Beschreibung baut darauf auf."
    )
    section_editor("claims", "claims")

    st.divider()
    st.markdown("#### Anspruchs-Checker")
    st.caption(
        "Regelbasierte Prüfung ohne KI. Fehler sind formale Mängel, Warnungen sollten "
        "fachlich bewertet werden."
    )
    findings = check_claims(data()["claims"])

    if "findings_before" in st.session_state:
        before = st.session_state.pop("findings_before")
        if len(findings) < before:
            st.success(f"KI-Korrektur: {before} → {len(findings)} Befunde")
        else:
            st.error(
                f"KI-Korrektur: {before} → {len(findings)} Befunde. Keine Verbesserung, "
                "eventuell 'Rückgängig' klicken."
            )

    if not data()["claims"].strip():
        st.info("Noch keine Ansprüche vorhanden.")
    elif not findings:
        st.success("Keine Auffälligkeiten gefunden.")
    else:
        show_findings(findings)
        if st.button("Befunde mit KI beheben", use_container_width=True):
            st.session_state.findings_before = len(findings)
            run_with_progress("claims", lambda p: fix_claims(findings, p), "KI korrigiert")


def page_description() -> None:
    page_header("Beschreibung")
    if not data()["claims"].strip():
        st.warning(
            "Noch keine Ansprüche vorhanden. Die Begriffe in der Beschreibung sind "
            "dann eventuell uneinheitlich."
        )
    for key in ("title", *DESCRIPTION_PARTS, "abstract"):
        section_editor(key, "description")
        st.divider()


def page_questions() -> None:
    page_header("Fragen an den Erfinder", "Interne Arbeitsnotiz. Wird nicht exportiert.")
    section_editor("questions", "questions")


def page_document() -> None:
    findings = check_claims(data()["claims"])
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)

    col_info, col_export = st.columns([3, 1])
    with col_info:
        page_header("Dokumentansicht")
        st.caption(
            f"{document_export.count_placeholders(data())} offene Platzhalter · "
            f"Checker: {errors} Fehler, {warnings} Warnungen · "
            "Klicke in einen Text, um ihn zu bearbeiten."
        )
        if "__all__" in st.session_state.durations:
            st.caption(
                "Gesamtentwurf erstellt in "
                f"{format_duration(st.session_state.durations['__all__'])}"
            )
    with col_export:
        st.write("")
        export_button("export_document")

    def heading(text: str, level: int) -> None:
        st.markdown(f'<div class="doc-h{level}">{text}</div>', unsafe_allow_html=True)

    def page_break() -> None:
        st.markdown('<div class="doc-break">Seitenumbruch</div>', unsafe_allow_html=True)

    with st.container(key="paper"):
        with st.container(key="doc_title"):
            text_field(
                "title",
                "Titel",
                "document",
                minimum=68,
                placeholder="[Titel der Erfindung]",
                chars_per_line=50,
            )
        heading("Beschreibung", 1)
        for key in DESCRIPTION_PARTS:
            label = SECTIONS[key]["label"]
            heading(label, 2)
            text_field(
                key,
                label,
                "document",
                minimum=68,
                placeholder=f"[{label} noch leer]",
                chars_per_line=85,
            )
        for key in ("claims", "abstract"):
            label = SECTIONS[key]["label"]
            page_break()
            heading(label, 1)
            text_field(
                key,
                label,
                "document",
                minimum=68,
                placeholder=f"[{label} noch leer]",
                chars_per_line=85,
            )

    st.caption(
        "Platzhalter [ERGÄNZEN: ...] werden im Word-Dokument gelb markiert. "
        "Formatierungen oder Zeichnungen bitte in Word ergänzen."
    )


def page_knowledge() -> None:
    page_header("Wissensbasis")
    st.caption(
        "Regeln und Richtlinien aus dem Ordner 'knowledge'. Werden beim Erstellen "
        "genutzt, wenn RAG in den Einstellungen aktiv ist."
    )
    documents = knowledge_base.list_documents()
    if documents:
        st.write("**Dokumente:** " + ", ".join(d.name for d in documents))
    else:
        st.warning("Der Ordner 'knowledge' ist leer.")
    st.write(knowledge_base.index_summary())

    if st.button("Index aufbauen / aktualisieren", disabled=not documents):
        bar = st.progress(0.0, text="Erstelle Index ...")
        count = knowledge_base.build_index(
            lambda v: bar.progress(v, text=f"Erstelle Index ... {int(v * 100)} %")
        )
        notify(f"Index erstellt: {count} Textabschnitte.")
        st.rerun()

    st.divider()
    st.markdown("#### Nachschlagen")
    question = st.text_input("Frage", placeholder="z. B. Wie lang darf die Zusammenfassung sein?")
    if st.button("Suchen", disabled=not question.strip()):
        passages = knowledge_base.search(question, k=4)
        if not passages:
            st.error("Kein Index vorhanden.")
            return
        excerpts = "\n\n".join(f"[{i}] ({p.source}) {p.text}" for i, p in enumerate(passages, 1))
        bar = st.progress(0.0, text="KI antwortet ... 0 %")
        start = time.perf_counter()
        answer = _generate(
            LOOKUP_PROMPT,
            f"Auszüge:\n{excerpts}\n\nFrage: {question}",
            600,
            lambda v: bar.progress(v, text=f"KI antwortet ... {int(v * 100)} %"),
        )
        bar.empty()
        st.markdown(answer)
        st.caption(f"Benötigte Zeit: {format_duration(time.perf_counter() - start)}")
        with st.expander("Quellen"):
            for i, p in enumerate(passages, 1):
                st.markdown(f"**[{i}] {p.source}** ({p.score:.2f})")
                st.caption(p.text)


PAGE_RENDERERS = {
    "invention": page_invention,
    "claims": page_claims,
    "description": page_description,
    "questions": page_questions,
    "document": page_document,
    "knowledge": page_knowledge,
}


# ======================================================================
# Entry point
# ======================================================================


def main() -> None:
    st.set_page_config(page_title="Patent-Assistent", page_icon=str(LOGO), layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    init_state()
    ensure_environment()
    if "toast" in st.session_state:
        st.toast(st.session_state.pop("toast"))
    PAGE_RENDERERS[sidebar()]()


main()
