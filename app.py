from flask import Flask, url_for, render_template, request, redirect, flash, session
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

app.config['SECRET_KEY']="Arek"

#main

@app.route('/')

def index():
    cur = mysql.connection.cursor()
    #cur.execute("INSERT INTO footballer(name, lastName) VALUES('Marcin','Najman')")
    mysql.connection.commit()
    cur.close()
    return render_template("index.html")

#footballers

@app.route('/add_footballer', methods=["POST","GET"])

def addft():
    if request.method == "POST":
        
        name=request.form['name']
        lastname=request.form['lastname']
        
        if name and lastname:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO footballer(name, lastName) VALUES(%s,%s)",(name,lastname))
            mysql.connection.commit()
            cur.close()
            flash("Pomyślnie dodano piłkarza","alert alert-success")
            return redirect(url_for("list_of_ft"))
        else:
            flash("Należy uzupełnić dane","alert alert-danger")
            return render_template("addfootballer.html", name=name, lastname=lastname)   
    else:    
        return render_template("addfootballer.html")

@app.route('/list_of_footballers')

def list_of_ft():
    cur = mysql.connection.cursor()
    #cur.execute("INSERT INTO footballer(name, lastName) VALUES('Marcin','Najman')")
    mysql.connection.commit()
    cur.close()
    return render_template("list_of_ft.html")

@app.route('/add_footballer', methods=["POST","GET"])

#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404



if __name__ == "__main__":
    app.run(debug=True)
    