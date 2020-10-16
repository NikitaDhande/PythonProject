import gevent.monkey

gevent.monkey.patch_all()

import constants
import requests
import time
from database_operations import db

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

database = db()
database.reset_active_users()

'''
====================================================================================================
Session Methods
====================================================================================================
'''

@app.route('/')
def session_loginpage():
    return render_template('Login.html')

@app.route('/alljobs')  
def session_alljobspage():
    if 'username' in session and 'password' in session:
        if session['username'] and session['password']:
            return render_template('alljobs.html')
    else:
        print("====================Session ended=======================")
        return redirect(url_for('/'))

@app.route('/stationdata')  
def session_stationspage():
    if 'username' in session and 'password' in session:
        if session['username'] and session['password']:
            return render_template('station_config.html')
    else:
        print("====================Session ended=======================")
        return redirect(url_for('/'))


'''
====================================================================================================
Basic Methods
====================================================================================================
'''


@socketio.on('serverside')
def handleMessage(msg):
    print(msg)
    print("=================================================")
    socketio.emit("data", "H")


@socketio.on('join')
def on_join(data):
    username = data['username']
    password = data['password']
    session['username'] = username
    session['password'] = password
    ip = request.environ['REMOTE_ADDR']
    x = database.login_user(username=username, password=password)
    if x != False:
        y = database.add_active_user(username=username, role=x, ip=ip)
        if y != False:
            join_room(ip)
            socketio.emit("login_cred", 'Welcome, ' + data['username'] + '. Logging you in !', room=ip)
            print(username + ' has entered the room.')
            time.sleep(1)
            socketio.emit("load_all_jobs", 'loading_all_jons', room=ip)
        else:
            join_room(ip)
            socketio.emit("login_cred", 'Welcome, ' + data[
                'username'] + '.You are logged in on different machine.Please log out to continue !',
                          room=ip)

            leave_room(ip)
    else:
        join_room(ip)
        socketio.emit("login_cred", "User details not found. Please check credentials again.",
                      room=ip)
        leave_room(ip)


