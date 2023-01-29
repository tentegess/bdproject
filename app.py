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
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT COUNT(name) AS footballers, (SELECT COUNT(name) FROM teams) AS teams,
                (SELECT COUNT(name) FROM league) AS league, (SELECT COUNT(id) FROM games) AS games  FROM footballer""")
    counts=cur.fetchone()
    cur.close()
    return render_template("index.html", counts=counts)

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
        
        name=request.form['name'].strip()
        lastname=request.form['lastname'].strip()
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
                    if actual_team=='0':
                        actual_team=None 
                    cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,actual_team,dateFrom_team))
                    if request.form.getlist('historydateFrom_team[]') and request.form.getlist('history_team[]'):
                        if len(request.form.getlist('historydateFrom_team[]')) == len(request.form.getlist('history_team[]')):
                            history_teams=request.form.getlist('history_team[]')
                            teams_dates=request.form.getlist('historydateFrom_team[]')
                            for i in range(0, len(request.form.getlist('historydateFrom_team[]'))):
                                if history_teams[i]=='0':
                                   history_teams[i]=None 
                                cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,history_teams[i], teams_dates[i]))
                        else:
                            flash("liczba klubów jest różna od liczby dat","alert alert-danger alert-dismissible")
                            return render_template("addfootballer.html", teams=teams_list, positions=positions_list) 
                if positions and positions_date:
                    for i in range(0, len(request.form.getlist('positions[]'))):
                        cur.execute("INSERT INTO positionhistory(id_footballer, id_position, dateFrom) VALUES(%s,%s,%s)",(last_ft_id,positions[i],positions_date))
                mysql.commit()
                cur.close()
                flash("Pomyślnie dodano piłkarza","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_ft"))
            except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return render_template("addfootballer.html", teams=teams_list, positions=positions_list)  
        else:
            flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
            return render_template("addfootballer.html", teams=teams_list, positions=positions_list)   
    else:    
        return render_template("addfootballer.html", teams=teams_list, positions=positions_list)

@app.route('/list_of_footballers', methods=["POST","GET"])

def list_of_ft():
    headings = ['Lp.', "Imie i Nazwisko", "Pozycja", "Drużyna"]
    cur = mysql.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM actions")
    action_list = cur.fetchall()
    headings += list(map(lambda x: x['name'], action_list)) + ['Historia']+['Edycja']
    action_list_values = []

    cur.execute("""SELECT DISTINCT YEAR(date) as year FROM games ORDER BY date DESC;""")
    seasons = cur.fetchall()

    
    if request.method == "POST":
        year = request.form.get('season_select')
    else:
        year = seasons[0]['year']

    print(year)

    for action in action_list:
        cur.execute("""
                    SELECT COUNT(a.name) as counted, f.id 
                    FROM footballer as f
                    LEFT JOIN actionsinmatch as am ON am.id_footballer = f.id 
                    LEFT JOIN games as g ON g.id = am.id_match 
                    LEFT JOIN actions as a  ON a.id = am.id_action AND a.name = %s AND YEAR(g.date) = %s
                    
                    GROUP BY f.id ORDER BY f.id""", (action['name'],year))    
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
                COALESCE(t.name, 'Brak drużyny') as team 
                FROM footballer as f 
                LEFT JOIN clubhistory as ch ON f.id = ch.id_footballer AND dateFROM is not NULL
                LEFT JOIN teams as t ON ch.id_team = t.id
                LEFT JOIN games as g ON g.id_home = t.id AND YEAR(g.date) = %s
                WHERE dateFrom = (SELECT MAX(dateFROM) FROM clubhistory WHERE id_footballer = f.id ) OR dateFROM IS NULL
                GROUP BY f.id ORDER BY f.id""", (year,)) 

    table_content = cur.fetchall()
    mysql.commit()
    cur.close()


    return render_template("list_of_ft.html", headings=headings, row=table_content, actions=action_list_values, seasons=seasons, year=int(year))


@app.route('/footballer_history/<footballer_id>')

