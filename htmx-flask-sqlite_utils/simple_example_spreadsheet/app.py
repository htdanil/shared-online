import html
from flask import Flask, request
from sqlite_utils import Database

app = Flask(__name__)

# --- DATABASE SETUP ---
def init_db():
    """Initializes the dynamically columned spreadsheet database."""
    db = Database("spreadsheet.db")
    
    # We drop the old static table structure just for clean testing 
    # of our new dynamic column logic!
    if "rows" in db.table_names() and "col1" not in db["rows"].columns_dict:
        db["rows"].drop()
        
    if "rows" not in db.table_names():
        db["rows"].insert_all([
            {"id": 1, "col1": "Rent", "col2": "Housing"},
            {"id": 2, "col1": "Groceries", "col2": "Food"}
        ], pk="id")

init_db()


# --- DYNAMIC HTML HELPERS ---

def get_columns():
    """Dynamically fetches all columns from the database, ignoring the primary key 'id'."""
    db = Database("spreadsheet.db")
    # Return all column names except 'id'
    return [c for c in db["rows"].columns_dict.keys() if c != "id"]


def _generate_row_html(row, cols):
    """Generates a single table row dynamically based on the current columns."""
    row_id = row['id']
    input_style = "width:100%; border:none; outline:none; background:transparent;"
    
    tds = ""
    for col in cols:
        # Get the value generically, defaulting to empty string if NULL
        val = html.escape(str(row.get(col) or ''))
        
        tds += f"""
        <td>
            <input type="text" name="{col}" value="{val}" 
                   hx-post="/update_row/{row_id}" hx-trigger="change" hx-swap="none" style="{input_style}">
        </td>
        """
        
    return f"""
    <tr id="row-{row_id}">
        {tds}
        <td style="text-align:center;">
            <button hx-delete="/delete_row/{row_id}" hx-target="closest tr" hx-swap="outerHTML" tabindex="-1" style="cursor:pointer; border:none; background:none;">❌</button>
        </td>
    </tr>
    """

def render_table():
    """Dynamically renders the complete table header and all rows."""
    db = Database("spreadsheet.db")
    cols = get_columns()
    data = list(db["rows"].rows)

    # 1. Dynamically Generate Table Headers
    th_html = ""
    for col in cols:
        th_html += f"""
        <th>
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span>{html.escape(col)}</span>
                <button hx-delete="/delete_col/{html.escape(col)}" 
                        hx-target="#table-container"
                        hx-confirm="Are you sure? This deletes the entire '{html.escape(col)}' column permanently!"
                        style="color:red; background:none; border:none; cursor:pointer;" 
                        title="Delete Column">✖</button>
            </div>
        </th>
        """
        
    # 2. Dynamically Generate Rows
    rows_html = "".join([_generate_row_html(r, cols) for r in data])
    
    return f"""
    <table>
        <thead>
            <tr>
                {th_html}
                <th style="width:30px;"></th>
            </tr>
        </thead>
        <tbody id="spreadsheet-body">
            {rows_html}
        </tbody>
    </table>
    """


# --- ROUTES ---

@app.route("/")
def index():
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <title>Dynamic HTMX Spreadsheet</title>
        <style>
            body {{ font-family: sans-serif; padding: 20px; }}
            
            table {{ border-collapse: collapse; width: 100%; max-width: 900px; margin-top:20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
            th, td {{ border: 1px solid #ccc; padding: 4px 8px; }}
            th {{ background-color: #f4f4f4; text-align:left; }}
            td:focus-within {{ outline: 2px solid #007bff; background-color: #f8fbff; }}
            
            .controls {{ margin-top: 20px; display: flex; gap: 15px; align-items:center; }}
            button {{ cursor: pointer; padding: 6px 12px; }}
        </style>
    </head>
    <body>
        <h2>HTMX Dynamic Spreadsheet</h2>
        <p>You can dynamically add/remove columns, rows, and auto-save cells!</p>
        
        <!-- The table is isolated in this container so HTMX can naturally redraw the whole block when columns change -->
        <div id="table-container">
            {render_table()}
        </div>
        
        <div class="controls">
            <!-- Append Row -->
            <button hx-post="/add_row" hx-target="#spreadsheet-body" hx-swap="beforeend">➕ Add Blank Row</button>
            
            <!-- Append Column -->
            <form hx-post="/add_col" hx-target="#table-container" hx-on::after-request="this.reset()" style="display:inline-flex; gap:5px;">
                <input type="text" name="col_name" placeholder="New column_name" required pattern="[a-zA-Z0-9_]+" title="Alphanumeric and underscores only" style="padding:6px;">
                <button type="submit">➕ Add Column</button>
            </form>
        </div>
        
    </body>
    </html>
    """

# --- ROW OPERATIONS ---

@app.route("/update_row/<int:row_id>", methods=["POST"])
def update_row(row_id):
    db = Database("spreadsheet.db")
    cols = get_columns()
    
    # Dynamically find which column input was silently posted
    update_data = {}
    for col in cols:
        if col in request.form:
            update_data[col] = request.form[col]
            
    if update_data:
        print(f"Auto-saving row {row_id} -> {update_data}")
        db["rows"].update(row_id, update_data)
        
    return "", 200

@app.route("/add_row", methods=["POST"])
def add_row():
    db = Database("spreadsheet.db")
    cols = get_columns()
    
    # Initialize all dynamic columns with empty string
    new_data = {c: "" for c in cols}
    inserted = db["rows"].insert(new_data)
    
    new_row = db["rows"].get(inserted.last_pk)
    return _generate_row_html(new_row, cols)

@app.route("/delete_row/<int:row_id>", methods=["DELETE"])
def delete_row(row_id):
    db = Database("spreadsheet.db")
    try:
        db["rows"].delete(row_id)
    except Exception:
        pass
    return ""


# --- COLUMN OPERATIONS ---

@app.route("/add_col", methods=["POST"])
def add_col():
    col_name = request.form.get("col_name", "").strip()
    
    if col_name and col_name.lower() != "id":
        db = Database("spreadsheet.db")
        try:
            # sqlite-utils adds the physical column to the database instantly
            db["rows"].add_column(col_name, str)
        except Exception as e:
            print("Error adding column:", e)
            
    # Redraw the entire table grid!
    return render_table()


@app.route("/delete_col/<col_name>", methods=["DELETE"])
def delete_col(col_name):
    if col_name and col_name.lower() != "id":
        db = Database("spreadsheet.db")
        try:
            # sqlite-utils handles dropping columns safely via table transformation under the hood
            db["rows"].transform(drop=[col_name])
        except Exception as e:
            print("Error dropping column:", e)
            
    # Redraw the entire table grid!
    return render_table()


if __name__ == "__main__":
    app.run(debug=True)
