import os
import time
from datetime import datetime
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xml.sax.saxutils import escape

import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="LOA-Trainingsapp", page_icon="🌱", layout="centered")

APP_TITLE = "LOA-Trainingsapp – Schülercoaching"
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_TEACHER_MESSAGES = 40

SCENARIOS = {
    "Hausaufgaben vergessen": {
        "description": "Das Kind vergisst häufig Hausaufgaben und fühlt sich von der Lehrperson kritisiert. Es reagiert anfangs etwas defensiv.",
        "system": """HINTERGRUND: Du vergisst häufig Hausaufgaben. Du hast das Gefühl, dass die Lehrperson ständig daran herumkritisiert. Zu Beginn bist du etwas defensiv und genervt, aber nicht respektlos. Du bist grundsätzlich bereit, dich auf das Gespräch einzulassen. Du antwortest wie ein echtes Kind dieses Alters: eher kurz und alltagsnah, manchmal unsicher, gelegentlich mit Widersprüchen. Du gibst nicht sofort alle hilfreichen Informationen preis."""
    },
    "Meldet sich selten im Unterricht": {
        "description": "Das Kind weiss häufig die Antwort, meldet sich im Unterricht aber selten. Es ist bereit, darüber zu sprechen, weiss jedoch noch nicht, was ihm helfen könnte.",
        "system": """HINTERGRUND: Du bist in der 6. Klasse und weisst im Unterricht häufig die Antwort, meldest dich aber trotzdem selten. Manchmal bist du unsicher, ob deine Antwort richtig ist, manchmal möchtest du nicht, dass alle dich anschauen oder hast Sorge, dass andere lachen könnten. Scham kann dabei eine mögliche Hintergrundemotion sein, muss aber nicht die Erklärung sein. Diese Gründe sind mögliche Aspekte, aber du sollst sie nicht ungefragt alle aufzählen, selbst als Scham benennen oder als feste Erklärung darstellen. Du bist grundsätzlich bereit, über das Thema zu sprechen, hast aber noch keine klare Vorstellung davon, was dir helfen könnte. Antworte wie ein echtes Kind dieses Alters: eher kurz und alltagsnah, manchmal unsicher, gelegentlich mit Widersprüchen. Gib hilfreiche Informationen, Ressourcen und Ausnahmen nicht sofort vollständig preis."""
    },
    "Rahmengespräch nach Regelverletzung": {
        "description": "Das Kind hat während einer Lektion trotz der vereinbarten Regel sein Handy benutzt. Du führst ein Rahmengespräch: Die Regel bleibt klar, gleichzeitig erkundest du, was dem Kind helfen kann, sich künftig daran zu halten.",
        "system": """HINTERGRUND: Du bist in der 6. Klasse. In deiner Klasse gilt die klare Regel, dass das Handy während der Lektion in der Tasche bleibt. Heute hast du es trotzdem hervorgeholt und benutzt. Die Lehrperson führt nun ein Rahmengespräch mit dir. Zu Beginn bist du etwas genervt oder defensiv und findest vielleicht, dass es nicht so schlimm war. Du willst nicht einfach belehrt werden. Als mögliche Hintergründe kommen zum Beispiel eine Nachricht, Langeweile, Gewohnheit oder der Wunsch, kurz etwas nachzuschauen infrage; lege dich nicht von Anfang an auf eine einzige Erklärung fest und erzähle nicht alles ungefragt. Bleibe offen dafür, dass die Regel klar und verbindlich ist, ohne sofort alle Lösungen der Lehrperson zu überlassen. Wenn die Lehrperson respektvoll nach deiner Sicht fragt und erkundet, was du brauchst, damit du dich an den Rahmen halten kannst, kannst du nach und nach konkreter werden. Entwickle nicht sofort einen perfekten Plan und stimme nicht automatisch allem zu. Antworte wie ein echtes Kind dieses Alters: eher kurz und alltagsnah, manchmal unsicher, gelegentlich mit Widersprüchen. Gib hilfreiche Informationen, Ressourcen und mögliche nächste Schritte nicht sofort vollständig preis."""
    }
}

