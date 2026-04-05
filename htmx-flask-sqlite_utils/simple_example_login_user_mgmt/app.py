import html
from flask import Flask, request, session, redirect, url_for
from sqlite_utils import Database
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_dev_key"

# --- DATABASE SETUP ---
def init_db():
    """Initializes the database, dropping old schema to add our new 'role' column."""
    db = Database("users.db")
    
    # For development, drop old tables so we don't have schema conflicts
    if "users" in db.table_names():
        db["users"].drop()
        
    # Create the admin user
    db["users"].insert({
        "username": "admin",
        "password_hash": generate_password_hash("admin123"),
        "role": "admin"
    }, pk="username")
    
    # Create a normal default user
    db["users"].insert({
        "username": "guest",
        "password_hash": generate_password_hash("guest123"),
        "role": "user"
    }, pk="username")

init_db()


# --- HTML RENDER HELPERS ---

def render_user_row(user):
    """Returns a standard HTML table row for a user."""
    username = html.escape(user['username'])
    role = html.escape(user['role'])
    
    # Prevent deleting the main admin account to avoid lockouts
    delete_btn = ""
    if username != "admin":
        delete_btn = f"""
        <button style="color:red;" 
                hx-delete="/admin/delete/{username}" 
                hx-target="closest tr" 
                hx-swap="outerHTML"
                hx-confirm="Are you sure you want to delete {username}?">Delete</button>
        """
                               
    return f"""
    <tr>
        <td>{username}</td>
        <td>{role}</td>
        <td>
            <button hx-get="/admin/edit/{username}" hx-target="closest tr" hx-swap="outerHTML">Edit</button>
            {delete_btn}
        </td>
    </tr>
    """

def render_user_edit_row(user):
    """Returns an inline HTML edit form replacing the standard row."""
    username = html.escape(user['username'])
    role = user['role']
    
    admin_sel = "selected" if role == "admin" else ""
    user_sel = "selected" if role == "user" else ""
    
    return f"""
    <tr style="background-color: #f9f9f9;">
        <td>{username}</td>
        <td>
            <!-- Let's link this select to the hidden form via html 'form' attribute -->
            <select name="role" form="edit-form-{username}">
                <option value="user" {user_sel}>user</option>
                <option value="admin" {admin_sel}>admin</option>
            </select>
        </td>
        <td>
            <form id="edit-form-{username}" 
                  hx-post="/admin/edit/{username}" 
                  hx-target="closest tr" 
                  hx-swap="outerHTML">
                <input type="password" name="new_password" placeholder="New Password (optional)" style="width:180px;">
                <button type="submit" style="color:green;">Save</button>
                <button type="button" hx-get="/admin/cancel_edit/{username}" hx-target="closest tr" hx-swap="outerHTML">Cancel</button>
            </form>
        </td>
    </tr>
    """

# --- ROUTES ---

