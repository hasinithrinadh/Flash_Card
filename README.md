#  FlashGen

**A local AI flashcard generator.** Paste your study notes, get flashcards, and quiz yourself, all running on your own machine with no cloud API and no account.

FlashGen is built with [Streamlit](https://streamlit.io) for the interface and [Ollama](https://ollama.com) for local AI (default model: `gemma3:1b`). Your notes and cards are stored as plain JSON files.

---

## Features

- **Notes library**: paste text or upload a `.txt` file, and keep multiple note sets
- **AI flashcard generation**: choose 3 to 15 cards per note set
- **Offline fallback**: if Ollama isn't running, FlashGen creates fill-in-the-blank cards from your notes
- **Study mode**: reveal answers, mark "Got it" or "Missed it", and see your score at the end of each session
- **Weak cards first**: cards you miss more often show up earlier
- **Card management**: browse, delete, and track accuracy per card
- **Export**: download all your cards as JSON
- **Duplicate protection**: regenerating for the same notes skips questions that already exist

---

## Requirements

- Python 3.10 or newer
- [Ollama](https://ollama.com/download) (optional but recommended, for AI-generated cards)
- Python packages: `streamlit`, `requests`

---

## Installation

**1. Install the Python packages**

```bash
pip install streamlit requests
```

**2. Install Ollama and download the model**

Download Ollama from https://ollama.com/download, then run:

```bash
ollama pull gemma3:1b
```

Check that it's available:

```bash
ollama list
```

**3. Get the project**

Put `flashcard_app.py` in its own folder, for example `flashgen/`.

---

## Running the app

Open a terminal in the project folder and run:

```bash
python -m streamlit run flashcard_app.py
```

The app opens in your browser at `http://localhost:8501`.

> **Important:** Streamlit apps must be started with `streamlit run`. Running the file with plain `python flashcard_app.py` (or the VS Code Run button) will show "missing ScriptRunContext" warnings and won't open the app.

---

## How to use

1. **Add notes**: in the sidebar, enter a title, paste your notes (or upload a `.txt` file), and click **Save Notes**.
2. **Generate cards**: open the **Generate** tab, pick a note set, choose the number of cards, and click **Generate Flashcards**.
3. **Study**: open the **Study** tab, choose a deck, and click **Start / Restart Session**. Reveal each answer and mark whether you got it.
4. **Manage**: open the **Manage Cards** tab to review accuracy, delete cards, or export everything.

**Tip:** Notes with clear facts and definitions work best. Short or opinion-based text gives weaker cards.

---

## Project structure

```
flashgen/
├── flashcard_app.py          # The whole app
├── flashcard_notes.json      # Created automatically: your saved notes
└── flashcard_cards.json      # Created automatically: your flashcards and stats
```

The JSON files are created in the folder you run the app from, so always launch it from the same place to keep your data together.

---

## How it works

1. **Notes** are saved to `flashcard_notes.json`.
2. When you click Generate, the first ~3,500 characters of the notes are sent to the local Ollama model with a prompt asking for flashcards in a strict `Q:` / `A:` format.
3. A regex parser turns the model's reply into question and answer pairs. (This format is used instead of JSON because small models are unreliable at producing valid JSON.)
4. If Ollama can't be reached or returns nothing usable, a rule-based generator creates fill-in-the-blank cards instead.
5. Cards are saved with `correct` and `wrong` counters. Study sessions update these counters and use them to put weak cards first.

---

## Configuration

Settings are at the top of `flashcard_app.py`:

```python
NOTES_FILE = "flashcard_notes.json"
CARDS_FILE = "flashcard_cards.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:1b"
```

To get better card quality, use a larger model:

```bash
ollama pull gemma3:4b
```

Then set `MODEL_NAME = "gemma3:4b"`.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `missing ScriptRunContext` warnings | Run with `python -m streamlit run flashcard_app.py`, not `python flashcard_app.py` |
| `streamlit` is not recognized | Use `python -m streamlit run ...` instead |
| `File does not exist: flashcard_app.py` | Your terminal is in a different folder. `cd` to the project folder or use the full path |
| Yellow "Ollama wasn't reachable" message | Make sure Ollama is running (`ollama serve`) and that `ollama list` shows your model |
| `ollama` is not recognized | Install Ollama, then close and reopen the terminal |
| Cards are vague or inaccurate | Use clearer, more factual notes or switch to a larger model |

---

## Ideas for future improvements

- PDF upload (e.g. with `pypdf`)
- Spaced repetition scheduling (SM-2 style)
- Multiple-choice quiz mode with AI-generated distractors
- Export to Anki or CSV
- SQLite storage instead of JSON
- Semantic note search with embeddings

---

## Tech stack

- **Python**
- **Streamlit**: web UI
- **Ollama**: local LLM runtime
- **JSON**: lightweight storage