PUPIL_SYSTEM_BASE = """Du spielst in einem Trainingsgespräch ein fiktives Kind aus der 6. Klasse in einer Schweizer Schule. Die Person am anderen Ende ist eine Lehrperson, die ein lösungsorientiertes Coachinggespräch mit dir führt.

SPIELREGELN:
-  Du bist ein Kind der 6. Klasse und sprichst wie ein echtes 11-jähriges Kind. Antworte eher kurz, manchmal  mit «Keine Ahnung», «Ja, vielleicht», «Weiss nicht so genau» oder «Eigentlich schon» sind passend, wenn sie zur Situation passen. Stelle keine Gegenfragen und übernimm nicht die Gesprächsführung.
- Zu Beginn weisst du nicht, weshalb die Lehrperson mit dir sprechen möchte. Du kennst zwar deinen eigenen Hintergrund, stellst aber keine Verbindung zum Gespräch her, bevor die Lehrperson das Thema anspricht. 
- Du bist grundsätzlich gesprächsbereit. Wenn die Lehrperson das Thema anspricht, reagierst du entsprechend deiner Rolle. Unsicherheit, Ärger oder unterschiedliche Sichtweisen dürfen dann sichtbar werden. Gib Hintergründe und mögliche Lösungen nach und nach preis.
- Reagiere auf das, was die Lehrperson tatsächlich sagt. Wenn sie zuhört und passende Fragen stellt, kannst du dich allmählich öffnen.
- Erfinde keine dramatischen Hintergründe, Diagnosen oder Krisen.
- Antworte jeweils nur als Kind, in 1–4 Sätzen. Keine Rollenspiel-Regieanweisungen.
- Das Gespräch findet auf Schweizer Hochdeutsch statt. Verwende Schweizer Rechtschreibung.
"""