def footballerHistory(footballer_id):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""
                SELECT CONCAT(f.name, ' ', f.lastName) AS last_name, f.id,
                CONCAT('Pozycja: ', COALESCE(
                    (SELECT GROUP_CONCAT(p.name SEPARATOR ', ') 
                    FROM positionhistory as ph 
                    JOIN position as p ON p.id = ph.id_position 
                    WHERE ph.id_footballer = f.id
                    AND dateEnd is NULL
                    ), 'Brak pozycji')) as position,
                CONCAT('Drużyna: ',COALESCE(t.name, 'Brak drużyny')) as team 
                FROM footballer as f 
                LEFT JOIN clubhistory as ch ON f.id = ch.id_footballer AND dateFROM is not NULL
                LEFT JOIN teams as t ON ch.id_team = t.id
                WHERE (dateFrom = (SELECT MAX(dateFROM) FROM clubhistory WHERE id_footballer = f.id ) OR dateFROM IS NULL)
                AND f.id = %s""", (footballer_id,))
        
    name = cur.fetchone()

    if not name:
        cur.close()
        flash("Wybrany piłkarz nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_ft"))
    
    cur.execute("SELECT id, name FROM actions")
    action_list = cur.fetchall()
    actions_names= list(map(lambda x: x['name'], action_list))
    action_values = []

    for action in action_list:
        cur.execute("""
                    SELECT COUNT(a.name) as counted 
                    FROM footballer as f
                    LEFT JOIN actionsinmatch as am ON am.id_footballer = f.id
                    LEFT JOIN actions as a  ON a.id = am.id_action AND a.name = %s
                    WHERE f.id=%s""", (action['name'],footballer_id))    
        action_values.append(cur.fetchone())

    actions=dict(zip(actions_names, list(map(lambda x: x['counted'], action_values))))
    
    print(actions)

    cur.execute("""
                SELECT COALESCE(t.name,'Brak drużyny') AS club_name, COALESCE(dateFrom,'') as dateFrom
                FROM footballer as f 
                LEFT JOIN clubhistory AS ch ON f.id = ch.id_footballer
                LEFT JOIN teams AS t ON t.id = ch.id_team
                WHERE f.id = %s
                GROUP BY dateFrom ORDER BY dateFrom DESC""", (footballer_id,))    
    club_history_content = cur.fetchall()

    cur.execute("""
                SELECT COALESCE(CONCAT('Dodanie pozycji: ',GROUP_CONCAT(p.name SEPARATOR ', ')),'Brak pozycji') as position,  COALESCE(dateFrom,'') as date
                FROM footballer as f 
                LEFT JOIN positionhistory AS ph ON f.id = ph.id_footballer
                LEFT JOIN position AS p ON p.id = ph.id_position
                WHERE f.id = %s 
                GROUP BY date
                UNION ALL
                SELECT CONCAT('Usunięcie pozycji: ',GROUP_CONCAT(p.name SEPARATOR ', ')) as position, dateEnd as date
                FROM footballer as f 
                LEFT JOIN positionhistory AS ph ON f.id = ph.id_footballer
                LEFT JOIN position AS p ON p.id = ph.id_position
                WHERE f.id = %s AND dateEnd is not NULL
                GROUP BY date ORDER BY date DESC
                """, (footballer_id,footballer_id))    
    position_history_content = cur.fetchall()

    club_history_content2 = club_history_content[::-1] + [{'dateFrom':date(9999,12,31)}]
    games_history_content = []

    for i in range(len(club_history_content2)-1):
        cur.execute("""
                SELECT ALL CONCAT(t1.name,' : ', t2.name) as game, date, COALESCE(
                    (SELECT ALL GROUP_CONCAT(CONCAT(a.name, ': ', am.time,'min') ORDER BY am.time SEPARATOR '</br>') 
                    FROM actionsinmatch as am 
                    JOIN actions as a ON a.id = am.id_action
                    WHERE am.id_match = g.id AND am.id_footballer = %s
                    ), 'Brak akcji') as akcje
                FROM games as g
                LEFT JOIN teams as t1 ON t1.id = g.id_home
                LEFT JOIN teams as t2 ON t2.id = g.id_away
                WHERE (t1.name = %s OR t2.name = %s) AND date BETWEEN %s AND %s
                ORDER BY g.date DESC
                """, (footballer_id,club_history_content2[i]['club_name'],club_history_content2[i]['club_name'],club_history_content2[i]['dateFrom'],club_history_content2[i+1]['dateFrom']))  
        games_history_content += cur.fetchall()

    return render_template("footballer_history.html", footballer=name, clubs=club_history_content, positions=position_history_content, matches=games_history_content, actions=actions)



@app.route('/update_footballer/<footballer_id>', methods=["POST","GET"])

def update_ft(footballer_id=None):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT f.id, f.name, f.lastName, MAX(ch.dateFrom) AS clubDate, MAX(ph.dateFrom) AS positionDate from footballer f
                LEFT JOIN clubhistory ch on f.id=ch.id_footballer
                LEFT JOIN positionhistory ph on f.id=ph.id_footballer
                WHERE f.id=%s AND ph.dateEnd IS NULL
                """,(footballer_id,))
    footballer=cur.fetchone()
    if not footballer['id']:
        cur.close()
        flash("Wybrany piłkarz nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_ft"))
    cur.execute("""SELECT id_position FROM positionhistory
                WHERE id_footballer=%s AND dateEND is NULL
                """,(footballer_id,))
    current_positions=cur.fetchall()

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
            if request.form.get('name').strip() and request.form.get('lastname').strip():
                cur.execute("UPDATE footballer SET name=%s, lastName=%s WHERE id=%s",(request.form.get('name').strip(),request.form.get('lastname').strip(), footballer_id))
                
                if request.form.get('noteam') and request.form.get('dateFrom_team'):
                    cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(footballer_id, None,request.form.get('dateFrom_team')))
                elif request.form.get('actual_team') and request.form.get('dateFrom_team'):
                   cur.execute("INSERT INTO clubhistory(id_footballer, id_team, dateFrom) VALUES(%s,%s,%s)",(footballer_id, request.form.get('actual_team'),request.form.get('dateFrom_team')))
                
                if request.form.get('noposition') and request.form.get('date_position'):
                    cur.execute("UPDATE positionhistory SET dateEnd=%s WHERE id_footballer=%s AND dateEnd IS NULL",(request.form.get('date_position'), footballer_id))
                    cur.execute("INSERT INTO positionhistory(id_footballer, id_position, dateFrom) VALUES(%s,%s,%s)",(footballer_id,None,request.form.get('date_position')))     
                elif request.form.getlist('positions[]') and request.form.get('date_position'):
                   cur.execute("UPDATE positionhistory SET dateEnd=%s WHERE id_footballer=%s AND dateEnd IS NULL",(request.form.get('date_position'), footballer_id))
                   for i in range(0, len(request.form.getlist('positions[]'))):
                        cur.execute("INSERT INTO positionhistory(id_footballer, id_position, dateFrom) VALUES(%s,%s,%s)",(footballer_id,request.form.getlist('positions[]')[i],request.form.get('date_position'))) 
                
                cur.close()
                mysql.commit()
                flash("Pomyślnie zaktualizowano piłkarza","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_ft"))
            else:
                cur.close()
                flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
                return redirect(url_for("update_ft",footballer_id=footballer_id))
        except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return redirect(url_for("list_of_ft"))
    
    return render_template("update_footballer.html",teams=teams_list, positions=positions_list, footballer=footballer, current_positions=current_positions)


