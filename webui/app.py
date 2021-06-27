#!/usr/bin/env python
import mysql.connector
from datetime import datetime

from flask import Flask, render_template, request, send_from_directory
app = Flask(__name__)

import mmh3

def init_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="besuchertracker")

db = init_db()

def get_cursor():
    global db
    try:
        db.ping(reconnect=True, attempts=2, delay=1)
    except mysql.connector.Error as err:
        db = init_db()
    return db.cursor(prepared=True)

get_user_stmt = 'SELECT * FROM stammdaten WHERE besucher_id = %s LIMIT 1'
insert_user_stmt = 'INSERT INTO stammdaten (besucher_id, kontakt, status, zustand) VALUES (%s, %s, %s, %s)'
update_user_stmt = 'UPDATE stammdaten SET status= %s, zustand = %s WHERE besucher_id = %s'
track_user_stmt = 'INSERT INTO verlaufsdaten (zeitstempel, scanner, besucher_id, aktion) VALUES (%s, "webui", %s, %s)'

count_user_status_stmt = '''
SELECT
  COUNT(DISTINCT(besucher_id)) AS anzahl
  ,zustand
  ,status
FROM stammdaten
GROUP BY zustand, status
ORDER BY status, zustand
'''

get_tracking_data_stmt = '''
SELECT
zeitstempel,
scanner,
v.besucher_id,
kontakt,
status,
aktion
FROM verlaufsdaten v
LEFT JOIN
(SELECT kontakt, status, besucher_id FROM stammdaten) as s
on v.besucher_id = s.besucher_id
WHERE
v.besucher_id = IFNULL(%s,v.besucher_id)
AND v.scanner = IFNULL(%s,v.scanner)
ORDER BY zeitstempel DESC
'''

GAST_MAX = 800
CREW_BAND_MAX = 200

@app.route('/stammdaten',methods=['POST','GET'])
def stammdaten():

    message=''
    lvl='info'
    cursor = get_cursor()

    if request.method == 'POST':
        # Update entry from form
        besucher_id = request.form.get('besucher_id', default=0, type=int)
        cursor.execute(get_user_stmt, (besucher_id,))
        besucher = cursor.fetchall()
        status = request.form.get('status')
        zustand = request.form.get('zustand')

        if len(besucher) == 0:
            message = 'Besucher mit ID {} existiert nicht.'.format(besucher_id)
            lvl='warning'
            name = ''
            kontakt = ''
        else:
            message = 'Besucher mit ID {} aktualisiert.'.format(besucher_id)
            print(besucher)
            data = besucher[0][1].decode()
            name = data[:data.find(';')]
            kontakt = data[data.find(';')+1:]
            print('Updating user {}'.format(besucher_id))
            cursor.execute(update_user_stmt, (status, zustand, besucher_id))
            lvl = 'success'

            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(track_user_stmt, (now, besucher_id, status))
            cursor.execute(track_user_stmt, (now, besucher_id, zustand))

        db.commit()
        cursor.close()
    else:
        besucher_id = request.args.get('besucher_id', default=0, type=int)
        cursor.execute(get_user_stmt, (besucher_id,))
        besucher = cursor.fetchall()
        cursor.close()

        if len(besucher) == 0:
            message = 'Besucher mit ID {} existiert nicht.'.format(besucher_id)
            lvl = 'warning'
            print(message)
            if besucher_id == 0:
                besucher_id = ''
                message = ''
            return render_template('stammdaten.html', id = besucher_id,
                                   zustand = 'reserviert', message = message, lvl = lvl)
        else:
            for b in besucher:
                data = b[1].decode()
                status = b[2].decode()
                zustand = b[3].decode()
                name = data[:data.find(';')]
                kontakt = data[data.find(';')+1:]
                if besucher_id != b[0]:
                    print('Warning: unexpected ID {} in query for {}'.format(
                        b[0], besucher_id))

                print("""
                ID:      {}
                Name:    {}
                Kontakt: {}
                Status:  {}
                Zustand: {}
                """.format(besucher_id, name, kontakt,
                           status, zustand))

            message = 'Besucher mit ID {} geladen.'.format(besucher_id)

    return render_template('stammdaten.html',
                           id = besucher_id,
                           name = name,
                           kontakt = kontakt,
                           status = status,
                           zustand = zustand,
                           message = message,
                           lvl = lvl)


@app.route('/verlaufsdaten',methods=['GET'])
def verlaufsdaten():
    cursor = get_cursor()
    besucher_id = request.args.get('besucher_id')
    besucher_id = (besucher_id, None)[besucher_id == '']
    scanner = request.args.get('scanner')
    scanner = (scanner, None)[scanner == '']
    cursor.execute(get_tracking_data_stmt, (besucher_id, scanner))
    verlauf = cursor.fetchall()
    cursor.close()
    return render_template('verlaufsdaten.html',
                           id = (besucher_id, '')[ besucher_id == None ],
                           scanner = (scanner, '')[ scanner == None ],
                           verlauf = verlauf)


@app.route('/',methods=['GET'])
def main():
    cursor = get_cursor()
    cursor.execute(count_user_status_stmt)
    counts = cursor.fetchall()
    cursor.close()
    anwesend = sum((0,anzahl)[zustand.decode() == 'kommt' ] for anzahl, zustand, status in counts)
    anwesend_gast = sum((0,anzahl)[status.decode() == 'gast' and
                                   zustand.decode() == 'kommt'] for
                        anzahl, zustand, status in counts)
    anwesend_crew_band = sum((0,anzahl)[(status.decode() == 'crew' or
                                         status.decode() == 'band') and
                                   zustand.decode() == 'kommt'] for
                        anzahl, zustand, status in counts)
    abwesend = sum((0,anzahl)[zustand.decode() == 'geht' or
                              zustand.decode() == 'reserviert'] for
                   anzahl, zustand, status in counts)
    abwesend_gast = sum((0,anzahl)[status.decode() == 'gast' and
                                   (zustand.decode() == 'geht' or
                                    zustand.decode() == 'reserviert')] for
                        anzahl, zustand, status in counts)
    abwesend_crew_band = sum((0,anzahl)[((status.decode() == 'crew' or
                                         status.decode() == 'band') and
                                   (zustand.decode() == 'geht' or
                                    zustand.decode() == 'reserviert'))] for
                        anzahl, zustand, status in counts)
    reserviert_gast = sum((0,anzahl)[zustand.decode() == 'reserviert' and
                                (status.decode() == 'gast' or
                                 status.decode() == 'nicht registriert') ] for
                     anzahl, zustand, status in counts)
    reserviert_crew_band = sum((0,anzahl)[zustand.decode() == 'reserviert' and
                                (status.decode() == 'crew' or
                                 status.decode() == 'band') ] for
                     anzahl, zustand, status in counts)
    registriert = sum(anzahl for anzahl, zustand, status in counts)

    return render_template('index.html',
                           counts = counts,
                           registriert = registriert,
                           anwesend = anwesend,
                           anwesend_gast = anwesend_gast,
                           anwesend_crew_band = anwesend_crew_band,
                           reserviert_gast = reserviert_gast,
                           reserviert_crew_band = reserviert_crew_band,
                           abwesend = abwesend,
                           abwesend_gast = abwesend_gast,
                           abwesend_crew_band = abwesend_crew_band,
                           gast_max = GAST_MAX,
                           crew_band_max = CREW_BAND_MAX)

if __name__ == '__main__':
    app.run()