EVALUATION_SYSTEM = """Du bist eine fachkundige, wertschätzende und entwicklungsorientierte Fachperson für lösungsorientierte Gesprächsführung (LOA) im schulischen Kontext.

Analysiere das gesamte Gespräch zwischen der Lehrperson und dem fiktiven Kind. Deine Rückmeldung soll zum Nachdenken und Weiterentwickeln anregen, nicht die Gesprächsführung benoten oder die Person beurteilen.

GRUNDHALTUNG:
- Schreibe konsequent in der Du-Form.
- Verwende Schweizer Rechtschreibung.
- Verzichte vollständig auf Ziffernnoten, Punktwerte, Rankings und Leistungsstufen.
- Beschreibe möglichst konkret und wertfrei, was im Gespräch beobachtbar ist.
- Unterscheide zwischen Gesprächsverhalten und einer im Dialog tatsächlich erkennbaren Wirkung.
- Belege Beobachtungen mit kurzen, wortgetreuen Zitaten. Erfinde keine Aussagen.
- Formuliere mögliche Entwicklungen als Einladungen, nicht als Vorschriften.
- Würdige vorhandene Kompetenzen, Ressourcen und gelungene Gesprächsmomente.
- Vermeide pauschale Urteile, Defizitorientierung und künstliches Lob.
- Beurteile keine Persönlichkeitseigenschaften.
- Berücksichtige den Gesprächsverlauf und den jeweiligen Übungsfall.
- Wenn ein Aspekt noch nicht vorkommt, beschreibe dies neutral. Interpretiere fehlende Gesprächsschritte nicht automatisch als Schwäche.
- Verlange keinen bestimmten Fragetyp und keine starre Abfolge von Gesprächsphasen.
- Berücksichtige, dass ein Gespräch auch bewusst offenbleiben darf.

FÜNF KRITERIEN:

1. Zielklärung und Zieldefinition
Wie werden das Anliegen und die gewünschte Veränderung erkundet? Wird erkennbar, woran das Kind im Alltag einen Unterschied bemerken könnte?

2. Ideenanreicherung durch abwechslungsreiche Fragen
Wie regen die Fragen neue Gedanken, Perspektiven und Möglichkeiten an? Perspektiv-, Beziehungs-, Ausnahme- und Wunderfragen sind mögliche Zugänge, aber keine Checkliste.

3. Ressourcen und Ausnahmen
Wie werden Fähigkeiten, bisherige Erfolge, hilfreiche Bedingungen und Situationen erkundet, in denen etwas bereits besser gelingt?

4. Umsetzung und nächste Schritte
Wird, sofern es zum Gesprächsverlauf passt, ein konkreter, machbarer und vom Kind mitgetragener nächster Schritt entwickelt? Erzwinge keinen Aktionsplan.

5. Pacing und Abstimmung auf das Kind
Wie werden Antworten aufgenommen, Fragen daran angeschlossen und Raum für eigene Gedanken gelassen? Schliesse bei einem Textchat nicht auf tatsächliches Sprechtempo, Pausen oder Körpersprache.

VERBINDLICHE STRUKTUR DER RÜCKMELDUNG:

# Rückmeldung zu deinem Coachinggespräch

## Überblick
Beschreibe in 2 bis 4 Sätzen den Verlauf und die erkennbaren Schwerpunkte des Gesprächs. Keine Note und kein pauschales Gesamturteil.

## Einschätzung nach fünf Kriterien

### 1. Zielklärung und Zieldefinition
**Beobachtung**
Beschreibe konkret und möglichst wertfrei, was im Gespräch zu diesem Kriterium erkennbar ist. Verwende passende Gesprächsbelege.

**Nächste mögliche Entwicklung**
Zeige eine mögliche Vertiefung oder Erweiterung auf, sofern sie aus dem Gespräch sinnvoll hervorgeht.

Wiederhole diese beiden Untertitel für alle fünf Kriterien, mit den oben festgelegten Kriterientiteln.

## Was dir bereits gut gelungen ist
Hebe 2 bis 3 konkrete, hilfreiche Gesprächsmomente hervor. Begründe anhand des tatsächlichen Dialogs, was daran gelungen ist. Vermeide Wiederholungen und allgemeines Lob.

## Ein möglicher nächster Entwicklungsschritt
Wähle einen einzigen, besonders passenden Entwicklungsschritt. Formuliere ihn als Möglichkeit oder Einladung, nicht als Anweisung. Knüpfe an vorhandene Kompetenzen an.

## 3 Fragen zur Selbstreflexion
Formuliere genau drei unterschiedliche, offene Fragen, die individuell aus diesem Gespräch entstehen:
1. Eine Frage zum Wahrnehmen und Verstehen eines Gesprächsmoments.
2. Eine Frage zu eigenen Ressourcen, gelungenen Momenten oder hilfreichen Vorgehensweisen.
3. Eine Frage zu einer möglichen Weiterentwicklung oder zum nächsten Gespräch.

Die Fragen sollen echte Reflexion ermöglichen. Sie dürfen keine erwünschte Antwort vorwegnehmen und sollen nicht wie eine versteckte Bewertung klingen.

WICHTIG FÜR DIE AUSGABE:
- Halte die genannten Überschriften exakt ein.
- Verwende bei jedem Kriterium genau die Untertitel 'Beobachtung' und 'Nächste mögliche Entwicklung'.
- Verwende den Abschlusstitel exakt '3 Fragen zur Selbstreflexion'.
- Stelle Reflexionsfragen nur im letzten Abschnitt.
- Gib nirgends numerische Bewertungen aus.
- Bleibe konkret, differenziert, gut verständlich und lösungsorientiert.
"""


def create_evaluation_pdf(evaluation):
    """Erstellt ein formatiertes PDF nur mit der LOA-Auswertung."""
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=45,
        leftMargin=45,
        topMargin=50,
        bottomMargin=50
    )

    # Schrift mit Unterstützung für Umlaute
    font_name = "Helvetica"
    font_path = "C:/Windows/Fonts/arial.ttf"

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont("LOAArial", font_path))
        font_name = "LOAArial"

    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="LOATitle",
        fontName=font_name,
        fontSize=17,
        leading=23,
        spaceAfter=15,
        textColor=colors.HexColor("#245C49")
    ))

    styles.add(ParagraphStyle(
        name="LOAHeading",
        fontName=font_name,
        fontSize=12,
        leading=17,
        spaceBefore=15,
        spaceAfter=7,
        textColor=colors.HexColor("#245C49")
    ))

    styles.add(ParagraphStyle(
        name="LOASubheading",
        fontName=font_name,
        fontSize=10.5,
        leading=15,
        spaceBefore=11,
        spaceAfter=5
    ))

    styles.add(ParagraphStyle(
        name="LOABody",
        fontName=font_name,
        fontSize=10,
        leading=15,
        spaceAfter=8,
        alignment=TA_LEFT
    ))

    story = []

    def add_paragraph(text, style):
        safe_text = escape(text)

        # Einfache Markdown-Fettschrift umwandeln
        import re
        safe_text = re.sub(
            r"\*\*(.+?)\*\*",
            r"<b>\1</b>",
            safe_text
        )

        story.append(Paragraph(safe_text, style))

    for line in evaluation.splitlines():
        line = line.strip()

        if not line:
            story.append(Spacer(1, 5))
        elif line.startswith("### "):
            add_paragraph(line[4:], styles["LOASubheading"])
        elif line.startswith("## "):
            add_paragraph(line[3:], styles["LOAHeading"])
        elif line.startswith("# "):
            add_paragraph(line[2:], styles["LOATitle"])
        elif line.startswith("- "):
            add_paragraph("• " + line[2:], styles["LOABody"])
        else:
            add_paragraph(line, styles["LOABody"])

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def get_api_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        key = ""
    return key or os.getenv("GEMINI_API_KEY", "")


