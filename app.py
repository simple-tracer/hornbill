from flask import Flask, request, redirect, url_for, render_template

from cryptography.fernet import Fernet

import flask_login

from airtable import Airtable

from dotenv import load_dotenv

import os

import urllib

from urllib.request import urlopen, Request

import ast 

import json

from twilio.rest import Client

from datetime import datetime

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("KEY")  # Change this!

login_manager = flask_login.LoginManager()

login_manager.init_app(app)

f = Fernet(os.getenv("KEY"))

ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
NOTIFY_SERVICE_SID = os.getenv('TWILIO_NOTIFY_SERVICE_SID')

client = Client(ACCOUNT_SID, AUTH_TOKEN)

users = {}

table = Airtable(os.getenv("AIRTABLE_BASE"),
                 'Admins', os.getenv("AIRTABLE_KEY"))

users_table = Airtable(os.getenv("AIRTABLE_BASE"),
                 'Users', os.getenv("AIRTABLE_KEY"))

class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    if email not in users:
        return

    user = User()

    user.id = email

    return user


@login_manager.request_loader
def request_loader(request):

    email = request.form.get('email')

    if email not in users:
        return

    user = User()

    user.id = email

    user.is_authenticated = request.form['password'] == users[email]['password']

    return user


@app.route('/login', methods=['GET', 'POST'])
def login():

    airtableUsers = table.get_all(view='Grid view')

    for i in airtableUsers:

        users[i['fields']['Username']] = {'password': i['fields']['Password']}

    if request.method == 'GET':

        return render_template('login.html')

    email = request.form['email']

    if email not in users:

        return 'Bad login'

    elif request.form['password'] == f.decrypt(users[email]['password'].encode()).decode():

        user = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('home'))

    return 'Bad login'


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('logout.html')


@app.route('/getContacts', methods=['GET', 'POST'])
@flask_login.login_required
def getContacts():

    if request.method == 'GET':

        return render_template('find_contacts.html')

    print(request.form['idNo'])
    url = os.getenv("API_URL")+'find-contacts'
    values = {"ID Number":request.form['idNo']}
    data = urllib.parse.urlencode(values).encode("utf-8")
    req = Request(url, data)
    response = urlopen(req)
    return render_template('contacts.html', contacts=ast.literal_eval(response.read().decode("utf-8")),id=request.form['idNo']) 

@app.route('/issueqo', methods=['POST', 'GET'])
@flask_login.login_required
def issueqo():
    print(request.args.get('numbers').replace(",]","]"))
    numbers = ast.literal_eval(request.args.get('numbers').replace(",]","]"))
    bindings = list(map(lambda number: json.dumps({'binding_type': 'sms', 'address': number}), numbers))
    print("=====> To Bindings :>", bindings, "<: =====")
    notification = client.notify.services(NOTIFY_SERVICE_SID).notifications.create(
        to_binding=bindings,
        body="test"
    )
    print(notification.body)
    for i in ast.literal_eval(request.args.get('contacts')):
        users_table.update_by_field('ID Number', i["ID Number"], {'Quarantine Starting Date': datetime.today().strftime('%Y-%m-%d')})
    
    return render_template('ordersplaced.html', contacts=ast.literal_eval(request.args.get('contacts')))


@app.route('/smsContacts', methods=['POST'])
@flask_login.login_required
def smsContacts():
    url = os.getenv("API_URL")+'sms-contacts'
    values = request.form['contacts']
    print(values)
    data = urllib.parse.quote(values).encode('utf-8')
    req = Request(url, data)
    response = urlopen(req)
    return response.read()

@app.route('/', methods=['GET'])
@flask_login.login_required
def home():
    return render_template('home.html')

@app.route('/quarantined', methods=['GET'])
@flask_login.login_required
def quarantined():
    return render_template('quarantined.html', people=users_table.search('Quarantined?', '1'))


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('not_logged_in.html')

if __name__ == '__main__':
    from os import environ
    app.run(debug=False, host='0.0.0.0', port=environ.get("PORT", 5000))