import sqlite3

import click
from flask import current_app, g
from flask.cli import with_appcontext

# g 是特別的 object -> unique for each request
# 用來儲存 可能在 request 時 被多個 function access 的資料

# connection 用來重複使用，而不是每次都 create 一個 connection

# current_app 是另一個 特別的 object，其指向 handle request 的 Flask application
# 當 application 被 created 且 正在 handle request 時，get_db 會被呼叫，所以此時 current_app 可以被使用
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            # 建立一個 connection 到 'DATABASE' configuration key 所指向的 file
            # file 不一定存在，而初始化 database 之後會存在
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        # ? tells the connection to return rows that behave like dicts. This allows accessing the columns by name.
        g.db.row_factory = sqlite3.Row
    return g.db

# 檢查是否 connection 有備 created
# 利用 檢查 g.db 有沒有被 set 的方式來檢查
def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()
# 將會在 application factory 告訴 app close_db function，以便在每個 request 之後可以被呼叫


# 藉由 current_app 來打開檔案 (路徑為 : flaskr package 的相對路徑)
# 如此一來將來 deploy app 的時候就不需要知道 schema.sql 的位置
def init_db():
    db = get_db() # returm the database connection, used to exectute the commands read from the file
    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf-8'))


# ref : http://flask.pocoo.org/docs/1.0/cli/#application-context

# click.command 用來定義一個 command line command : 'init-db'
# 用來 call init_db function 以及顯示成功訊息給 user

# command 被執行時，會帶有 application context 被 push (意思應該是附帶 app 的訊息)
# -> 所以 command 和 extension 可以存取到 app 和 its configuration

# 方法1 cli command decorator
# 例如: @app.cli.command(with_appcontext=False)
# 利用 app instance(Flask) 裡面的 cli (實際上是 click.Group 的 instance) 
# command() (等同於 click.Group 的 command() function，但是這裡還包含了 with_appcontext() 的 callback)
# disable : with_appcontext=Falsk
# 
# 方法2 利用 Click command  decorator來達成，但要另外加上 `with_appcontext` 來達到一樣的行為
@click.command('init-db') 
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo("Initialized the database.")


# 把這個 function 加入到 factory
def init_app(app):
    # 告訴 Flask 當 回傳 response 之後要打掃乾淨時 call 這個 function
    app.teardown_appcontext(close_db)
    # 加入一個新的 command，且這個 command 可以被用 `flask` command 來呼叫
    app.cli.add_command(init_db_command)