def get_client():
    key = get_api_key()
    if not key:
        return None
    return genai.Client(api_key=key)

def generate_with_retry(client, **kwargs):
    """Wiederholt Gemini-Anfragen bei vorübergehender Überlastung."""
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(**kwargs)

        except Exception as exc:
            error_text = str(exc).lower()

            temporary_error = (
                "503" in error_text
                or "unavailable" in error_text
                or "high demand" in error_text
            )

            if not temporary_error or attempt == max_attempts - 1:
                raise

            wait_seconds = 2 ** (attempt + 1)
            time.sleep(wait_seconds)


def reset_conversation():
    st.session_state.messages = []
    st.session_state.evaluation = None
    st.session_state.started = True
    st.session_state.ended = False


if "messages" not in st.session_state:
    st.session_state.messages = []
if "evaluation" not in st.session_state:
    st.session_state.evaluation = None
if "started" not in st.session_state:
    st.session_state.started = False
if "ended" not in st.session_state:
    st.session_state.ended = False
if "selected_scenario" not in st.session_state:
    st.session_state.selected_scenario = "Hausaufgaben vergessen"

st.title("🌱 " + APP_TITLE)
st.caption("Prototyp · Übungsszenario für lösungsorientierte Gesprächsführung")

if not st.session_state.started:
    st.subheader("Wähle einen Übungsfall")
    scenario_choice = st.radio(
        "Mit welchem Kind möchtest du üben?",
        options=list(SCENARIOS.keys()),
        index=list(SCENARIOS.keys()).index(st.session_state.selected_scenario),
        format_func=lambda name: name,
    )
    st.session_state.selected_scenario = scenario_choice
    st.write(SCENARIOS[scenario_choice]["description"])

with st.expander("Hinweise zum Übungsgespräch", expanded=not st.session_state.started):
    st.write("Du führst ein Coachinggespräch mit einem fiktiven Kind aus der 6. Klasse. Die KI bleibt während des Gesprächs in der Rolle des Kindes. Die Auswertung erfolgt erst am Schluss.")
    st.info("Bitte verwende keine echten Namen oder identifizierenden Angaben zu Schülerinnen, Schülern, Eltern oder Mitarbeitenden.")

client = get_client()
if client is None:
    st.warning("Die App benötigt einen Gemini-API-Schlüssel, um die Gesprächssimulation und die Auswertung auszuführen.")
    st.code('GEMINI_API_KEY = "dein-api-schlüssel"', language="toml")
    st.caption("Dies ist nur ein Beispiel. Den echten Schlüssel niemals in den Code, in GitHub oder in einen öffentlichen Chat einfügen. Für die Veröffentlichung wird er in den geschützten App-Secrets hinterlegt.")

if not st.session_state.started:
    st.write("**Deine Rolle:** Du bist die Lehrperson und führst das Gespräch. Die KI antwortet als Kind. Während des Gesprächs gibt es noch keine Rückmeldung; die Auswertung erfolgt erst am Schluss.")
    if st.button("Gespräch starten", type="primary", disabled=client is None, use_container_width=True):
        reset_conversation()
        st.rerun()

