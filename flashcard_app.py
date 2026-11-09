import streamlit as st
import json
import os
import re
import random
import requests
from datetime import datetime

NOTES_FILE = "flashcard_notes.json"
CARDS_FILE = "flashcard_cards.json"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma3:1b"


# ---------- Storage helpers ----------

def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return []


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, ensure_ascii=False)


def next_id(items):
    return max([item["id"] for item in items], default=0) + 1


# ---------- Notes ----------

def add_note(title, text):
    notes = load_json(NOTES_FILE)
    note = {
        "id": next_id(notes),
        "title": title,
        "text": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    notes.append(note)
    save_json(NOTES_FILE, notes)
    return note


def delete_note(note_id):
    notes = [n for n in load_json(NOTES_FILE) if n["id"] != note_id]
    save_json(NOTES_FILE, notes)

    cards = [c for c in load_json(CARDS_FILE) if c["note_id"] != note_id]
    save_json(CARDS_FILE, cards)


# ---------- Cards ----------

def add_cards(note_id, new_cards):
    cards = load_json(CARDS_FILE)
    existing = {c["question"].lower() for c in cards if c["note_id"] == note_id}
    added = 0

    for q, a in new_cards:
        if q.lower() in existing:
            continue
        cards.append({
            "id": next_id(cards),
            "note_id": note_id,
            "question": q,
            "answer": a,
            "correct": 0,
            "wrong": 0,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })
        existing.add(q.lower())
        added += 1

    save_json(CARDS_FILE, cards)
    return added


def delete_card(card_id):
    cards = [c for c in load_json(CARDS_FILE) if c["id"] != card_id]
    save_json(CARDS_FILE, cards)


def record_result(card_id, was_correct):
    cards = load_json(CARDS_FILE)
    for card in cards:
        if card["id"] == card_id:
            if was_correct:
                card["correct"] += 1
            else:
                card["wrong"] += 1
    save_json(CARDS_FILE, cards)


# ---------- AI ----------

def ask_ollama(prompt):
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=180,
        )
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        return None
    except Exception:
        return None


def build_prompt(text, count):
    return f"""
You are a flashcard generator for students.

Create exactly {count} flashcards from the notes below.

Rules:
- Each flashcard tests ONE idea.
- Questions must be clear and specific.
- Answers must be short (1-2 sentences).
- Use ONLY information from the notes. Do not invent facts.
- Use exactly this format and nothing else:

Q: question here
A: answer here

Notes:
{text}
"""


def parse_cards(raw):
    pattern = r"Q:\s*(.+?)\s*A:\s*(.+?)(?=\n\s*Q:|\Z)"
    matches = re.findall(pattern, raw, flags=re.DOTALL)
    cards = []
    for q, a in matches:
        q = " ".join(q.split())
        a = " ".join(a.split())
        if q and a:
            cards.append((q, a))
    return cards


