#!/usr/bin/env python3

# The input is either a command to change scanner behavior:
#  - 'kommt', 'geht', 'reserviert' to assign visitor actions
#  - 'gast', 'band', 'crew' to change/assign visitor status
# or a Base45 encoded PK crypto string (RSA 2048 OAEP SHA256)
#  - decodes to '<name>;<contact>' to identify a person.
#  - hashed to identify an entry in the db (!!!ignoring collisions!!)
# Otherwise the input is invalid / discarded

from datetime import datetime
import evdev
from evdev import ecodes
import mysql.connector
import sys
from base45 import b45decode, b45encode
from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto import Hash
import mmh3

scancodes = {
    # Scancode : ASCII Code
    0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
    10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'q', 17: u'w', 18: u'e', 19: u'r',
    20: u't', 21: u'y', 22: u'u', 23: u'i', 24: u'o', 25: u'p', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL',
    30: u'a', 31: u's', 32: u'd', 33: u'f', 34: u'g', 35: u'h', 36: u'j', 37: u'k', 38: u'l', 39: u';',
    40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'z', 45: u'x', 46: u'c', 47: u'v', 48: u'b', 49: u'n',
    50: u'm', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 57: u' ', 100: u'RALT'
}

capscodes = {
    # (SHIFT) Scancode : ASCII Code
    0: None, 1: u'ESC', 2: u'!', 3: u'@', 4: u'#', 5: u'$', 6: u'%', 7: u'^', 8: u'&', 9: u'*',
    10: u'(', 11: u')', 12: u'_', 13: u'+', 14: u'BKSP', 15: u'TAB', 16: u'Q', 17: u'W', 18: u'E', 19: u'R',
    20: u'T', 21: u'Y', 22: u'U', 23: u'I', 24: u'O', 25: u'P', 26: u'{', 27: u'}', 28: u'CRLF', 29: u'LCTRL',
    30: u'A', 31: u'S', 32: u'D', 33: u'F', 34: u'G', 35: u'H', 36: u'J', 37: u'K', 38: u'L', 39: u':',
    40: u'\'', 41: u'~', 42: u'LSHFT', 43: u'|', 44: u'Z', 45: u'X', 46: u'C', 47: u'V', 48: u'B', 49: u'N',
    50: u'M', 51: u'<', 52: u'>', 53: u'?', 54: u'RSHFT', 56: u'LALT',  57: u' ', 100: u'RALT'
}

scanner = evdev.InputDevice('/dev/input/{}'.format(sys.argv[1]))
scan_id = sys.argv[1]
scanner.grab()

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

track_user_stmt = 'INSERT INTO verlaufsdaten (zeitstempel, scanner, besucher_id, aktion) VALUES (%s, %s, %s, %s)'
check_id_stmt = 'SELECT besucher_id FROM stammdaten WHERE besucher_id = %s LIMIT 1'
insert_visitor_stmt = 'INSERT INTO stammdaten (besucher_id, kontakt, status, zustand) VALUES (%s, %s, %s, %s)'
update_visitor_status_stmt = 'UPDATE stammdaten SET status = %s WHERE besucher_id = %s'
update_visitor_zustand_stmt = 'UPDATE stammdaten SET zustand = %s WHERE besucher_id = %s'

ACTION_MESSAGE=('kommt','geht','reserviert','gast','band','crew')
status = 'kommt'

key = RSA.importKey(open('stuss2021_key').read())
cipher = PKCS1_OAEP.new(key, hashAlgo=Hash.SHA256)


def decrypt_contact(scan):
    # Base45 decode + RSA OAEP SHA256 decrypt
    # MurmurHash3 to compute ID for contact details

    msg = b45decode(scan)
    contact = cipher.decrypt(msg)
    # print('\tBase45: {}\n\tContact: {}'.format(scan, contact))
    h = mmh3.hash(contact)
    return h, contact.decode()


def handle(scan):
    global status

    if scan in ACTION_MESSAGE:
        status = scan
        print('Scanner in Modus: "{}"'.format(status))
    else:
        try:
            id, kontakt = decrypt_contact(scan)
            name_idx = kontakt.find('\t')
            if (name_idx == -1):
                print('WARNUNG: Keine validen Kontaktdaten: "{}"'.format(kontakt))
                return
            cursor = get_cursor()
            cursor.execute(check_id_stmt, (id,))
            z = cursor.fetchall()
            if status in ('gast','band','crew'):
                # change visitor 'status', register as default
                # zustand 'kommt' if visitor previously unknown
                if len(z) == 0:
                    cursor.execute(insert_visitor_stmt, (id, kontakt, status, 'kommt'))
                    print('Neuer Besucher erfasst ("{}" / "kommt"):\n\tName: {}\n\tKontakt: {}'.format(
                        status, kontakt[:name_idx], kontakt[name_idx+1:]))
                else:
                    cursor.execute(update_visitor_status_stmt, (status, id))
            else:
                # change visitor 'zustand', register as default
                # status 'gast' if visitor previously unknown
                if len(z) == 0:
                    cursor.execute(insert_visitor_stmt, (id, kontakt, 'gast', status))
                    print('Neuer Besucher erfasst ("gast" / "{}"):\n\tName: {}\n\tKontakt: {}'.format(
                        status, kontakt[:name_idx], kontakt[name_idx+1:]))
                else:
                    cursor.execute(update_visitor_zustand_stmt, (status, id))

            # track activity
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(track_user_stmt, (now, scan_id, id, status))
            print('{} Scanner {} erfasst Besucher "{}" => {}'.format(
                now, scan_id, kontakt[:name_idx], status))

            db.commit()
            cursor.close()
        except mysql.connector.Error as e:
            print('WARNUNG: Datenbankfehler - wir verlieren Daten!\n\t(Scan: {} / Status: {}) ({})'.format(
                scan, status, e))
        except Exception as e:
            print('WARNUNG: Keine valide ID or oder anderer Fehler: {} ({})'.format(scan, e))


def scan():
    try:
        result = ''
        caps = False
        for event in scanner.read_loop():
            if event.type == ecodes.EV_KEY:
                key = evdev.categorize(event)
                if key.scancode == 42: # LSHIFT
                    caps = (key.keystate == 1)
                    continue
                if key.keystate == 1: # Key DOWN
                    if key.scancode == 28: # CRLF
                        handle(result)
                        result = ''
                    else:
                        if not caps:
                            chr=scancodes.get(key.scancode)
                        else:
                            chr=capscodes.get(key.scancode)
                        if chr == None:
                            chr='<{}>'.format(key.scancode)
                        result += chr
    except Exception as e:
        print('WARNUNG: Unbekannter Fehler in der Eingabe: {}'.format(e))


if __name__ == '__main__':
    scan()

