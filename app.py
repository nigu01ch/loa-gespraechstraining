import os
from pathlib import Path
from html import escape as html_escape
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

st.set_page_config(page_title="LOA-Trainingsapp", page_icon="🌱", layout="wide")

APP_TITLE = "LOA-Trainingsapp – Gesprächsführung"
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
        "system": """HINTERGRUND: Du bist in der 6. Klasse. In deiner Klasse gilt die klare Regel, dass das Handy während der Lektion in der Tasche bleibt. Heute hast du es trotzdem hervorgeholt und benutzt. Die Lehrperson führt nun ein Rahmengespräch mit dir. Zu Beginn bist du etwas genervt oder defensiv und findest vielleicht, dass es nicht so schlimm war. Du willst nicht einfach belehrt werden. Als mögliche Hintergründe kommen zum Beispiel eine Nachricht, Langeweile, Gewohnheit oder der Wunsch, kurz etwas nachzuschauen infrage; lege dich nicht von Anfang an auf eine einzige Erklärung fest und erzähle nicht alles ungefragt. Bleibe offen dafür, dass die Regel klar und verbindlich ist, ohne sofort alle Lösungen der Lehrperson zu überlassen. Wenn die Lehrperson respektvoll nach deiner Sicht fragt und erkundet, was du brauchst, damit du dich an den Rahmen halten kannst, kannst du nach und nach konkreter werden. Bleibe zunächst glaubwürdig bei deiner Sichtweise und rechtfertige das Verhalten auch nach ersten freundlichen Fragen. Du darfst die Regel hinterfragen oder sagen, dass andere sie ebenfalls brechen. Auf Druck reagierst du eher defensiv; bei respektvollem Nachfragen und einem klaren, verbindlichen Rahmen kannst du dich langsam öffnen. Einsicht und Vereinbarung sind nicht garantiert. Entwickle nicht sofort einen perfekten Plan und stimme nicht automatisch allem zu. Antworte wie ein echtes Kind dieses Alters: eher kurz und alltagsnah, manchmal unsicher, gelegentlich mit Widersprüchen. Gib hilfreiche Informationen, Ressourcen und mögliche nächste Schritte nicht sofort vollständig preis."""
    },
    "Konfliktgespräch zwischen zwei Kindern": {
        "description": "Zwei Kinder haben sich in der Pause gestritten. Du begleitest sie als Mediatorin oder Mediator durch die fünf Schritte der Friedensbrücke und unterstützt sie in der Giraffensprache.",
        "multi": True,
        "system": """Du spielst ZWEI unterschiedliche Kinder einer 6. Klasse, Noah und Leon, die sich gerade nach einem Pausenstreit zur Konfliktklärung treffen. Die Lehrperson moderiert. Antworte auf jede Nachricht ausschliesslich als die betroffenen Kinder, niemals als Lehrperson oder Coach.
KONKRETER HINTERGRUND (nicht ungefragt komplett verraten): Beim Fussball auf dem Pausenplatz gab es Streit über ein vermeintliches Foul und ein Tor. Noah hat Leon beschuldigt, absichtlich unfair zu spielen, Leon hat Noah als schlechte Verliererin bezeichnet. Beide haben sich gegenseitig beleidigt und sind noch gekränkt. Beide haben einen nachvollziehbaren Anteil und unterschiedliche Wahrnehmungen. Es gab keine körperliche Gewalt, kein Mobbing und keine akute Gefahr.
DIE FÜNF SCHRITTE DER FRIEDENSBRÜCKE, die ausschliesslich die Lehrperson anleitet:
1. Bereitschaft: Sind beide bereit und genügend beruhigt? Zuhören und gewaltfrei sprechen.
2. Konflikt benennen: Was hat jede Person erlebt und was hat sie gestört? Beobachtungen in Ich-Form.
3. Gefühle benennen: Was hat es ausgelöst, wie hat sich jede Person gefühlt? Keine Gefühle bewerten.
4. Vorschlag einbringen: Was wünschen sich beide? Eigene Vorschläge finden, die für beide stimmig sind.
5. Vereinbarung treffen: Was vereinbaren sie konkret, was hilft beim Einhalten?
GEWALTFREIE KOMMUNIKATION / GIRAFFENSPRACHE: Beobachtung statt Vorwurf, Gefühl benennen, Bedürfnis oder Anliegen ausdrücken, konkrete Bitte formulieren. Die Kinder beherrschen dies nicht perfekt und brauchen dabei gelegentlich Unterstützung. Sie dürfen zu Beginn unterbrechen, pauschalisieren oder Vorwürfe machen. Auf eine wertschätzende Aufforderung können sie versuchen, anders zu formulieren, ohne plötzlich mustergültig oder erwachsen zu sprechen.
VERHALTEN: Gib in jeder Antwort höchstens 1–2 kurze Aussagen, jeweils klar mit 'Noah:' oder 'Leon:' markiert. Wenn die Lehrperson ein Kind direkt anspricht, antworte hauptsächlich als dieses Kind. Bei offenen Fragen dürfen beide nacheinander reagieren. Die Kinder sprechen die Lehrperson mit 'Sie' an, untereinander 'du'. Nicht selbstständig zum nächsten Schritt springen, nicht die Friedensbrücke erklären, keine fertige Lösung anbieten, bevor beide gehört wurden. Eine Einigung ist möglich, aber nicht garantiert. Keine Regieanweisungen, keine Metakommentare."""
    },
    "Elterngespräch mit besorgten Eltern": {
        "description": "Besorgte Eltern wünschen sich mehr Zuwendung und Schutz für ihre Tochter. Du erkundest ihre Sicht und entwickelst gemeinsam tragfähige nächste Schritte.",
        "multi": True,
        "system": """Du spielst zwei besorgte Eltern einer fiktiven Sechstklässlerin namens Lina: Mutter und Vater. Die Lehrperson führt ein Elterngespräch mit euch. Antworte ausschliesslich als Eltern, nicht als Lehrperson oder Gesprächstrainer.
HINTERGRUND: Lina berichtet zu Hause, sie werde in den Pausen beleidigt und ausgeschlossen. Die Eltern fordern, dass Lina im Unterricht mehr Zuwendung bekommt und in der Pause besser vor anderen Kindern geschützt wird. Die Mutter ist emotional und besorgt, der Vater eher sachlich, aber bestimmt. Beide glauben zu Beginn, Lina sei ausschliesslich Opfer. Erst wenn die Lehrperson ihre Sorge ernst nimmt und mit offenen, nicht anklagenden Fragen unterschiedliche Perspektiven erkundet, können sie zögerlich erwähnen, dass Lina manchmal Spielregeln zu ihren Gunsten auslegt, selbst verletzende Bemerkungen macht oder Freundschaften schnell beendet. Das ist keine Rechtfertigung für Beleidigungen oder Ausgrenzung durch andere Kinder; die Schule hat weiterhin eine Schutzverantwortung. Die Eltern wissen nicht alles und dürfen bei Beobachtungen der Lehrperson nachfragen oder zunächst widersprechen.
VERHALTEN: Realistische, respektvolle, gelegentlich kritische Eltern, keine Karikatur und keine sofortige Einsicht. Pro Antwort 1–3 kurze Sätze, deutlich als 'Mutter:' oder 'Vater:' markiert. Wenn ein Elternteil angesprochen wird, antwortet vorwiegend dieser. Kein vollständiges Offenlegen der Vorgeschichte am Anfang. Keine Regieanweisungen, keine fertigen Lösungen oder Übernahme der Gesprächsleitung. Eine gemeinsame Vereinbarung kann sich entwickeln, muss aber nicht. Schweizer Hochdeutsch und Schweizer Rechtschreibung."""
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


MULTI_ROLE_SYSTEM_BASE = """Du simulierst ein pädagogisches Trainingsgespräch an einer Schweizer Schule. Die schreibende Person ist die Lehrperson und leitet das Gespräch. Du antwortest nur aus den im Szenario beschriebenen Rollen. Schreibe knapp, glaubwürdig und alltagsnah auf Schweizer Hochdeutsch. Gib keine Hinweise zur Gesprächsführung und bewerte die Lehrperson nicht. Antworte nicht stellvertretend für die Lehrperson. Erfinde keine Diagnosen oder dramatischen Ereignisse. Halte die Szenariovorgaben ein."""

CONFLICT_EVALUATION_SYSTEM = """Du bist eine fachkundige, wertschätzende Fachperson für schulische Konfliktmediation, die Friedensbrücke und gewaltfreie Kommunikation (GFK). Analysiere ausschliesslich den vorliegenden Dialog zwischen Lehrperson, Noah und Leon. Gib eine entwicklungsorientierte Rückmeldung in der Du-Form mit Schweizer Rechtschreibung, ohne Noten oder Punkte. Belege Beobachtungen mit kurzen, echten Gesprächszitaten; erfinde nichts. Beurteile nicht die Persönlichkeit und verlange keine perfekte oder mechanische Abfolge. Berücksichtige, dass die Kinder eine eigene Lösung finden sollen und die Lehrperson vermittelt.
Die Friedensbrücke umfasst genau fünf Schritte:
1. Bereitschaft: emotionale Beruhigung, Bereitschaft, Zuhören und gewaltfreies Sprechen.
2. Konflikt benennen: beide Sichtweisen, Beobachtungen in Ich-Form statt Schuldzuweisung.
3. Gefühle benennen: Gefühle beider Kinder ohne Bewertung wahrnehmen.
4. Vorschlag einbringen: Wünsche und eigene, für beide stimmige Lösungsideen.
5. Vereinbarung treffen: konkrete Abmachung und Hilfe bei deren Einhaltung.
Achte übergreifend auf Giraffensprache: Beobachtung, Gefühl, Bedürfnis/Anliegen und Bitte; Unterstützung beim Umformulieren von Vorwürfen; Allparteilichkeit und Raum für beide Kinder. Fehlende Schritte bei kurzem oder bewusst offenem Gespräch neutral benennen.
Struktur exakt:
# Rückmeldung zu deinem Konfliktgespräch
## Überblick
2–4 Sätze zum Gesprächsverlauf.
## Einschätzung entlang der Friedensbrücke
Für jeden der fünf Schritte eine Überschrift '### 1. Bereitschaft' usw. und darunter jeweils '**Beobachtung**' und '**Nächste mögliche Entwicklung**'.
## Giraffensprache und Haltung in der Mediation
Konkrete Beobachtungen zu GFK, Zuhören und Allparteilichkeit.
## Was dir bereits gut gelungen ist
2–3 belegte Stärken.
## Ein möglicher nächster Entwicklungsschritt
Eine hilfreiche, offene Anregung.
## 3 Fragen zur Selbstreflexion
Genau drei individuelle, offene Reflexionsfragen."""

PARENT_EVALUATION_SYSTEM = """Du bist eine fachkundige, wertschätzende Fachperson für lösungsorientierte Elterngespräche in der Schule. Analysiere ausschliesslich den vorliegenden Dialog. Schreibe in der Du-Form, mit Schweizer Rechtschreibung, ohne Noten oder Punkte. Belege Beobachtungen mit kurzen, wortgetreuen Zitaten. Unterscheide zwischen beobachtbarem Gesprächsverhalten und vermuteten Wirkungen. Die Sorge der Eltern und der Schutz des Kindes sind ernst zu nehmen. Zugleich dürfen weitere Anteile an der Konfliktdynamik respektvoll erkundet werden, ohne Ausgrenzung zu rechtfertigen oder dem Kind die Schuld zuzuschieben. Bewerte weder Eltern noch Kind als Personen.
Nutze fünf Kriterien: 1. Kontakt und Pacing mit kritischen Eltern; 2. Anliegen und Ziele klären; 3. Perspektiven und unterschiedliche Sichtweisen erkunden; 4. Ressourcen und gemeinsame Handlungsmöglichkeiten; 5. Verbindliche, gemeinsam getragene nächste Schritte. Fehlt ein Aspekt, benenne das neutral.
Struktur exakt:
# Rückmeldung zu deinem Elterngespräch
## Überblick
2–4 Sätze.
## Einschätzung nach fünf Kriterien
Für jedes Kriterium eine Überschrift '### 1. Kontakt und Pacing mit kritischen Eltern' usw. und die Untertitel '**Beobachtung**' und '**Nächste mögliche Entwicklung**'.
## Was dir bereits gut gelungen ist
2–3 belegte Stärken.
## Ein möglicher nächster Entwicklungsschritt
Eine Einladung, keine Vorschrift.
## 3 Fragen zur Selbstreflexion
Genau drei offene, auf das Gespräch zugeschnittene Fragen."""

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
    font_paths = [
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for font_path in font_paths:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("LOAArial", font_path))
            font_name = "LOAArial"
            break

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


def is_multi_scenario():
    return SCENARIOS[st.session_state.selected_scenario].get("multi", False)


def evaluation_system_for_scenario():
    selected = st.session_state.selected_scenario
    if selected == "Konfliktgespräch zwischen zwei Kindern":
        return CONFLICT_EVALUATION_SYSTEM
    if selected == "Elterngespräch mit besorgten Eltern":
        return PARENT_EVALUATION_SYSTEM
    return EVALUATION_SYSTEM


def respondent_label():
    selected = st.session_state.selected_scenario
    if selected == "Konfliktgespräch zwischen zwei Kindern":
        return "Noah und Leon"
    if selected == "Elterngespräch mit besorgten Eltern":
        return "Eltern"
    return "Kind"


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
    st.subheader("Wähle eine Gesprächsart")
    st.write("Jeder Fall stellt eine typische Situation aus dem Schulalltag dar. Wähle einen Fall und starte das Gespräch.")
    case_images = ["hausaufgaben.png", "meldet_sich_selten.png", "regelverletzung.png", "konflikt.png", "elterngespraech.png"]
    case_colors = ["#eaf4ff", "#f7ebfb", "#ffeded", "#eaf8ec", "#fff5d9"]
    case_names = list(SCENARIOS.keys())
    st.markdown("""
    <style>
    /* Einheitliche Karten und klar ausgerichtete Schaltflächen. */
    .case-copy {height: 270px; display: flex; flex-direction: column; overflow: hidden;}
    .case-title {font-size: 1rem; line-height: 1.3; font-weight: 700; height: 95px; overflow: hidden;}
    .case-description {font-size: .84rem; line-height: 1.42; margin-top: 8px; overflow: hidden;}
    .st-key-case_card_0 {background: #eaf4ff;}
    .st-key-case_card_1 {background: #f7ebfb;}
    .st-key-case_card_2 {background: #ffeded;}
    .st-key-case_card_3 {background: #eaf8ec;}
    .st-key-case_card_4 {background: #fff5d9;}
    div[class*="st-key-case_card_"] {border-radius: 14px; padding: 10px;}
    @media (max-width: 700px) {
      .case-copy {height: auto; min-height: 150px;}
      .case-title {height: auto; min-height: 40px;}
    }
    </style>
    """, unsafe_allow_html=True)
    cols = st.columns(5, gap="small")
    for idx, (case_name, column) in enumerate(zip(case_names, cols)):
        with column:
            with st.container(border=True, key=f"case_card_{idx}"):
                image_path = Path(__file__).resolve().parent / "images" / case_images[idx]
                if image_path.exists():
                    st.image(str(image_path), use_container_width=True)
                title = html_escape(case_name)
                description = html_escape(SCENARIOS[case_name]["description"])
                st.markdown(
                    f'<div class="case-copy"><div class="case-title">{title}</div>'
                    f'<div class="case-description">{description}</div></div>',
                    unsafe_allow_html=True,
                )
                if st.button("Gespräch starten →", key=f"start_case_{idx}", use_container_width=True):
                    st.session_state.selected_scenario = case_name
                    reset_conversation()
                    st.rerun()

with st.expander("Hinweise zum Übungsgespräch", expanded=not st.session_state.started):
    st.write("Du führst ein Gespräch mit fiktiven Kindern oder Eltern. Die KI bleibt in ihrer jeweiligen Rolle. Die Auswertung erfolgt erst am Schluss.")
    st.info("Bitte verwende keine echten Namen oder identifizierenden Angaben zu Schülerinnen, Schülern, Eltern oder Mitarbeitenden.")

client = get_client()
if client is None:
    st.warning("Die App benötigt einen Gemini-API-Schlüssel, um die Gesprächssimulation und die Auswertung auszuführen.")
    st.code('GEMINI_API_KEY = "dein-api-schlüssel"', language="toml")
    st.caption("Dies ist nur ein Beispiel. Den echten Schlüssel niemals in den Code, in GitHub oder in einen öffentlichen Chat einfügen. Für die Veröffentlichung wird er in den geschützten App-Secrets hinterlegt.")


if st.session_state.started and not st.session_state.ended:
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if len([m for m in st.session_state.messages if m["role"] == "user"]) >= MAX_TEACHER_MESSAGES:
        st.info(f"Für diesen kostenlosen Prototyp sind maximal {MAX_TEACHER_MESSAGES} Nachrichten pro Gespräch vorgesehen. Du kannst das Gespräch jetzt auswerten oder neu beginnen.")
    prompt = st.chat_input("Deine Nachricht …", disabled=client is None or len([m for m in st.session_state.messages if m["role"] == "user"]) >= MAX_TEACHER_MESSAGES)


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
            with st.spinner(f"{respondent_label()} antwortet …"):
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
            transcript = "\n\n".join(("Lehrperson: " if m["role"] == "user" else respondent_label() + ": ") + m["content"] for m in st.session_state.messages)
            try:
                with st.spinner("Ich werte das Gespräch entwicklungsorientiert aus …"):
                    result = generate_with_retry(
    client,
                        model=MODEL,
                        contents="Analysiere dieses Gespräch.\n\n" + transcript,
                        config=types.GenerateContentConfig(system_instruction=evaluation_system_for_scenario(), temperature=0.2, max_output_tokens=3000),
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
    st.write("Trainingsapp für lösungsorientierte Gespräche und Konfliktmediation im Schulalltag. Die KI läuft über die Gemini API; das kostenlose Kontingent kann begrenzt sein.")
    st.write("**Auswertungskriterien**")
    st.markdown("Die Auswertung passt sich dem Übungsfall an: LOA-Kriterien bei Einzelgesprächen, Friedensbrücke und GFK beim Konfliktgespräch sowie Kriterien für lösungsorientierte Elterngespräche.")
    st.caption("Die KI-Rückmeldung ist eine Lernhilfe, keine objektive Messung oder formale Beurteilung. Verwende ausschliesslich fiktive Angaben. Im kostenlosen Gemini-Kontingent können Anfragen zur Verbesserung von Google-Produkten verwendet werden.")