@app.route('/remove_ft/<footballer_id>')

def rmft(footballer_id):
    cur = mysql.cursor()
    try:
        cur.execute("DELETE FROM footballer WHERE id=%s",(footballer_id,))
        mysql.commit()
        cur.close()
        flash("Pomyślnie usunięto piłkarza","alert alert-success alert-dismissible")
        return redirect(url_for("list_of_ft"))
    except Exception as e:
        mysql.rollback()
        cur.close()
        flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_ft"))
    
#clubs

@app.route('/list_of_clubs', methods=["POST","GET"])

def list_of_clubs():
    headings = ['Lp.', "Drużyna", "Liga", "Rozegrane mecze", "Wygane", "Remisy", "Przegrane", "Punkty ligowe", "Historia", "Edycja"]
    cur = mysql.cursor(dictionary=True)

    
    cur.execute("""SELECT DISTINCT YEAR(date) as year FROM games ORDER BY date DESC;""")
    seasons = cur.fetchall()

    if request.method == "POST":
        year = request.form.get('season_select')
    else:
        year = seasons[0]['year']

    cur.execute("""
                SELECT t.id as id, t.name as team, l.name as league, 
                COUNT(CASE WHEN home_goals > away_goals AND t.id=g.id_home THEN 1 WHEN away_goals > home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as wins,
                COUNT(CASE WHEN home_goals = away_goals AND (t.id=g.id_home OR t.id=g.id_away) THEN 1 END) as draws,
                COUNT(CASE WHEN home_goals < away_goals AND t.id=g.id_home THEN 1 WHEN away_goals < home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as loses,
                COUNT((SELECT SUM(CASE WHEN g2.id_away=t.id OR g2.id_home=t.id THEN 1 ELSE NULL END) FROM games AS g2
                WHERE (g2.id_away=t.id OR g2.id_home=t.id) AND g2.id IS NOT NULL AND YEAR(g.date) = %s)) AS games_played,
                SUM(CASE WHEN home_goals > away_goals AND t.id=g.id_home THEN 3 WHEN away_goals > home_goals AND t.id=g.id_away THEN 3  
                WHEN home_goals = away_goals AND (t.id=g.id_home OR t.id=g.id_away) THEN 1 ELSE 0 END) as league_points
                FROM teams as t
                LEFT JOIN league as l ON l.id = t.id_league
                LEFT JOIN (SELECT g.date, g.id_home, g.id_away, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team=g.id_home THEN 1 END) as home_goals, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team =g.id_away THEN 1 END) as away_goals
                    FROM games AS g
                    LEFT JOIN actionsinmatch as am ON g.id = am.id_match
                    LEFT JOIN actions as a ON a.id = am.id_action
                    LEFT JOIN footballer as f ON am.id_footballer = f.id 
                    LEFT JOIN clubhistory as ch ON (ch.id_team = g.id_away OR ch.id_team = g.id_home) AND 
                    f.id = ch.id_footballer AND (SELECT MAX(ch2.dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer=f.id AND ch2.dateFrom<= g.date) = ch.dateFrom
                    WHERE YEAR(g.date) = %s
                    GROUP BY g.id) as g ON g.id_home = t.id OR g.id_away = t.id
                GROUP BY t.id;""",(year,year))
    table_content = cur.fetchall()

    return render_template("list_of_clubs.html", headings=headings, row=table_content, seasons=seasons, year=int(year))


