import serial
from threading import Lock
from flask import Flask, render_template, session, request, jsonify, url_for
from flask_socketio import SocketIO, emit, disconnect
import MySQLdb
import time
import configparser as ConfigParser
import json

async_mode = None

app = Flask(__name__)


ser = serial.Serial('/dev/ttyACM0', 9600) #Spojenie s Arduinom cez seriovu komunikaciu
config = ConfigParser.ConfigParser()
config.read('config.cfg')
myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')
toggle = 'stop'


app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app, async_mode=async_mode)
thread = None
thread_lock = Lock() 

def background_thread(args):
    global toggle #Globalna premenna toggle pre zapnutie/vypnutie zaznamu hodnot
    count = 0
    dataList = []
    db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
    while True:
        if ser.in_waiting > 0: #Ak je na seriovej komunikacii aspon jeden neprecitany byte, podmienka je splnena
            try: #Try-except klauzula kvoli vypadku komunikacie
                data = ser.readline().decode().strip() #Precitanie posledneho riadku zo seriovej komunikacie, dekodovanie a nasledne odstranenie tzv. "trailing whitespaces"
            except:
                print()
            print(data)
            if args:
                toggle = dict(args).get('toggle')
            print(toggle)  
            socketio.sleep(1)
            if toggle == 'start':
                dataDict = {
                    "t": time.time(),
                    "x": count,
                    "data": data}
                dataList.append(dataDict)
            else:
                if len(dataList)>0:
                    aux = str(dataList).replace("'", "\"")
                    cursor = db.cursor()
                    aux = json.dumps(dataList)
                    print(aux)
                    cursor.execute("INSERT INTO final (data) VALUES (%s)", (str(aux),)) #SQL prikaz na ulozenie do databazy
                    db.commit() #Commit databazy, teda potvrdenie zapisu
                    write2file(aux) #Zapis hodnot do textoveho suboru
                dataList = []
            socketio.emit('my_response',
                          {'data': data, 'count': count},
                          namespace='/test')
            count += 1
    db.close()


def write2file(val):
    fo = open("static/files/final.txt","a+")    
    fo.write("%s\r\n" %val)
    return "done"

@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('disconnect_request', namespace='/test')
def disconnect_request():
    session['receive_count'] = session.get('receive_count', 0) + 1
    emit('my_response',
         {'data': 'Disconnected!', 'count': session['receive_count']})
    disconnect()

@socketio.on('connect', namespace='/test')
def test_connect():
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task(target=background_thread, args=session._get_current_object())

@socketio.on('db_event', namespace='/test')
def db_message(message):
    global toggle
    toggle = message['value']
    print(message['value'])
    
@app.route('/graph', methods=['GET', 'POST'])
def graph():
    return render_template('graph.html', async_mode=socketio.async_mode)
    
@app.route('/db')
def db():
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute('''SELECT data FROM final''')
  rv = cursor.fetchall()
  return str(rv)
  
@app.route('/file')
def file_read():
  fo = open("static/files/final.txt","r")
  rows = fo.readlines()
  return str(rows)

@app.route('/dbdata/<string:num>', methods=['GET', 'POST']) #Funkcia na citanie z databazy
def dbdata(num):
  db = MySQLdb.connect(host=myhost,user=myuser,passwd=mypasswd,db=mydb)
  cursor = db.cursor()
  cursor.execute("SELECT data FROM final WHERE id=%s", num)
  rv = cursor.fetchone()
  return str(rv[0])
  
@app.route('/read/<string:num>') #Funkcia na citanie zo suboru
def filedata(num):
    print(num)
    return str(readmyfile(num))

def readmyfile(num): #Pomocna funkcia na precitanie celeho suboru
    fo = open("static/files/final.txt","r")
    rows = fo.readlines()
    return rows[int(num)-1]

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected', request.sid)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=80, debug=True)
