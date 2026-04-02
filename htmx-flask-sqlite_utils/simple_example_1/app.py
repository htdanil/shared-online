import sqlite3
from flask import Flask, request
from sqlite_utils import Database

app = Flask(__name__, static_folder="static")

conn = sqlite3.connect("notes.db", check_same_thread=False)
db = Database(conn)

if not db["notes"].exists():
    db["notes"].create({
        "id": int,
        "title": str,
        "content": str,
        "priority": str
    }, pk="id")


def get_notes_html():
    rows = list(db["notes"].rows)
    
    if not rows:
        return '<p style="color: #666; font-style: italic;">No notes yet. Add one above!</p>'
    
    html = ""
    for note in rows:
        title = note.get('title', 'No Title')
        content = note.get('content', '')
        priority = note.get('priority', 'Normal')
        
        # We avoid using divs entirely as requested! Using nice semantic HTML5 tags instead.
        html += f"""
        <article class="note-item">
            <section>
                <header>
                    <strong style="font-size: 1.1rem; color: #333;">{title}</strong>
                    <span class="priority-badge">{priority}</span>
                </header>
                <p style="color: #555; margin: 0.5rem 0 0 0;">{content}</p>
            </section>
            <aside>
                <button class="delete-btn" hx-delete="/delete/{note['id']}" hx-target="#notes-list" hx-swap="innerHTML">
                    Delete
                </button>
            </aside>
        </article>
        """
    return html

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/notes", methods=["GET"])
def load_notes():
    return get_notes_html()

@app.route("/add", methods=["POST"])
def add_note():
    data = request.json or {}
    print("✨ Gathered scattered JSON payload:", data)
    
    title = data.get("title", "").strip()
    content = data.get("content", "").strip()
    priority = data.get("priority", "Normal").strip()
    
    if content or title:
        db["notes"].insert({
            "title": title if title else "Untitled",
            "content": content,
            "priority": priority
        })
    
    return get_notes_html()

@app.route("/delete/<int:note_id>", methods=["DELETE"])
def delete_note(note_id):
    db["notes"].delete(note_id)
    return get_notes_html()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