@app.route('/add_club', methods=["POST","GET"])

def addclub():
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT id, name FROM league""")
    leagues=cur.fetchall()
    cur.close()
    if request.method == "POST":
        name=request.form.get('name').strip()
        league=request.form.get('league').strip()
        if name and league:
            cur = mysql.cursor()
            cur.execute("""SELECT COUNT(name) as counter FROM teams WHERE name=%s""",(name,))
            counter=cur.fetchone()
            print(counter)
            if counter[0]>0:
                cur.close()
                flash("Podana drużyna istnieje w bazie","alert alert-danger alert-dismissible")
                return render_template("addclub.html", leagues=leagues)
            try:
                cur.execute("INSERT INTO teams(name, id_league) VALUES(%s,%s)",(name,league))
                mysql.commit()
                cur.close()
                flash("Pomyślnie dodano drużynę","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_clubs"))
            except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return render_template("addclub.html", leagues=leagues)
        else:
            flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
            return redirect(url_for("addclub"))
    return render_template("addclub.html", leagues=leagues)

@app.route('/remove_team/<club_id>')

def rmteam(club_id):
    cur = mysql.cursor()
    try:
        cur.execute("DELETE FROM teams WHERE id=%s",(club_id,))
        mysql.commit()
        cur.close()
        flash("Pomyślnie usunięto klub","alert alert-success alert-dismissible")
        return redirect(url_for("list_of_clubs"))
    except Exception as e:
        mysql.rollback()
        cur.close()
        flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_clubs"))


@app.route('/club_history/<club_id>')

def club_history(club_id):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT name FROM teams AS t WHERE t.id = %s""", (club_id,))
        
    name = cur.fetchone()
    print(name)
    if not name:
        cur.close()
        flash("Wybrana drużyna nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_clubs"))

    cur.execute("""
                SELECT CONCAT(f.name, ' ', f.lastName) AS last_name, CONCAT('</br>Pozycja: ', COALESCE(
                    (SELECT GROUP_CONCAT(p.name SEPARATOR ', ') 
                    FROM positionhistory as ph 
                    JOIN position as p ON p.id = ph.id_position 
                    WHERE ph.id_footballer = f.id
                    AND dateEnd is NULL
                    ), 'Brak pozycji')) as position
                FROM clubhistory AS ch
                LEFT JOIN teams as t ON t.id = ch.id_team
                LEFT JOIN footballer as f ON f.id = ch.id_footballer 
                WHERE t.id = %s AND dateFrom = (SELECT MAX(dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer =ch.id_footballer )""", (club_id,))
    actual_players = cur.fetchall()

    cur.execute("""
                SELECT CONCAT('Dołączył do klubu: </br>', GROUP_CONCAT(CONCAT(f.name, ' ', f.lastName) SEPARATOR '</br>')) AS last_name, ch.dateFrom as date
                FROM clubhistory AS ch
                LEFT JOIN teams as t ON t.id = ch.id_team
                LEFT JOIN footballer as f ON f.id = ch.id_footballer 
                WHERE t.id = %s
                GROUP BY ch.dateFrom
                UNION ALL
                SELECT CONCAT('Odszedł z klubu: </br>', GROUP_CONCAT(CONCAT(f.name, ' ', f.lastName) SEPARATOR '</br>')) AS last_name, ch2.dateFrom as date
                FROM clubhistory AS ch
                LEFT JOIN teams as t ON t.id = ch.id_team
                LEFT JOIN footballer as f ON f.id = ch.id_footballer 
                LEFT JOIN (SELECT id_footballer, dateFrom FROM clubhistory WHERE id_team != %s) AS ch2 ON ch2.id_footballer = ch.id_footballer AND ch2.dateFrom > ch.dateFrom
                WHERE t.id = %s AND ch2.dateFrom > ch.dateFrom
                GROUP BY ch2.dateFrom ORDER BY date DESC; """, (club_id,club_id,club_id))
    players_history = cur.fetchall()

    cur.execute("""
                SELECT CASE WHEN g.id_home = %s THEN t2.name WHEN g.id_away = %s THEN t1.name END AS games, g.date as date, 
                CASE WHEN g2.id_home = %s THEN CONCAT(home_goals,':',away_goals) ELSE CONCAT(away_goals,':',home_goals) END as test
                FROM games AS g
                LEFT JOIN teams as t1 ON t1.id = g.id_home 
                LEFT JOIN teams as t2 ON t2.id = g.id_away
                LEFT JOIN (SELECT g.date, g.id_home, g.id_away, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team=g.id_home THEN 1 END) as home_goals, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team =g.id_away THEN 1 END) as away_goals
                    FROM games AS g
                    LEFT JOIN actionsinmatch as am ON g.id = am.id_match
                    LEFT JOIN actions as a ON a.id = am.id_action
                    LEFT JOIN footballer as f ON am.id_footballer = f.id 
                    LEFT JOIN clubhistory as ch ON (ch.id_team = g.id_away OR ch.id_team = g.id_home) AND 
                    f.id = ch.id_footballer AND (SELECT MAX(ch2.dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer=f.id AND ch2.dateFrom<= g.date) = ch.dateFrom
                    GROUP BY g.id) as g2 ON (g2.id_home = %s  OR g2.id_away = %s) AND g.date = g2.date
                WHERE t1.id = %s OR t2.id = %s
                 ORDER BY g.date DESC;
                """, (club_id,club_id,club_id,club_id,club_id,club_id,club_id))
    games_history = cur.fetchall()

    cur.execute("""
            SELECT
            COUNT(CASE WHEN home_goals > away_goals AND t.id=g.id_home THEN 1 WHEN away_goals > home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as wins,
            COUNT(CASE WHEN home_goals = away_goals AND (t.id=g.id_home OR t.id=g.id_away) THEN 1 END) as draws,
            COUNT(CASE WHEN home_goals < away_goals AND t.id=g.id_home THEN 1 WHEN away_goals < home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as loses,
            COUNT((SELECT SUM(CASE WHEN g2.id_away=t.id OR g2.id_home=t.id THEN 1 ELSE NULL END) FROM games AS g2
            WHERE (g2.id_away=t.id OR g2.id_home=t.id) AND g2.id IS NOT NULL)) AS games_played
            FROM teams as t
            LEFT JOIN league as l ON l.id = t.id_league
            LEFT JOIN (SELECT g.date, g.id_home, g.id_away, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team=g.id_home THEN 1 END) as home_goals, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team =g.id_away THEN 1 END) as away_goals
                FROM games AS g
                LEFT JOIN actionsinmatch as am ON g.id = am.id_match
                LEFT JOIN actions as a ON a.id = am.id_action
                LEFT JOIN footballer as f ON am.id_footballer = f.id 
                LEFT JOIN clubhistory as ch ON (ch.id_team = g.id_away OR ch.id_team = g.id_home) AND 
                f.id = ch.id_footballer AND (SELECT MAX(ch2.dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer=f.id AND ch2.dateFrom<= g.date) = ch.dateFrom
                GROUP BY g.id) as g ON g.id_home = t.id OR g.id_away = t.id
            WHERE t.id = %s;""",(club_id,))
    team_stats = cur.fetchone()

    return render_template("club_history.html", team=name, actual_players=actual_players, players_history=players_history, games_history=games_history, team_stats=team_stats, number_of_players=len(actual_players))

