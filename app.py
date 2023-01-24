from flask import Flask, url_for, render_template, request, redirect, flash, session
from psycopg2 import sql
import mysql.connector
import yaml
from datetime import date, datetime, timedelta


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
    cur.execute("SELECT id, name FROM position")
    positions_list=cur.fetchall()
    cur.close()
    
    if request.method == "POST":
        
        name=request.form['name']
        lastname=request.form['lastname']
        actual_team=request.form.get('actual_team')
        dateFrom_team=request.form.get('dateFrom_team')
        positions=request.form.getlist('positions[]')
        positions_date=request.form.get('date_position')
        
        if name and lastname:
            cur = mysql.cursor()
            try:
                cur.execute("INSERT INTO footballer(name, lastName) VALUES(%s,%s)",(name,lastname))
                last_ft_id=cur.lastrowid
                if actual_team and dateFrom_team:
                    cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,actual_team,dateFrom_team))
                    if request.form.getlist('historydateFrom_team[]') and request.form.getlist('history_team[]'):
                        if len(request.form.getlist('historydateFrom_team[]')) == len(request.form.getlist('history_team[]')):
                            history_teams=request.form.getlist('history_team[]')
                            teams_dates=request.form.getlist('historydateFrom_team[]')
                            for i in range(0, len(request.form.getlist('historydateFrom_team[]'))):
                                cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,history_teams[i], teams_dates[i]))
                        else:
                            flash("liczba klubów jest różna od liczby dat","alert alert-danger")
                            return render_template("addfootballer.html", teams=teams_list, positions=positions_list) 
                if positions and positions_date:
                    for i in range(0, len(request.form.getlist('positions[]'))):
                        cur.execute("INSERT INTO positionhistory(id_footballer, id_position, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,positions[i],positions_date))
                mysql.commit()
                cur.close()
                flash("Pomyślnie dodano piłkarza","alert alert-success")
                return redirect(url_for("list_of_ft"))
            except Exception:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych","alert alert-danger")
                return render_template("addfootballer.html", teams=teams_list, positions=positions_list)  
        else:
            flash("Należy uzupełnić dane","alert alert-danger")
            return render_template("addfootballer.html", teams=teams_list, positions=positions_list)   
    else:    
        return render_template("addfootballer.html", teams=teams_list, positions=positions_list)

@app.route('/list_of_footballers')

def list_of_ft():
    headings = ['Lp.', "Imie i Nazwisko", "Pozycja", "Drużyna"]
    cur = mysql.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM actions")
    action_list = cur.fetchall()
    headings += list(map(lambda x: x['name'], action_list)) + ['Historia']+['Edycja']
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
                    AND dateEnd is NULL
                    ), 'Brak pozycji') as position,
                COALESCE(t.name, 'Brak druzyny') as team 
                FROM footballer as f 
                LEFT JOIN clubhistory as ch ON f.id = ch.id_footballer AND dateFROM is not NULL
                LEFT JOIN teams as t ON ch.id_team = t.id
                WHERE dateFrom = (SELECT MAX(dateFROM) FROM clubhistory WHERE id_footballer = f.id ) OR dateFROM IS NULL
                GROUP BY f.id ORDER BY f.id""")

    table_content = cur.fetchall()
    mysql.commit()
    cur.close()


    return render_template("list_of_ft.html", headings=headings, row=table_content, actions=action_list_values,)


@app.route('/footballer_history/<footballer_id>')

def footballerHistory(footballer_id):
    cur = mysql.cursor(dictionary=True)
    cur.execute("SELECT CONCAT(f.name, ' ', f.lastName) as last_name FROM footballer as f WHERE f.id = %s", (footballer_id,))    
    name = cur.fetchall()
    if not name:
        cur.close()
        flash("Wybrany piłkarz nie istnieje","alert alert-danger")
        return redirect(url_for("list_of_ft"))

    cur.execute("""
                SELECT t.name AS club_name, dateFrom
                FROM footballer as f 
                LEFT JOIN clubhistory AS ch ON f.id = ch.id_footballer
                LEFT JOIN teams AS t ON t.id = ch.id_team
                WHERE f.id = %s
                GROUP BY dateFrom ORDER BY dateFrom ASC""", (footballer_id,))    
    club_history_content = cur.fetchall()

    cur.execute("""
                SELECT CONCAT('Dodanie pozycji: ', p.name) as position, dateFrom as date
                FROM footballer as f 
                LEFT JOIN positionhistory AS ph ON f.id = ph.id_footballer
                LEFT JOIN position AS p ON p.id = ph.id_position
                WHERE f.id = %s
                UNION ALL
                SELECT CONCAT('Usunięcie pozycji: ', p.name) as position, dateEnd as date
                FROM footballer as f 
                LEFT JOIN positionhistory AS ph ON f.id = ph.id_footballer
                LEFT JOIN position AS p ON p.id = ph.id_position
                WHERE f.id = %s AND dateEnd is not NULL
                GROUP BY ph.id_position, ph.id_footballer, date ORDER BY date DESC
                """, (footballer_id,footballer_id))    
    position_history_content = cur.fetchall()


    club_history_content2 = club_history_content + [{'dateFrom':date.today()}]
    club_history_content3 = []
    
    for i in range(len(club_history_content2)-1):
        cur.execute("""
                SELECT ALL CONCAT(t1.name,' : ', t2.name) as game, date, COALESCE(
                    (SELECT ALL GROUP_CONCAT(CONCAT(a.name, ': ', am.time,'min') ORDER BY am.time SEPARATOR ', ') 
                    FROM actionsinmatch as am 
                    JOIN actions as a ON a.id = am.id_action
                    WHERE am.id_match = g.id AND am.id_footballer = %s
                    ), 'Brak akcji') as akcje
                FROM games as g
                LEFT JOIN teams as t1 ON t1.id = g.id_home
                LEFT JOIN teams as t2 ON t2.id = g.id_away
                WHERE (t1.name = %s OR t2.name = %s) AND date BETWEEN %s AND %s
                """, (footballer_id,club_history_content2[i]['club_name'],club_history_content2[i]['club_name'],club_history_content2[i]['dateFrom'],club_history_content2[i+1]['dateFrom']))  
        club_history_content3 += cur.fetchall()

    return render_template("footballer_history.html", footballer_name=name[0], clubs=club_history_content, positions=position_history_content, matches=club_history_content3)



@app.route('/update_footballer/<footballer_id>', methods=["POST","GET"])

def update_ft(footballer_id=None):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT f.id, f.name, f.lastName, MAX(ch.dateFrom) AS clubDate, MAX(ph.dateFrom) AS positionDate from footballer f
                LEFT JOIN clubhistory ch on f.id=ch.id_footballer
                LEFT JOIN positionhistory ph on f.id=ph.id_footballer
                WHERE f.id=%s AND ph.dateEnd IS NULL
                """,(footballer_id,))
    footballer=cur.fetchone()
    print(footballer)
    if not footballer['id']:
        cur.close()
        flash("Wybrany piłkarz nie istnieje","alert alert-danger")
        return redirect(url_for("list_of_ft"))
    if footballer['clubDate']:
        footballer['clubDate']=footballer['clubDate']+timedelta(days=1)
    if footballer['positionDate']:
        footballer['positionDate']=footballer['positionDate']+timedelta(days=1)
    cur.execute("SELECT id, name FROM teams")
    teams_list=cur.fetchall()
    cur.execute("SELECT id, name FROM position")
    positions_list=cur.fetchall()
    cur.close()
    
    if request.method == "POST":
        cur = mysql.cursor()
        try:
            if request.form.get('name') and request.form.get('lastname'):
                cur.execute("UPDATE footballer SET name=%s, lastName=%s WHERE id=%s",(request.form.get('name'),request.form.get('lastname'), footballer_id))
                if request.form.get('actual_team') and request.form.get('dateFrom_team'):
                   cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(footballer_id, request.form.get('actual_team'),request.form.get('dateFrom_team')))
                if request.form.getlist('positions[]') and request.form.get('date_position'):
                   cur.execute("UPDATE positionhistory SET dateEnd=%s WHERE id_footballer=%s AND dateEnd IS NULL",(request.form.get('date_position'), footballer_id))
                   for i in range(0, len(request.form.getlist('positions[]'))):
                        cur.execute("INSERT INTO positionhistory(id_footballer, id_position, dateFrom) VALUES(%s,%s,%s)",(footballer_id,request.form.getlist('positions[]')[i],request.form.get('date_position'))) 
                cur.close()
                mysql.commit()
                flash("Pomyślnie zaktualizowano piłkarza","alert alert-success")
                return redirect(url_for("list_of_ft"))
            else:
                cur.close()
                flash("Należy uzupełnić dane","alert alert-danger")
                return redirect(url_for("update_ft",footballer_id=footballer_id))
        except Exception:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych","alert alert-danger")
                return redirect(url_for("list_of_ft"))
    
    return render_template("update_footballer.html",teams=teams_list, positions=positions_list, footballer=footballer)

#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404



if __name__ == "__main__":
    app.run(debug=True)
    