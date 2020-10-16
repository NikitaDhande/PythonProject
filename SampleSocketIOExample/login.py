import gevent.monkey

gevent.monkey.patch_all()

from flask import Flask, render_template, send_file, send_from_directory, abort, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO, emit, join_room, leave_room, send, rooms, close_room
from flask_session import Session
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret1!'
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app,manage_session=False)
thread = None
data = 0

@app.route('/')
def loginpage():
    return render_template('index.html')

@app.route('/session')
def profilepage():
    return render_template('session.html')

@socketio.on('join')
def on_join(data):

    username = data['username']
    password = data['password']
    socketio.emit("logged_in", "logged_in")
    socketio.emit("login_details", username)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)