def fallback_cards(text, count):
    """Used when Ollama is offline: turns sentences into fill-in-the-blank cards."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cards = []

    for sentence in sentences:
        words = sentence.split()
        if len(words) < 6:
            continue
        candidates = [w for w in words if len(w.strip(".,;:!?")) > 5]
        if not candidates:
            continue
        target = max(candidates, key=lambda w: len(w))
        answer = target.strip(".,;:!?")
        question = "Fill in the blank: " + sentence.replace(target, "_____", 1)
        cards.append((question, answer))
        if len(cards) >= count:
            break

    return cards


def generate_cards(text, count):
    raw = ask_ollama(build_prompt(text[:3500], count))

    if raw:
        cards = parse_cards(raw)
        if cards:
            return cards[:count], "ai"

    return fallback_cards(text, count), "fallback"


# ---------- Page setup ----------

st.set_page_config(page_title="FlashGen", page_icon="🃏", layout="wide")

st.title("🃏 FlashGen")
st.caption("Paste your notes. Get flashcards. Study them.")

defaults = {
    "queue": [],
    "pos": 0,
    "show_answer": False,
    "session_right": 0,
    "session_wrong": 0,
}
for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ---------- Sidebar: notes ----------

with st.sidebar:
    st.header("📚 Notes Library")

    notes = load_json(NOTES_FILE)
    cards_all = load_json(CARDS_FILE)

    col1, col2 = st.columns(2)
    col1.metric("Notes", len(notes))
    col2.metric("Cards", len(cards_all))

    st.divider()
    st.subheader("Add Notes")

    note_title = st.text_input("Title (e.g. Biology Ch.3)")
    note_text = st.text_area("Paste your notes", height=180)

    uploaded = st.file_uploader("...or upload a .txt file", type=["txt"])
    if uploaded is not None and not note_text.strip():
        note_text = uploaded.read().decode("utf-8", errors="ignore")

    if st.button("💾 Save Notes", use_container_width=True):
        if note_title.strip() and note_text.strip():
            add_note(note_title.strip(), note_text.strip())
            st.success("Notes saved!")
            st.rerun()
        else:
            st.warning("Please add a title and some text.")

    st.divider()
    st.subheader("Saved Notes")

    if notes:
        for note in notes:
            count = len([c for c in cards_all if c["note_id"] == note["id"]])
            st.write(f"**{note['title']}** — {count} cards")
            if st.button(f"Delete '{note['title']}'", key=f"del_note_{note['id']}"):
                delete_note(note["id"])
                st.session_state.queue = []
                st.rerun()
    else:
        st.info("No notes yet.")


notes = load_json(NOTES_FILE)
note_lookup = {n["id"]: n for n in notes}

tab_generate, tab_study, tab_manage = st.tabs(
    ["⚡ Generate", "🎓 Study", "🗂️ Manage Cards"]
)


# ---------- Tab 1: Generate ----------

with tab_generate:
    if not notes:
        st.info("Add some notes in the sidebar to get started.")
    else:
        selected_id = st.selectbox(
            "Choose notes",
            options=list(note_lookup.keys()),
            format_func=lambda i: note_lookup[i]["title"],
        )
        card_count = st.slider("Number of cards", 3, 15, 8)

        with st.expander("Preview notes"):
            st.write(note_lookup[selected_id]["text"])

        if st.button("⚡ Generate Flashcards", type="primary"):
            with st.spinner("Generating flashcards..."):
                new_cards, source = generate_cards(
                    note_lookup[selected_id]["text"], card_count
                )

            if not new_cards:
                st.error("Couldn't generate cards. Try longer or clearer notes.")
            else:
                added = add_cards(selected_id, new_cards)
                if source == "ai":
                    st.success(f"Added {added} new flashcards.")
                else:
                    st.warning(
                        f"Ollama wasn't reachable, so I made {added} "
                        "fill-in-the-blank cards instead."
                    )
                for q, a in new_cards:
                    with st.expander(q):
                        st.write(a)


# ---------- Tab 2: Study ----------

with tab_study:
    cards = load_json(CARDS_FILE)

    if not cards:
        st.info("Generate some flashcards first.")
    else:
        deck_options = {0: "All notes"}
        for n in notes:
            deck_options[n["id"]] = n["title"]

        deck_id = st.selectbox(
            "Deck",
            options=list(deck_options.keys()),
            format_func=lambda i: deck_options[i],
            key="deck_select",
        )
        weak_first = st.checkbox("Show weak cards first", value=True)

        if st.button("▶️ Start / Restart Session"):
            deck = [c for c in cards if deck_id == 0 or c["note_id"] == deck_id]
            random.shuffle(deck)
            if weak_first:
                deck.sort(key=lambda c: c["correct"] - c["wrong"])
            st.session_state.queue = [c["id"] for c in deck]
            st.session_state.pos = 0
            st.session_state.show_answer = False
            st.session_state.session_right = 0
            st.session_state.session_wrong = 0
            st.rerun()

        queue = st.session_state.queue

        if not queue:
            st.caption("Press Start to begin studying.")
        elif st.session_state.pos >= len(queue):
            total = st.session_state.session_right + st.session_state.session_wrong
            st.balloons()
            st.success(
                f"Session complete! You got {st.session_state.session_right} "
                f"of {total} right."
            )
        else:
            card_map = {c["id"]: c for c in cards}
            card = card_map.get(queue[st.session_state.pos])

            if card is None:
                st.session_state.pos += 1
                st.rerun()
            else:
                st.progress(
                    st.session_state.pos / len(queue),
                    text=f"Card {st.session_state.pos + 1} of {len(queue)}",
                )

                st.markdown(f"### ❓ {card['question']}")

                if not st.session_state.show_answer:
                    if st.button("👀 Show Answer", use_container_width=True):
                        st.session_state.show_answer = True
                        st.rerun()
                else:
                    st.info(f"**Answer:** {card['answer']}")

                    c1, c2 = st.columns(2)
                    if c1.button("✅ Got it", use_container_width=True):
                        record_result(card["id"], True)
                        st.session_state.session_right += 1
                        st.session_state.pos += 1
                        st.session_state.show_answer = False
                        st.rerun()
                    if c2.button("❌ Missed it", use_container_width=True):
                        record_result(card["id"], False)
                        st.session_state.session_wrong += 1
                        st.session_state.pos += 1
                        st.session_state.show_answer = False
                        st.rerun()


# ---------- Tab 3: Manage ----------

with tab_manage:
    cards = load_json(CARDS_FILE)

    if not cards:
        st.info("No flashcards yet.")
    else:
        total_right = sum(c["correct"] for c in cards)
        total_wrong = sum(c["wrong"] for c in cards)
        attempts = total_right + total_wrong

        m1, m2, m3 = st.columns(3)
        m1.metric("Total cards", len(cards))
        m2.metric("Attempts", attempts)
        m3.metric(
            "Accuracy",
            f"{round(100 * total_right / attempts)}%" if attempts else "—",
        )

        st.divider()

        for card in cards:
            deck_name = note_lookup.get(card["note_id"], {}).get("title", "Unknown")
            with st.expander(f"[{deck_name}] {card['question']}"):
                st.write(f"**Answer:** {card['answer']}")
                st.caption(
                    f"Correct: {card['correct']} | Missed: {card['wrong']}"
                )
                if st.button("Delete card", key=f"del_card_{card['id']}"):
                    delete_card(card["id"])
                    st.rerun()

        st.divider()
        st.download_button(
            "⬇️ Export cards (JSON)",
            data=json.dumps(cards, indent=2, ensure_ascii=False),
            file_name="flashcards.json",
            mime="application/json",
        )
