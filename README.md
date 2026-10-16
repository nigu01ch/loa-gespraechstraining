# LOA-Trainingsapp – erster Prototyp

Dieser Prototyp simuliert ein Coachinggespräch zwischen einer Lehrperson und einem fiktiven Kind der 6. Klasse. Nach dem Gespräch erstellt die KI eine entwicklungsorientierte Auswertung anhand von fünf LOA-Kriterien.

## Was enthalten ist
- Drei fiktive Übungsfälle: Hausaufgaben werden häufig vergessen; ein Kind meldet sich selten, obwohl es oft die Antwort weiss; ein Rahmengespräch nach einer Handy-Regelverletzung.
- Chat mit einer KI, die in der Rolle des Kindes bleibt.
- Auswertung nach fünf LOA-Kriterien mit Gesprächsbelegen.
- Download von Gespräch und Auswertung als Textdatei.

## Was benötigt wird
- Windows-PC mit Python
- Google Gemini-API-Schlüssel und ein API-Konto (API-Nutzung kann separat kostenpflichtig sein)
- Internetverbindung

## Lokal starten (Windows)
1. Installiere Python von https://www.python.org/downloads/windows/.
2. Öffne im Windows-Startmenü die Eingabeaufforderung (`cmd`).
3. Wechsle in den entpackten Projektordner. Beispiel, falls der Ordner im Downloads-Ordner liegt:
   `cd %USERPROFILE%\Downloads\loa_trainingsapp`
4. Erstelle eine virtuelle Umgebung:
   `python -m venv .venv`
5. Aktiviere sie:
   `.venv\Scripts\activate`
6. Installiere die Abhängigkeiten:
   `python -m pip install -r requirements.txt`
7. Lege im Projektordner den Ordner `.streamlit` an (falls nicht vorhanden) und darin die Datei `secrets.toml`.
8. Trage in `secrets.toml` ein:
   `GEMINI_API_KEY = "DEIN_ECHTER_API_SCHLUESSEL"`
9. Starte die App:
   `streamlit run app.py`
10. Der Browser sollte sich öffnen. Falls nicht, kopiere die lokale Adresse aus dem Terminal in den Browser.

## Sicherheit
- Teile deinen API-Schlüssel mit niemandem und füge ihn niemals in `app.py` ein.
- Die Datei `.streamlit/secrets.toml` ist in `.gitignore` eingetragen und darf nicht in GitHub hochgeladen werden.
- Nutze ausschliesslich fiktive Übungsfälle. Gib keine echten oder identifizierenden Schüler-, Eltern- oder Personaldaten ein.
- Vor öffentlicher Veröffentlichung sind Datenschutz, Nutzungsgrenzen, Kosten und die aktuelle Hosting-Konfiguration zu prüfen.

## Hinweis
Dies ist ein erster Prototyp, noch keine produktionsreife oder datenschutzrechtlich geprüfte Anwendung. Die KI-Auswertung kann Fehler enthalten und sollte als Reflexionshilfe verstanden werden.


## Kostenloser Gemini-Prototyp

Diese Variante verwendet standardmässig `gemini-3.5-flash-lite`. Pro Gespräch sind bis zu 40 Nachrichten der Lehrperson möglich. Enthalten sind drei Übungsfälle, darunter ein Rahmengespräch nach einer Regelverletzung. Die bestehende Struktur der Gesprächsauswertung bleibt unverändert. Das kostenlose API-Kontingent unterliegt Raten- und Nutzungslimits und kann sich ändern. Für die kostenlose Nutzung können Eingaben zur Verbesserung von Google-Produkten verwendet werden. Deshalb ausschliesslich fiktive Übungsfälle und keine echten oder identifizierenden Schülerdaten eingeben.