@app.route('/edit_club/<club_id>', methods=["POST","GET"])

def edit_club(club_id, methods=["POST","GET"]):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT t.id, t.name as club, l.name as league FROM teams t
                INNER JOIN league l ON t.id_league=l.id WHERE t.id=%s""",(club_id,))
    club=cur.fetchone()
    if not club:
        cur.close()
        flash("Wybrana drużyna nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_clubs"))
    cur.close()
    
    if request.method == "POST":
        name=request.form.get('name').strip()
        if name:
            try:
                cur = mysql.cursor()
                cur.execute("""SELECT id, COUNT(name) as counter FROM teams WHERE name=%s""",(name,))
                counter=cur.fetchone()
                if counter[1]>0 and str(counter[0])!=club_id:
                    flash("Taka drużyna już istnieje","alert alert-danger alert-dismissible")
                    cur.close()
                    return redirect(url_for("list_of_clubs"))
                cur.execute("""UPDATE teams SET name=%s WHERE id=%s""",(name,club_id))
                cur.close()
                mysql.commit()
                flash("Pomyślnie zaktualizowano drużynę","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_clubs"))
            except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return redirect(url_for("list_of_clubs"))
        else:
            flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
            return redirect(url_for("edit_club", club_id=club_id))
            
    return render_template("edit_club.html", club=club)

#leagues

@app.route('/list_of_leagues', methods=["POST","GET"])

def list_of_leagues():
    headings = ['Lp.', "Liga", "Liczba drużyn", "Tabela", "Historia", "Edycja"]
    cur = mysql.cursor(dictionary=True)

    cur.execute("""
                SELECT l.name AS name, COUNT((SELECT SUM(CASE WHEN l.id = l2.id THEN 1 ELSE NULL END) FROM league as l2 INNER JOIN teams as t ON l2.id = t.id_league
                WHERE (l2.id = l.id) AND l2.id IS NOT NULL)) AS number_of_teams,
                l.id AS id
                FROM league as l
                LEFT JOIN teams as t ON l.id = t.id_league
                GROUP BY l.id;""")
    leagues = cur.fetchall()

    return render_template("list_of_leagues.html", headings=headings, row=leagues)


@app.route('/add_league', methods=["POST","GET"])

def addleague():
    if request.method == "POST":
        name=request.form.get('name').strip()
        if name:
            cur = mysql.cursor()
            cur.execute("""SELECT COUNT(name) as counter FROM league WHERE name=%s""",(name,))
            counter=cur.fetchone()
            if counter[0]>0:
                    cur.close()
                    flash("Taka liga już istnieje","alert alert-danger alert-dismissible")
                    return render_template("addleague.html")
            try:
                cur.execute("INSERT INTO league(name) VALUES(%s)",(name,))
                mysql.commit()
                cur.close()
                flash("Pomyślnie dodano ligę","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_leagues"))
            except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return render_template("addleague.html")
        else:
            flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
            return redirect(url_for("addleague"))
    
    return render_template("addleague.html")

@app.route('/remove_league/<league_id>')

def rmleague(league_id):
    cur = mysql.cursor()
    try:
        cur.execute("DELETE FROM league WHERE id=%s",(league_id,))
        mysql.commit()
        cur.close()
        flash("Pomyślnie usunięto ligę","alert alert-success alert-dismissible")
        return redirect(url_for("list_of_leagues"))
    except Exception as e:
        mysql.rollback()
        cur.close()
        flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_leagues"))

@app.route('/edit_league/<league_id>', methods=["POST","GET"])

def edit_league(league_id, methods=["POST","GET"]):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""SELECT id, name FROM league WHERE id=%s""",(league_id,))
    league=cur.fetchone()
    if not league:
        cur.close()
        flash("Wybrana liga nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_leagues"))
    cur.close()
    
    if request.method == "POST":
        name=request.form.get('name').strip()
        if name:
            try:
                cur = mysql.cursor()
                cur.execute("""SELECT id, COUNT(name) as counter FROM league WHERE name=%s""",(name,))
                counter=cur.fetchone()
                if counter[1]>0 and str(counter[0])!=league_id:
                    flash("Taka liga już istnieje","alert alert-danger alert-dismissible")
                    cur.close()
                    return redirect(url_for("list_of_leagues"))
                cur.execute("""UPDATE league SET name=%s WHERE id=%s""",(name,league_id))
                cur.close()
                mysql.commit()
                flash("Pomyślnie zaktualizowano ligę","alert alert-success alert-dismissible")
                return redirect(url_for("list_of_leagues"))
            except Exception as e:
                mysql.rollback()
                cur.close()
                flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
                return redirect(url_for("list_of_leagues"))
        else:
            flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
            return redirect(url_for("edit_league", league_id=league_id))
            
    return render_template("edit_league.html", league=league)

