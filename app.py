from flask import Flask, request, redirect, url_for

import flask_login

from airtable import Airtable

from dotenv import load_dotenv

import os

import urllib

from urllib.request import urlopen, Request

load_dotenv()

app = Flask(__name__)

app.secret_key = 'super secret string'  # Change this!

login_manager = flask_login.LoginManager()

login_manager.init_app(app)

users = {}

table = Airtable(os.getenv("AIRTABLE_BASE_KEY"),
                 'Admins', os.getenv("AIRTABLE_API_KEY"))


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

        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'/>
                <input type='password' name='password' id='password' placeholder='password'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    email = request.form['email']

    if email not in users:

        return 'Bad login'

    elif request.form['password'] == users[email]['password']:

        user = User()
        user.id = email
        flask_login.login_user(user)
        return redirect(url_for('home'))

    return 'Bad login'


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return 'Logged out<br><a href = "/login">Log in again.</a>'


@app.route('/getContacts', methods=['GET', 'POST'])
@flask_login.login_required
def getContacts():

    if request.method == 'GET':

        return 'Logged in as: ' + flask_login.current_user.id + '''
               <br> 
               <form action='getContacts' method='POST'>
                <input type='text' name='idNo' id='idNo' placeholder='id number'/>
                <input type='submit' name='submit'/>
               </form>
               '''

    url = 'https://contact-tracer-api.herokuapp.com/find-contacts'
    values = {"ID Number":request.form['idNo']}

    data = urllib.parse.urlencode(values).encode("utf-8")
    req = Request(url, data)
    response = urlopen(req)
    return response.read()

@app.route('/', methods=['GET'])
@flask_login.login_required
def home():

    return '<a href = "/getContacts#">Fetch Contacts.</a><br><a href = "/logout">Log out.</a>'


@login_manager.unauthorized_handler
def unauthorized_handler():
    return 'Unauthorized' + '<br><br><a href = "/login#">Login in here.</a>'
