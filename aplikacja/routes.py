from aplikacja import app

@app.route("/")
def index():
    return "<h1>Witaj w księgarni e-booków!</h1>"
