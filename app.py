from flask import Flask, render_template
from flask_mysqldb import MySQL
import yaml

app = Flask(__name__)

#Configure db
db = yaml.safe_load(open('static/db.yaml'))
app.config['MYSQL_HOST'] = db['mysql_host']
app.config['MYSQL_USER'] = db['mysql_user']
app.config['MYSQL_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DB'] = db['mysql_db']

mysql=MySQL(app)

@app.route('/')

def index():
    cur = mysql.connection.cursor()
    #cur.execute("INSERT INTO footballer(name, lastName) VALUES('Marcin','Najman')")
    mysql.connection.commit()
    cur.close()
    return render_template("index.html")

    

#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(debug=True)
    