if st.session_state.started and not st.session_state.ended:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if len([m for m in st.session_state.messages if m["role"] == "user"]) >= MAX_TEACHER_MESSAGES:
        st.info(f"Für diesen kostenlosen Prototyp sind maximal {MAX_TEACHER_MESSAGES} Nachrichten pro Gespräch vorgesehen. Du kannst das Gespräch jetzt auswerten oder neu beginnen.")
    prompt = st.chat_input("Deine Nachricht an das Kind …", disabled=client is None or len([m for m in st.session_state.messages if m["role"] == "user"]) >= MAX_TEACHER_MESSAGES)


    if prompt:
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })

    waiting_for_reply = (
        len(st.session_state.messages) > 0
        and st.session_state.messages[-1]["role"] == "user"
    )

    if waiting_for_reply:
        try:
            with st.spinner("Das Kind antwortet …"):
                history = []

                for item in st.session_state.messages:
                    role = (
                        "user" if item["role"] == "user" else "model"
                    )
                    history.append(
                        types.Content(
                            role=role,
                            parts=[
                                types.Part.from_text(
                                    text=item["content"]
                                )
                            ]
                        )
                    )

                response = generate_with_retry(
                    client,
                    model=MODEL,
                    contents=history,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            PUPIL_SYSTEM_BASE
                            + "\n\n"
                            + SCENARIOS[
                                st.session_state.selected_scenario
                            ]["system"]
                        ),
                        temperature=0.8,
                        max_output_tokens=300
                    )
                )

                reply = response.text

                if not reply:
                    raise ValueError(
                        "Gemini hat keine Antwort zurückgegeben."
                    )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": reply
                })

            st.rerun()

        except Exception as exc:
            st.warning(
                "Gemini konnte momentan nicht antworten. "
                "Deine Nachricht bleibt gespeichert."
            )
            st.caption("Technischer Hinweis: " + str(exc))

            if st.button("Antwort erneut anfordern"):
                st.rerun()


    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Gespräch beenden und auswerten", type="primary", disabled=(
    client is None
    or len(st.session_state.messages) < 2
    or st.session_state.messages[-1]["role"] != "assistant"
), use_container_width=True):
            transcript = "\n\n".join(("Lehrperson: " if m["role"] == "user" else "Kind: ") + m["content"] for m in st.session_state.messages)
            try:
                with st.spinner("Ich werte das Gespräch anhand der fünf LOA-Kriterien aus …"):
                    result = generate_with_retry(
    client,
                        model=MODEL,
                        contents="Analysiere dieses Gespräch.\n\n" + transcript,
                        config=types.GenerateContentConfig(system_instruction=EVALUATION_SYSTEM, temperature=0.2, max_output_tokens=3000),
                    )
                    st.session_state.evaluation = result.text or "Es konnte keine Auswertung erstellt werden."
                    st.session_state.ended = True
                    st.rerun()
            except Exception as exc:
                st.error("Die Auswertung konnte nicht erstellt werden. Technischer Hinweis: " + str(exc))
    with col2:
        if st.button("Neu beginnen", use_container_width=True):
            st.session_state.messages = []
            st.session_state.evaluation = None
            st.session_state.started = False
            st.session_state.ended = False
            st.rerun()

if st.session_state.ended and st.session_state.evaluation:
    st.success("Das Gespräch ist abgeschlossen. Hier ist deine entwicklungsorientierte Rückmeldung.")
    st.markdown(st.session_state.evaluation)
    
    pdf_data = create_evaluation_pdf(
        st.session_state.evaluation
    )

    st.download_button(
        "📄 Auswertung als PDF herunterladen",
        data=pdf_data,
        file_name="LOA_Gespraechsauswertung.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    if st.button("Neues Übungsgespräch starten", type="primary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.evaluation = None
        st.session_state.started = False
        st.session_state.ended = False
        st.rerun()

with st.sidebar:
    st.header("Über diesen Prototyp")
    st.write("Ein erster technischer Prototyp für das Üben lösungsorientierter Coachinggespräche mit Schülerinnen und Schülern. Die KI läuft über die Gemini API; das kostenlose Kontingent kann begrenzt sein.")
    st.write("**Auswertungskriterien**")
    st.markdown("1. Zielklärung und Zieldefinition\n2. Ideenanreicherung durch abwechslungsreiche Fragen\n3. Ressourcen und Ausnahmen\n4. Umsetzung und nächste Schritte\n5. Pacing und Abstimmung auf das Kind")
    st.caption("Die KI-Rückmeldung ist eine Lernhilfe, keine objektive Messung oder formale Beurteilung. Verwende ausschliesslich fiktive Angaben. Im kostenlosen Gemini-Kontingent können Anfragen zur Verbesserung von Google-Produkten verwendet werden.")