@app.route('/league_history/<league_id>')

def league_history(league_id):
    cur = mysql.cursor(dictionary=True)
    cur.execute("""
                SELECT l.name AS name, COUNT(*) AS number_of_teams, l.id AS id
                FROM league as l
                LEFT JOIN teams as t ON l.id = t.id_league
                WHERE l.id = %s GROUP BY l.id;""",(league_id,))
    league = cur.fetchone()

    if not league:
        cur.close()
        flash("Wybrana liga nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_leagues"))

    cur.execute("""
                SELECT CASE WHEN g.id_home = t1.id THEN CONCAT(t2.name, ' - ', t1.name) WHEN g.id_away = t2.id THEN CONCAT(t1.name, ' - ', t2.name) END AS games, g.date as date, 
                CASE WHEN g2.id_home = t1.id THEN CONCAT(home_goals,':',away_goals) ELSE CONCAT(away_goals,':',home_goals) END as test
                FROM games AS g
                LEFT JOIN teams as t1 ON t1.id = g.id_home 
                LEFT JOIN teams as t2 ON t2.id = g.id_away
                LEFT JOIN league as l ON t1.id_league = l.id AND t2.id_league = l.id
                LEFT JOIN (SELECT g.date, g.id_home, g.id_away, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team=g.id_home THEN 1 END) as home_goals, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team =g.id_away THEN 1 END) as away_goals
                    FROM games AS g
                    LEFT JOIN actionsinmatch as am ON g.id = am.id_match
                    LEFT JOIN actions as a ON a.id = am.id_action
                    LEFT JOIN footballer as f ON am.id_footballer = f.id 
                    LEFT JOIN clubhistory as ch ON (ch.id_team = g.id_away OR ch.id_team = g.id_home) AND 
                    f.id = ch.id_footballer AND (SELECT MAX(ch2.dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer=f.id AND ch2.dateFrom<= g.date) = ch.dateFrom
                    GROUP BY g.id ) as g2 ON (g2.id_home = t1.id  OR g2.id_away = t2.id ) AND g.date = g2.date
                WHERE l.id = %s
                GROUP BY g.id ORDER BY g.date DESC;
                """, (league_id,))
    games_history = cur.fetchall()
    
    return render_template("league_history.html", leagues=league, games_history=games_history)


