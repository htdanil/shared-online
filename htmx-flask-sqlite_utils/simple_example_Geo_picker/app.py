from flask import Flask, request, send_from_directory
from sqlite_utils import Database

# Initialize Flask and connect to SQLite
app = Flask(__name__, static_folder="static")

def get_db():
    """Create a fresh database connection."""
    return Database("geo.db")

def seed():
    """Populate the database with simple test data."""
    db = get_db()
    # Replace=True ensures we don't get duplicates if we run this many times
    db["continents"].insert_all([{"id": 1, "name": "Asia"}, {"id": 2, "name": "Europe"}], pk="id", replace=True)
    db["countries"].insert_all([
        {"id": 1, "name": "Nepal", "continent_id": 1},
        {"id": 2, "name": "France", "continent_id": 2}
    ], pk="id", replace=True)
    db["cities"].insert_all([
        {"id": 1, "name": "Kathmandu", "country_id": 1},
        {"id": 2, "name": "Paris", "country_id": 2}
    ], pk="id", replace=True)

@app.route("/")
def index():
    """Serve the static/index.html file when someone visits the homepage."""
    return send_from_directory("static", "index.html")

@app.route("/continents")
def get_continents():
    """Fetch all continents and return them as an HTML <select> dropdown."""
    db = get_db()
    # List comprehension to build <option> tags for each row in the continents table
    opts = "".join([f'<option value="{r["id"]}">{r["name"]}</option>' for r in db["continents"].rows])
    
    # hx-get: Tells HTMX to call /countries when the user changes the selection
    # hx-target: Tells HTMX to put the result inside the element with id="country-div"
    return f'''
        <select name="continent_id" hx-get="/countries" hx-target="#country-div">
            <option value="">Select Continent</option>
            {opts}
        </select>
    '''

@app.route("/countries")
def get_countries():
    """Fetch countries based on the selected continent_id."""
    db = get_db()
    continent_id = request.args.get("continent_id")
    
    # Query the database for countries where continent_id matches
    rows = list(db["countries"].rows_where("continent_id = ?", [continent_id])) if continent_id else []
    opts = "".join([f'<option value="{r["id"]}">{r["name"]}</option>' for r in rows])
    
    # 1. Main response: The HTML for the Country dropdown
    html = f'''
        <select name="country_id" hx-get="/cities" hx-target="#city-div">
            <option value="">Select Country</option>
            {opts}
        </select>
    '''
    
    # 2. Reset logic (OOB Swaps):
    # HTMX "Out-of-Band" (OOB) swaps allow one request to update multiple parts of the page.
    # We use this to reset the City dropdown and Result area when the Continent changes.
    html += '<div id="city-div" hx-swap-oob="innerHTML">Select a country first</div>'
    html += '<div id="result" hx-swap-oob="innerHTML"></div>'
    
    return html

@app.route("/cities")
def get_cities():
    """Fetch cities based on the selected country_id."""
    db = get_db()
    country_id = request.args.get("country_id")
    
    rows = list(db["cities"].rows_where("country_id = ?", [country_id])) if country_id else []
    opts = "".join([f'<option value="{r["id"]}">{r["name"]}</option>' for r in rows])
    
    # Return the City dropdown
    html = f'''
        <select name="city_id" hx-get="/result" hx-target="#result">
            <option value="">Select City</option>
            {opts}
        </select>
    '''
    
    # Reset the Result area if the user picks a different country
    html += '<div id="result" hx-swap-oob="innerHTML"></div>'
    return html

@app.route("/result")
def get_result():
    """Look up the final city name and return a simple text result."""
    db = get_db()
    city_id = request.args.get("city_id")
    
    if not city_id: 
        return ""
        
    city = db["cities"].get(city_id)
    return f"Selected: {city['name']}"

if __name__ == "__main__":
    seed()  # Setup database on startup
    app.run(debug=True)
