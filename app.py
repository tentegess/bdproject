from flask import Flask, url_for, render_template, request, redirect, flash, session
import mysql.connector
import yaml

app = Flask(__name__)

#Configure db
db = yaml.safe_load(open('static/db.yaml'))

mysql = mysql.connector.connect(
    host = db['mysql_host'],
    user = db['mysql_user'],
    password = db['mysql_password'],
    database = db['mysql_db']
)

app.config['SECRET_KEY']="Arek"

#main

@app.route('/')

def index():
    cur = mysql.cursor()
    #cur.execute("INSERT INTO footballer(name, lastName) VALUES('Marcin','Najman')")
    mysql.commit()
    cur.close()
    return render_template("index.html")

#footballers

@app.route('/add_footballer', methods=["POST","GET"])

def addft():
    if request.method == "POST":
        
        name=request.form['name']
        lastname=request.form['lastname']
        
        if name and lastname:
            cur = mysql.cursor()
            cur.execute("INSERT INTO footballer(name, lastName) VALUES(%s,%s)",(name,lastname))
            mysql.commit()
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
    headings = ('Lp.', "Imie i Nazwisko", "Pozycja", "Drużyna", "Lista akcji", "Historia")
    cur = mysql.cursor(dictionary=True)
    cur.execute("""
                SELECT CONCAT(f.name, ' ', f.lastName) AS nameLastname, 
                GROUP_CONCAT(p.name SEPARATOR ', ') as position
                FROM footballer as f 
                LEFT JOIN positionhistory as ph ON f.id = ph.id_footballer
                LEFT JOIN position as p ON p.id = ph.id_position
                WHERE ph.dateEND is NULL""")
    test = cur.fetchall()
    mysql.commit()
    cur.close()

    return render_template("list_of_ft.html", headings=headings, row=test)

@app.route('/add_footballer', methods=["POST","GET"])

#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404



if __name__ == "__main__":
    app.run(debug=True)
    