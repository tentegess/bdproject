from flask import Flask, render_template

app = Flask(__name__)
app.config['SECRET_KEY'] = "Arek"


@app.route('/')

def index():
    return render_template("index.html")

#invalid URL
@app.errorhandler(404)

#lol2
def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)