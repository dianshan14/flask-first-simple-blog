import functools

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash

from flaskr.db import get_db

# 叫做 auth 的 Blueprint
# 就像是 app object, blueprint 需要知道他在哪裡被 define -> __name__
# url_prefix 會被加在每個跟這個 blueprint 有關的 URL 前面
bp = Blueprint('auth', __name__, url_prefix='/auth')

# authentication blueprint 會有 register new user, log in, log out 的 view

# first view : Register
# URL: /auth/register
# view code

# URL: /register , view function: register
# request to /auth/register -> call register() view function and return value is response
@bp.route('/register', methods=('GET', 'POST')) # bp.route
def register():
    # user submit : request.method = POST
    # start validating the input
    if request.method == 'POST':
        # "request.form" is a dict : **mapping submitted form keys and values**
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None

        # validate username and password
        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        # querying the database to check whether username is not already registered
        elif db.execute(
            # ? is placeholder for any user input
            # values in tuple replace the placeholders with.
            'SELECT id FROM user WHERE username = ?', (username,)
        # fetechone(): return one row from the query (next)
        # fetchall(): return a list of all results
        ).fetchone() is not None: # return=None -> not yet register
            error = 'User {} is already registered.'.format(username)

        # validation success, insert new user data into the database
        if error is None:
            db.execute(
                'INSERT INTO user (username, password) VALUES (?, ?)',
                (username, generate_password_hash(password))
                # generate_password_hash() : for security
            )
            # query modefied data : commit() needs to eb called to save the changes
            db.commit()
            
            # after store the user, they are redirected to login page
            # url_for() : generate the URL for the login view based on its name
            # ? better than writing the URL directly, it allow we to change the URL later
            # without changing all code that links to it
            return redirect(url_for('auth.login'))
            # redirect() : generate a 'redirect response' to the generated URL

        # validation error
        # messages that can be retrieved when "rendering the template"
        # -> template can get flash msg
        flash(error)

    # user initially navigates to `auth/register` or there was an validation error
    # HTML page with the registration form should be shown
    return render_template('auth/register.html')


# URL: auth/login
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        # user is queried first and stored in a variable for later use.
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        # check username
        if user is None:
            error = 'Incorrect username.'
        # check password : securely compares
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password.'

        # session : is a dict that store data across requests
        # proxy and cookie
        if error is None:
            # store user's id in a new session
            # data is stored in a "cookie" that is sent to the browser
            # and browser then sends it back with subsequent requests
            # **Flask securely signs the data so that it can’t be tampered with.**
            session.clear()
            session['user_id'] = user['id'] # user_id is stored in session
            # it will be available on subsequent requests
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')


# 在所有 request 開始時，假如已經有 user login 的資訊了，則 user information 應該被 loaded
# 且 made available to other views

# decorator: register a function that rins before the view function, no matter what URL is requested
@bp.before_app_request
def load_logged_in_user():
    # check if a user id is stored in the session
    user_id = session.get('user_id')

    # 'g' lasts for the length of the request
    if user_id is None:
        g.user = None
    # get user data from database
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()


# logout
@bp.route('/logout')
def logout():
    # need to remove the user id from the session
    # then load_logged_in_user will not load a user on subsequent requests
    session.clear()
    return redirect(url_for('index'))


# Require Authentication in Other Views
# 要求使用者要登入才能進行的操作
# decorator for checking user logged in
# return new view function
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        # not loaded -> redirect to login page
        if g.user is None:
            return redirect(url_for('auth.login'))

        # loaded -> original viwes is called and continues normally
        return view(**kwargs)

    return wrapped_view
# be used in blog views