@app.route("/")
def index():
    if "username" in session: return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        db = Database("users.db")
        try:
            user = db["users"].get(username)
            if check_password_hash(user["password_hash"], password):
                session["username"] = username
                session["role"] = user.get("role", "user") # Store role securely in session!
                return "", 200, {"HX-Redirect": url_for("dashboard")}
            else:
                error = "<p style='color:red;'>Incorrect password!</p>"
        except Exception:
            error = "<p style='color:red;'>User not found!</p>"

        # UI FIX: If it's an HTMX request reacting to the form post, return JUST the error snippet.
        if request.headers.get("HX-Request"):
            return error

    return f"""
    <!DOCTYPE html>
    <html>
    <head><script src="https://unpkg.com/htmx.org@1.9.10"></script><title>Login</title></head>
    <body style="font-family:sans-serif; max-width:400px; margin:auto; padding:20px;">
        <h2>System Login</h2>
        <p>Try <b>admin</b> / <b>admin123</b> <br>or <b>guest</b> / <b>guest123</b></p>
        <form hx-post="/login" hx-target="#msg">
            <input type="text" name="username" placeholder="Username" required><br><br>
            <input type="password" name="password" placeholder="Password" required><br><br>
            <button type="submit">Login</button>
        </form>
        <div id="msg">{error}</div>
    </body>
    </html>
    """

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if "username" not in session: return redirect(url_for("login"))
    
    username = html.escape(session['username'])
    role = html.escape(session.get('role', 'user'))
    
    # Hide the Admin link entirely if the user is not an admin!
    admin_link = ""
    if role == "admin":
        admin_link = '<br><br><a href="/admin">⚙️ Open User Administration</a>'
        
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Dashboard</title></head>
    <body style="font-family:sans-serif; padding:20px;">
        <h2>Welcome to the Dashboard, {username}!</h2>
        <p>Your current assigned role is: <b>{role}</b></p>
        
        <a href="/logout">🚪 Logout</a>
        {admin_link}
    </body>
    </html>
    """


@app.route("/admin", methods=["GET"])
def admin():
    # SECURITY: Verify the user is strictly an admin
    if session.get("role") != "admin": return "Forbidden: Admins only", 403
        
    db = Database("users.db")
    users = list(db["users"].rows)
    users_html = "".join([render_user_row(u) for u in users])
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://unpkg.com/htmx.org@1.9.10"></script>
        <title>User Admin</title>
    </head>
    <body style="font-family:sans-serif; padding:20px; max-width:600px; margin:auto;">
        <h2>User Management</h2>
        
        <table border="1" cellpadding="8" cellspacing="0" style="width:100%; text-align:left;">
            <thead><tr><th>Username</th><th>Role</th><th>Actions</th></tr></thead>
            <tbody id="user-list">
                {users_html}
            </tbody>
        </table>
        
        <br><hr><br>
        
        <h3>Add New User</h3>
        <form hx-post="/admin/add" hx-target="#user-list" hx-swap="beforeend" hx-on::after-request="this.reset()">
            <input type="text" name="new_username" placeholder="Username" required>
            <input type="password" name="new_password" placeholder="Password" required>
            <select name="role">
                <option value="user">user</option>
                <option value="admin">admin</option>
            </select>
            <button type="submit">Add</button>
        </form>
        
        <br><br>
        <a href="/dashboard">⬅ Back to Dashboard</a>
    </body>
    </html>
    """

@app.route("/admin/add", methods=["POST"])
def add_user():
    if session.get("role") != "admin": return "Forbidden", 403
        
    new_username = request.form.get("new_username")
    new_password = request.form.get("new_password")
    role = request.form.get("role", "user")
    
    if not new_username or not new_password: return "Missing data", 400
        
    db = Database("users.db")
    try:
        db["users"].get(new_username)
        return f"<tr style='color:red;'><td colspan='3'>Error: {html.escape(new_username)} exists!</td></tr>"
    except Exception:
        pass

    db["users"].insert({
        "username": new_username,
        "password_hash": generate_password_hash(new_password),
        "role": role
    }, pk="username")
    
    new_user = db["users"].get(new_username)
    return render_user_row(new_user)

@app.route("/admin/delete/<username>", methods=["DELETE"])
def delete_user(username):
    # Uses HTMX DELETE method
    if session.get("role") != "admin": return "Forbidden", 403
    if username == "admin": return "Cannot delete admin", 403 # Safety check
    
    db = Database("users.db")
    try:
        db["users"].delete(username)
    except Exception:
        pass
        
    # Returing an empty string clears the element from the DOM (since hx-swap is outerHTML)
    return ""

@app.route("/admin/edit/<username>", methods=["GET", "POST"])
def edit_user(username):
    """Handles both rendering the inline edit form (GET) and saving it (POST)"""
    if session.get("role") != "admin": return "Forbidden", 403
    
    db = Database("users.db")
    try:
        user = db["users"].get(username)
    except Exception:
        return "User not found", 404
        
    # GET: Swap table row with edit form
    if request.method == "GET":
        return render_user_edit_row(user)
        
    # POST: Save updates
    new_role = request.form.get("role")
    new_password = request.form.get("new_password")
    
    update_data = {"role": new_role}
    if new_password: # Only update password if a new one was typed
        update_data["password_hash"] = generate_password_hash(new_password)
        
    db["users"].update(username, update_data)
    
    # Swap back to standard readonly row
    updated_user = db["users"].get(username)
    return render_user_row(updated_user)


@app.route("/admin/cancel_edit/<username>", methods=["GET"])
def cancel_edit(username):
    """Cancels inline editing by restoring the standard readonly row."""
    if session.get("role") != "admin": return "Forbidden", 403
    
    db = Database("users.db")
    try:
        user = db["users"].get(username)
        return render_user_row(user)
    except Exception:
        return ""

if __name__ == "__main__":
    app.run(debug=True)