@app.route('/league_table/<league_id>', methods=["POST","GET"])

def league_table(league_id):
    headings = ['Miejsce', "Drużyna", "Rozegrane mecze", "Wygane", "Remisy", "Przegrane", "Punkty ligowe"]
    cur = mysql.cursor(dictionary=True)
    cur.execute("""
                SELECT l.name AS name, COUNT(*) AS number_of_teams, l.id AS id
                FROM league as l
                LEFT JOIN teams as t ON l.id = t.id_league
                WHERE l.id = %s GROUP BY l.id;""",(league_id,))
    league = cur.fetchone()

    if not league:
        cur.close()
        flash("Wybrana liga nie istnieje","alert alert-danger alert-dismissible")
        return redirect(url_for("list_of_leagues"))

    cur.execute("""SELECT DISTINCT YEAR(date) as year FROM games ORDER BY date DESC;""")
    seasons = cur.fetchall()

    if request.method == "POST":
        year = request.form.get('season_select')
    else:
        year = seasons[0]['year']

    cur.execute("""
                SELECT t.id as id, t.name as team, l.name as league, 
                COUNT(CASE WHEN home_goals > away_goals AND t.id=g.id_home THEN 1 WHEN away_goals > home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as wins,
                COUNT(CASE WHEN home_goals = away_goals AND (t.id=g.id_home OR t.id=g.id_away) THEN 1 END) as draws,
                COUNT(CASE WHEN home_goals < away_goals AND t.id=g.id_home THEN 1 WHEN away_goals < home_goals AND t.id=g.id_away THEN 1 ELSE NULL END) as loses,
                COUNT((SELECT SUM(CASE WHEN g2.id_away=t.id OR g2.id_home=t.id THEN 1 ELSE NULL END) FROM games AS g2
                WHERE (g2.id_away=t.id OR g2.id_home=t.id) AND g2.id IS NOT NULL AND YEAR(g.date) = %s)) AS games_played,
                SUM(CASE WHEN home_goals > away_goals AND t.id=g.id_home THEN 3 WHEN away_goals > home_goals AND t.id=g.id_away THEN 3  
                WHEN home_goals = away_goals AND (t.id=g.id_home OR t.id=g.id_away) THEN 1 ELSE 0 END) as league_points
                FROM teams as t
                LEFT JOIN league as l ON l.id = t.id_league
                LEFT JOIN (SELECT g.date, g.id_home, g.id_away, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team=g.id_home THEN 1 END) as home_goals, COUNT(CASE WHEN a.name = 'Gol' AND ch.id_team =g.id_away THEN 1 END) as away_goals
                    FROM games AS g
                    LEFT JOIN actionsinmatch as am ON g.id = am.id_match
                    LEFT JOIN actions as a ON a.id = am.id_action
                    LEFT JOIN footballer as f ON am.id_footballer = f.id 
                    LEFT JOIN clubhistory as ch ON (ch.id_team = g.id_away OR ch.id_team = g.id_home) AND 
                    f.id = ch.id_footballer AND (SELECT MAX(ch2.dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer=f.id AND ch2.dateFrom<= g.date) = ch.dateFrom
                    WHERE YEAR(g.date) = %s
                    GROUP BY g.id) as g ON g.id_home = t.id OR g.id_away = t.id
                WHERE l.id=%s  GROUP BY t.id ORDER BY league_points DESC;""",(year,year,league_id))
    table_content = cur.fetchall()
    
    return render_template("league_table.html", leagues=league, headings=headings, row=table_content, seasons=seasons, year=int(year))

