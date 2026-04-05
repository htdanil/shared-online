import random
from flask import Flask, request

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <h2>Infinite Random Numbers</h2>
    <div hx-get="/numbers?page=1" hx-trigger="load" hx-swap="outerHTML"></div>
    """

@app.route("/numbers")
def numbers():
    page = request.args.get("page", 1, type=int)
    
    per_page = 20
    max_items = 150
    current_count = (page - 1) * per_page
    
    # Figure out how many items to generate for this specific page 
    items_this_page = min(per_page, max_items - current_count)
    
    html = ""
    has_next = False
    
    for i in range(items_this_page):
        num = random.randint(100, 999)
        
        is_last = (i == items_this_page - 1)
        has_next = (current_count + items_this_page) < max_items
        
        # If it's the last item and we haven't hit 150 yet, attach HTMX triggers
        if is_last and has_next:
            html += f'<p hx-get="/numbers?page={page+1}" hx-trigger="revealed" hx-swap="afterend">{num}</p>'
        else:
            html += f'<p>{num}</p>'
            
    # CRITICAL FIX: Append the "Done" message to the very last batch of HTML!
    if not has_next:
        html += f"<br><b>Done! {max_items} numbers generated.</b>"
            
    return html

if __name__ == "__main__":
    app.run(debug=True)
