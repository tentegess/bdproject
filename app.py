from flask import Flask, url_for, render_template, request, redirect, flash, session
from psycopg2 import sql
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
    cur = mysql.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM teams")
    teams_list=cur.fetchall()
    cur.close()
    
    if request.method == "POST":
        
        name=request.form['name']
        lastname=request.form['lastname']
        
        if name and lastname:
            cur = mysql.cursor()
            try:
                cur.execute("INSERT INTO footballer(name, lastName) VALUES(%s,%s)",(name,lastname))
                if request.form['actual_team'] and request.form['dateFrom_team']:
                    last_ft_id=cur.lastrowid
                    actual_team=request.form['actual_team']
                    dateFrom_team=request.form['dateFrom_team']
                    cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,actual_team,dateFrom_team))
                mysql.commit()
                cur.close()
                flash("Pomyślnie dodano piłkarza","alert alert-success")
                return redirect(url_for("list_of_ft"))
            except Exception:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych","alert alert-danger")
                return render_template("addfootballer.html", teams=teams_list)  
        else:
            flash("Należy uzupełnić dane","alert alert-danger")
            return render_template("addfootballer.html", teams=teams_list)   
    else:    
        return render_template("addfootballer.html", teams=teams_list)

@app.route('/list_of_footballers')

def list_of_ft():
    headings = ['Lp.', "Imie i Nazwisko", "Pozycja", "Drużyna"]
    cur = mysql.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM actions")
    action_list = cur.fetchall()
    headings += list(map(lambda x: x['name'], action_list))
    action_list_values = []

    for action in action_list:
        cur.execute("""
                    SELECT COUNT(a.name) as counted, f.id 
                    FROM footballer as f
                    LEFT JOIN actionsinmatch as am ON am.id_footballer = f.id
                    LEFT JOIN actions as a  ON a.id = am.id_action AND a.name = %s
                    GROUP BY f.id ORDER BY f.id""", (action['name'],))    
        action_list_values.append(cur.fetchall())


    cur.execute("""
                SELECT CONCAT(f.name, ' ', f.lastName) AS nameLastname, f.id,
                COALESCE(
                    (SELECT GROUP_CONCAT(p.name SEPARATOR ', ') 
                    FROM positionhistory as ph 
                    JOIN position as p ON p.id = ph.id_position 
                    WHERE ph.id_footballer = f.id
                    ), 'Brak pozycji') as position,
                COALESCE(t.name, 'Brak druzyny') as team 
                FROM footballer as f 
                LEFT JOIN clubhistory as ch ON f.id = ch.id_footballer AND dateFROM is not NULL
                LEFT JOIN teams as t ON ch.id_team = t.id
                GROUP BY f.id ORDER BY f.id""")

    table_content = cur.fetchall()
    mysql.commit()
    cur.close()


    return render_template("list_of_ft.html", headings=headings, row=table_content, actions=action_list_values,)

@app.route('/add_footballer', methods=["POST","GET"])

#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404



if __name__ == "__main__":
    app.run(debug=True)
    