@app.route('/addgame', methods=["POST","GET"])

def addgame():
    cur = mysql.cursor(dictionary=True)
    cur.execute(""" SELECT l.name AS name, l.id AS id
                FROM league as l
                INNER JOIN teams as t ON l.id = t.id_league
                GROUP BY l.id HAVING COUNT(t.id) >= 2;""")
    leagues=cur.fetchall()
    cur.close()
    
    if request.method == "POST":
        cur = mysql.cursor(dictionary=True)
        try:
            league=request.form.get('league')
            home=request.form.get('home')
            away=request.form.get('away')
            gamedate=request.form.get('gamedate')
            if league and home and away and gamedate:
                cur.execute("INSERT INTO games(id_home,id_away,date) VALUES(%s,%s,%s)",(home,away,gamedate))
                last_game_id=cur.lastrowid
                if request.form.getlist('players[]') and request.form.getlist('players_ac[]') and request.form.getlist('ac_time[]'):
                    players=request.form.getlist('players[]')
                    players_ac=request.form.getlist('players_ac[]')
                    ac_time=request.form.getlist('ac_time[]')
                    if len(players) == len(players_ac) == len(ac_time):
                        for i in range(0, len(players)):
                            cur.execute("INSERT INTO actionsinmatch(id_match,id_footballer,id_action,time) VALUES(%s,%s,%s,%s)",(last_game_id,players[i],players_ac[i],ac_time[i]))     
                    else:
                        cur.close()
                        flash("liczba akcji jest niezgodna z liczbą piłkarzy","alert alert-danger alert-dismissible")
                        return redirect(url_for("addgame")) 
                    
                    
                cur.close()
                mysql.commit()
                flash("Pomyślnie dodano rozgrywkę","alert alert-success alert-dismissible")
                #tu też redirect do listy
                return redirect(url_for("index"))
            else:
                cur.close()
                flash("Należy uzupełnić dane","alert alert-danger alert-dismissible")
                return redirect(url_for("addgame"))
        except Exception as e:
            mysql.rollback()
            cur.close()
            flash("Wystąpił błąd w bazie danych: "+str(e),"alert alert-danger alert-dismissible")
            #tu zmienić na liste gier jak będzie
            return redirect(url_for("list_of_leagues"))
    
    return render_template("addgame.html", leagues=leagues)

#partials
@app.get('/getteams')

def getteams():
    league=request.args.get('league')
    if not league:
        return render_template("partials/blank.html")
    cur=mysql.cursor(dictionary=True)
    cur.execute("SELECT id, name FROM teams WHERE id_league=%s",(league,))
    teams=cur.fetchall()
    cur.close()
    return render_template("partials/getteams.html",teams=teams)

@app.get('/getplayers')

def getplayers():
    home=request.args.get('home')
    away=request.args.get('away')
    date=request.args.get('gamedate')
    if not home or not away or not date:
        return render_template("partials/blank.html")
    cur=mysql.cursor(dictionary=True)
    cur.execute("""
                SELECT f.id AS ftid, CONCAT(t.name,'-',f.name, ' ', f.lastName) AS player
                FROM clubhistory AS ch
                LEFT JOIN teams as t ON t.id = ch.id_team
                LEFT JOIN footballer as f ON f.id = ch.id_footballer 
                WHERE t.id IN(%s,%s) AND dateFrom = (SELECT MAX(dateFrom) FROM clubhistory as ch2 WHERE ch2.id_footballer =ch.id_footballer AND ch2.dateFrom<=%s )""", (home,away,date))
    players=cur.fetchall()
    cur.execute("SELECT id, name FROM actions")
    action_list = cur.fetchall()
    cur.close()
    return render_template("partials/getplayers.html", players=players, actions=action_list)
#invalid URL
@app.errorhandler(404)

def not_found(e):
    return render_template("404.html"), 404



if __name__ == "__main__":
    app.run(debug=True)
    