@socketio.on('login_page')
def login(data):
    print("================Login Page Loaded======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        join_room(ip)
        socketio.emit("login_cred", 'Welcome, ' + x["username"] + '. Logging you in !', room=ip)
        time.sleep(1)
        socketio.emit("load_all_jobs", 'loading_all_jons', room=ip)


@socketio.on('logout')
def logout(data):
    print("================Logout======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.del_active_user(ip)
    print(x)
    close_room(ip)
    print(rooms)
    socketio.emit("redirect", "loginpage")


'''
====================================================================================================
All Jobs Page
====================================================================================================
'''


@socketio.on('user_action')
def user_action(data):
    print("================All jobs User action Detected======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        print(data)
        if "role" in x:
            if x["role"] == "Admin" or x["role"] == "Manager":
                if "jobnumber" in data:
                    if "action" in data:
                        if data["action"] == "redo":
                            y = database.redo_job(jobnumber=data["jobnumber"])
                            if y != False:
                                join_room(ip)
                                socketio.emit("console_status", "Done resetting the job.", room=ip)
                                leave_room(ip)
                            else:
                                join_room(ip)
                                socketio.emit("console_status", "Error resetting the job.", room=ip)
                                leave_room(ip)

                        if data["action"] == "delete":
                            y = database.delete_job(jobnumber=data["jobnumber"])
                            print("deleting the job")
                            join_room(ip)
                            socketio.emit("console_status", "Done deleting the job.", room=ip)
                            all_job_data = database.get_all_jobs()
                            socketio.emit("all_job_data", all_job_data, room=ip)
                            leave_room(ip)

            else:
                join_room(ip)
                socketio.emit("console_status", "You do not have access to create,redo or delete the job.", room=ip)
                leave_room(ip)


@socketio.on('all_jobs_page')
def all_jobs_page(data):
    print("================All jobs Page Loaded======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    print(ip)

    current_station_data = database.get_current_stations()
    print("====================Current stations====================")
    print(current_station_data)
    join_room(ip)
    socketio.emit("current_station_data", current_station_data, room=ip)
    leave_room(ip)

    all_jobtypes = database.get_all_jobtypes()
    print("====================All job types=====================")
    print(all_jobtypes)
    join_room(ip)
    socketio.emit("all_jobtypes", all_jobtypes, room=ip)
    leave_room(ip)
    
    y = database.find_station(ip)
    if x != False:

        if y == False:
            join_room(ip)
            socketio.emit("console_status", "No specific station found. Loading all jobs.", room=ip)
            print("Loading all job data.")
            socketio.emit("userinfo", x, room=ip)
            all_job_data = database.get_all_jobs()
            socketio.emit("all_job_data", all_job_data, room=ip)
            print(all_job_data)
            print("Sent All Data")
            leave_room(ip)

        else:
            join_room(ip)
            socketio.emit("console_status", "Logged on station " + y["station_no"] + ". Loading current station jobs.",
                          room=ip)

            print("Loading station job data.")
            socketio.emit("userinfo", x, room=ip)
            all_job_data = database.query_jobdetails({"stationnumber": (y["station_no"])})
            socketio.emit("all_job_data", all_job_data, room=ip)
            print(all_job_data)
            print("Sent Station Data")
            leave_room(ip)


@socketio.on('query_job')
def all_jobs_page(data):
    print("================ Query Specific Job ======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    yy = database.find_station(ip)
    if x != False:
        if yy == False:
            print(data)
            join_room(ip)
            socketio.emit("console_status", "Finding data !", room=ip)
            leave_room(ip)
            y = False
            if data["jobnumber"] == "":
                if data["jobstatus"] == '0' and data["jobtype"] != '0':
                    y = database.query_jobdetails({"jobtype": data["jobtype"]})
                if data["jobstatus"] != '0' and data["jobtype"] == '0':
                    y = database.query_jobdetails({"status": data["jobstatus"]})
                if data["jobstatus"] != '0' and data["jobtype"] != '0':
                    y = database.query_jobdetails({"status": data["jobstatus"], "jobtype": data["jobtype"]})
                if data["jobstatus"] == '0' and data["jobtype"] == '0':
                    y = False
            else:

                y = database.query_jobdetails({"jobnumber": data["jobnumber"]})

            if y != False and y != []:
                join_room(ip)
                socketio.emit("all_job_data", y, room=ip)
                socketio.emit("console_status", "Data query Done!", room=ip)
                leave_room(ip)
                print(y)
                print("==============Sent filtered Data =============================")
            else:
                join_room(ip)
                socketio.emit("all_job_data", y, room=ip)
                socketio.emit("console_status", "No data found !", room=ip)
                leave_room(ip)
                print("=================== No data found =============================")

        else:

            print(data)
            join_room(ip)
            socketio.emit("console_status", "Finding data for " + yy["station_no"] + "!", room=ip)
            leave_room(ip)
            y = False
            if data["jobnumber"] == "":
                if data["jobstatus"] == '0' and data["jobtype"] != '0':
                    y = database.query_jobdetails({"jobtype": data["jobtype"], "stationnumber": yy["station_no"]})
                if data["jobstatus"] != '0' and data["jobtype"] == '0':
                    y = database.query_jobdetails({"status": data["jobstatus"], "stationnumber": yy["station_no"]})
                if data["jobstatus"] != '0' and data["jobtype"] != '0':
                    y = database.query_jobdetails(
                        {"status": data["jobstatus"], "jobtype": data["jobtype"], "stationnumber": yy["station_no"]})
                if data["jobstatus"] == '0' and data["jobtype"] == '0':
                    y = False
            else:

                y = database.query_jobdetails({"jobnumber": data["jobnumber"], "stationnumber": yy["station_no"]})

            if y != False and y != []:
                join_room(ip)
                socketio.emit("all_job_data", y, room=ip)
                socketio.emit("console_status", "Data query Done for station " + yy["station_no"] + " !", room=ip)
                leave_room(ip)
                print(y)
                print("==============Sent filtered Data =============================")
            else:
                join_room(ip)
                socketio.emit("all_job_data", y, room=ip)
                socketio.emit("console_status", "No data found for station " + yy["station_no"] + " !", room=ip)
                leave_room(ip)
                print("=================== No data found =============================")


@socketio.on('create_job')
def create_job(data):
    print("================Create Detected======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    
    x = database.find_active_user(ip=ip)
    # print(x)
    # print(rooms)
    
    if x != False:
        # print(data)
        y = database.add_job(productline=data['productline'], jobnumber=data['jobnumber'],
                             batchnumber=data['batchnumber'], sequence=data["sequencenumber"],
                             stationnumber=(data["stationnumber"]), target_quantity=(data["target_quantity"]),
                             done_quantity=0, jobtype=data["jobtype"],
                             status="Not Started",
                             start_date=data["start_date"], due_date=data["due_date"],
                             report_link=("/pdf/" + str(data['jobnumber'])),
                             manager_incharge=data["manager_incharge"], test_incharge=data["test_incharge"],
                             pass_quantity="0", fail_quantity="0")

        print(y)

        if y != False:
            print("job_added")
            join_room(ip)
            socketio.emit("console_status", "Job Created !", room=ip)

            yy = database.find_station(ip)

            if yy == False:

                all_job_data = database.get_all_jobs()

                socketio.emit("all_job_data", all_job_data, room=ip)

                leave_room(ip)

            else:

                queried_job_data = database.query_jobdetails({"stationnumber": yy["station_no"]})

                if queried_job_data != False and queried_job_data != []:
                    
                    socketio.emit("all_job_data", queried_job_data, room=ip)
                    socketio.emit("console_status", "Data query Done for station " + yy["station_no"] + " !", room=ip)
                    leave_room(ip)
                    print(y)
                    print("==============Sent filtered Data =============================")

                else:
                
                    socketio.emit("all_job_data", queried_job_data, room=ip)
                    socketio.emit("console_status", "No data found for station " + yy["station_no"] + " !", room=ip)
                    leave_room(ip)
                    print("=================== No data found =============================")
                
        else:
            join_room(ip)
            socketio.emit("console_status", "Job not Created . Please check if similar Job Number exists!", room=ip)
            leave_room(ip)
            print("Job Not Added.Please check if similar Job Number exists!")


@socketio.on('station_check')
def station_check(data):
    print("================Stations Check Loaded ======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        y = database.find_station(ip)

        if y == False:
            print("Station not found")
            join_room(ip)
            socketio.emit("station_check", "This IP is not configured as station.", room=ip)
            socketio.emit("console", "Could not start test. This IP is not configured as station.", room=ip)
            leave_room(ip)
        else:
            yy = database.query_jobdetails({"jobnumber": data["jobnumber"], "stationnumber": y["station_no"]})
            if yy != False and yy != []:
                join_room(ip)
                socketio.emit("station_check", "OK", room=ip)
                socketio.emit("console", "Starting test.", room=ip)
                leave_room(ip)
                print(y)
                print("==============Starting test=============================")
                print(yy[0]['jobtype'])
                # ---------------------------------------------------------
                # JOB Details API
                # ----------------------------------------------------------
                API_ENDPOINT = "http://" + ip + ":5000/jobdetails"
                data = yy[0]
                r = requests.post(url=API_ENDPOINT, data=data)
                pastebin_url = r.text
                print("The pastebin URL is:%s" % pastebin_url)

                # -----------------------------------------------
                # Job Data API
                # -----------------------------------------------

                job_data = database.get_job_data(jobnumber=data["jobnumber"])

                print("-----------JOB DATA ---------------")
                print(job_data)
                print("-----------------------------")
                url = "http://" + ip + ":5000/jobdata"
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post(url, data=json.dumps(job_data), headers=headers)
                # extracting response text
                pastebin_url = r.text
                print("The pastebin URL is:%s" % pastebin_url)

                # -------------------------------------------------------
                # EMPTY JOB API
                # -------------------------------------------------------

                empty_job_data = database.get_empty_job(jobnumber=data["jobnumber"])
                data1 = {"data": empty_job_data}
                print(data1)
                url = "http://" + ip + ":5000/emptyjobdata"
                # data = {'sender': 'Alice', 'receiver': [{1: "Trial"}, 2, 3, 4, 5], 'message': 'We did it!'}
                headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
                r = requests.post(url, data=json.dumps(data1), headers=headers)

                # extracting response text
                pastebin_url = r.text
                print("The pastebin URL is:%s" % pastebin_url)

                # jobtype_data= database.query_jobnumber(jobnumber=data["jobnumber"])
                print("-----------------------------------")
                print(yy)
                print("-----------------------------------")
                socketio.emit("turn_to_localhost", yy[0]["jobtype"])

            else:
                join_room(ip)
                socketio.emit("station_check", "This jobnumber is configured to another station.", room=ip)
                socketio.emit("console", "Could not start test. This jobnumber is configured to another station.",
                              room=ip)
                leave_room(ip)
                print("=================== Start Invalid =============================")

                # defining the api-endpoint


'''
====================================================================================================
Station Action Page
====================================================================================================
'''


@socketio.on('create_station')
def create_station(data):
    print("================Create Station Detected======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    # print(x)
    # print(rooms)
    if x != False:
        # print(data)
        y = database.add_stations(station_no=data["station_no"], ip=data["ip"])
        print(y)
        if y != False:
            print("job_added")
            join_room(ip)
            socketio.emit("console_status", "Station Created !", room=ip)
            station_data = database.query_all_stations()
            socketio.emit("station_data", station_data, room=ip)
            leave_room(ip)

        else:
            join_room(ip)
            socketio.emit("console_status", "Station not Created . Please check if similar Station Number exists!",
                          room=ip)
            leave_room(ip)
            print("Station Not Added.Please check if similar Station Number exists!")


@socketio.on('station_config_page')
def station_config_page(data):
    print("================Stations Page Loaded======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        print("In correct Loop")
        join_room(ip)
        socketio.emit("userinfo", x, room=ip)
        station_data = database.query_all_stations()
        socketio.emit("station_data", station_data, room=ip)
        leave_room(ip)
        print(station_data)
        print("Sent All Data")


@socketio.on('station_actions')
def station_action(data):
    print("================Station action Detected======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        print(data)
        if "role" in x:
            if x["role"] == "Admin" or x["role"] == "Manager":
                if "ip" in data:
                    if "action" in data:
                        if data["action"] == "delete":
                            y = database.remove_stations(ip=data["ip"])
                            if y != False:
                                join_room(ip)
                                socketio.emit("console_status", "Done deleting the station.", room=ip)
                                station_data = database.query_all_stations()
                                socketio.emit("station_data", station_data, room=ip)

                                leave_room(ip)
            else:
                join_room(ip)
                socketio.emit("console_status", "You do not have access to create,redo or delete the Station.", room=ip)
                leave_room(ip)


'''
==================================================================================
Server to server json
==================================================================================
'''


@app.route('/update_sessiondetails', methods=['POST'])
def update_jobdetails():
    if request.method == 'POST':
        session_data = request.json

        # "print(session_data)
        if '_id' in session_data: del session_data['_id']
        print(session_data)
        x = database.update_jobnumber(session_data["jobnumber"], session_data)
        print(x)
        return "Data received"


@app.route('/update_sessiondata', methods=['POST'])
def update_jobdata():
    if request.method == 'POST':

        session_data = request.json
        print(session_data)
        for i in range(len(session_data)):
            if "_id" in session_data[i]:
                del session_data[i]["_id"]
        x = database.del_jobdata(session_data[0]["jobnumber"])
        print(x)
        x = database.add_many_jobdata(session_data)
        return "Data received"


@app.route('/')
def index():
    return render_template('Login.html')


@app.route('/index')
def index1():
    return render_template('main.html')


@app.route('/alljobs/')
def index2():
    print("================All Jobs Loaded======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        return render_template('alljobs.html')
    else:
        return "Login to View !"


@app.route('/stationdata/')
def stationdata():
    print("================Station Data Loaded======================")
    ip = request.environ['REMOTE_ADDR']
    print(ip)
    x = database.find_active_user(ip=ip)
    print(x)
    print(rooms)
    if x != False:
        if "role" in x:
            if x["role"] == "Admin" or x["role"] == "Manager":
                print("Role Correct")
                return render_template('station_config.html')

            else:
                print("No Login")
                return "Only Manager or Admin can view this page."

    else:
        return "Login to View !"


'''@app.route('/Report/PCB_B')
def report_PCB_B():
    return render_template('REPORTS/B_report.html')


@app.route('/Report/PCB_I')
def report_PCB_I():
    return render_template('REPORTS/I_Report.html')


@app.route('/Report/PCB_TX_COIL')
def report_PCB_TX_COIL():
    return render_template('REPORTS/TX_Coil_REPORT.html')'''


@socketio.on('job_data_request')
def job_data_request(jobnumber):
    room = request.sid
    join_room(room)
    print("================== JOB DATA Requested ====================")
    job_data = database.get_job_data(jobnumber=str(jobnumber))
    print(job_data)
    socketio.emit("job_data_response",job_data,room=room)

@socketio.on('job_details_request')
def job_details_request(jobnumber):
    room = request.sid
    join_room(room)
    print("================== JOB DETAILS Requested ====================")
    job_details = database.query_jobdetails({"jobnumber": str(jobnumber)})
    print(job_details)
    socketio.emit("job_details_response",job_details,room=room)


@app.route('/Report/<jobtype>/<jobnumber>')
def report_of_a_type(jobtype, jobnumber):
    if jobtype == "PCB_Coils_TX":
        return render_template('REPORTS/TX_Coil_REPORT.html', jobnumber=jobnumber)
    if jobtype == "PCB_Coils_RX":
        return render_template('REPORTS/RX_Coil_REPORT.html', jobnumber=jobnumber)
    if jobtype == "PCB_Coils_Monitor":
        return render_template('REPORTS/Monitor_Coil_REPORT.html', jobnumber=jobnumber)
    if jobtype == "PCB_timer":
        return render_template('REPORTS/timer_REPORT.html', jobnumber=jobnumber)
    if jobtype == "PCB_B":
        return render_template('REPORTS/B_report.html', jobnumber=jobnumber)
    if jobtype == "PCB_I":
        return render_template('REPORTS/I_Report.html', jobnumber=jobnumber)


@app.route('/REPORT/<jobnumber>')
def report(jobnumber):
    print("Report Requested")
    print(jobnumber)
    print("----------------")

    job_details = database.query_jobdetails({"jobnumber": str(jobnumber)})
    job_details = job_details[0]
    print(job_details)
    print(job_details["jobtype"])

    # job_data = database.get_job_data(jobnumber=str(jobnumber))
    # print(job_data)

    return render_template('REPORTS/iframe_trial.html',
                           src="/Report/" + job_details["jobtype"] + "/" + str(jobnumber))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, port=80)
