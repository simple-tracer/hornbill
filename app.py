from flask import Flask, request, redirect, url_for, render_template

from cryptography.fernet import Fernet

import flask_login

from airtable import Airtable

from dotenv import load_dotenv

import os

import urllib

from urllib.request import urlopen, Request

import ast 

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("KEY")  # Change this!

login_manager = flask_login.LoginManager()

login_manager.init_app(app)

f = Fernet(os.getenv("KEY"))
u="poder"
print(f.encrypt(u.encode()))
 
users = {}

table = Airtable(os.getenv("AIRTABLE_BASE_KEY"),
                 'Admins', api_key=os.getenv("AIRTABLE_API_KEY"))


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

    print(f.decrypt(users[email]['password'].encode()))

    print(users[email]['password'])

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
    url = 'https://contact-tracer-api.herokuapp.com/find-contacts'
    values = {"ID Number":request.form['idNo']}

    data = urllib.parse.urlencode(values).encode("utf-8")
    req = Request(url, data)
    response = urlopen(req)
    return render_template('contacts.html', contacts=ast.literal_eval(response.read().decode("utf-8")),id=request.form['idNo']) 

@app.route('/smsContacts', methods=['POST'])
@flask_login.login_required
def smsContacts():
    url = 'https://contact-tracer-api.herokuapp.com/sms-contacts'
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


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('not_logged_in.html')
