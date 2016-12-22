# all the imports
import os, urllib2, time
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, session, g, redirect, url_for, abort, render_template, flash

# create our little application :)
app = Flask(__name__)
app.config.from_object(__name__)

# Load default config and override config from an environment variable
app.config.update(dict(
    SQLALCHEMY_DATABASE_URI = "postgresql://yourpostgresql",
    SECRET_KEY='development key',
    USERNAME='admin',
    PASSWORD='default'
))
app.config.from_envvar('FLASKR_SETTINGS', silent=True)
engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

files = ['5MB.zip', '10MB.zip', '20MB.zip', '50MB.zip', '100MB.zip']
regions = ['Singapore - EC2', 'London - EC2', 'California - EC2', 'California - Google']

@app.before_request
def before_request():
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        import traceback; traceback.print_exc()
        g.conn = None

@app.teardown_request
def teardown_request(exception):
    try:
        g.conn.close()
    except Exception as e:
        pass

#### Index
@app.route('/')
def index():
    db = g.conn
    #files = db.execute('select * from file').fetchall()
    stat = {}
    for r in range(1, 5):
        region = regions[r-1]
        stat[region] = {}
        for f in range(1, 6):
            stat[region][files[f-1]] = {}
            count = db.execute('select count(*) from down where fid=(%s) and rid=(%s) and iscdn=false', [f, r]).fetchone()[0]
            avg = 0
            avgcdn = 0
            if not count == 0:
                avg = db.execute('select avg(dlast) from down where fid=(%s) and iscdn=false and rid=(%s)', [f, r]).fetchone()[0]
                avgcdn = db.execute('select avg(dlast) from down where fid=(%s) and iscdn=true and rid=(%s)', [f, r]).fetchone()[0]
            stat[region][files[f-1]]['count'] = count;
            stat[region][files[f-1]]['avg'] = avg;
            stat[region][files[f-1]]['avgcdn'] = avgcdn;

    return render_template('index.html', files=files, regions=regions, stat=stat)


@app.route('/r/<r>/', methods=['GET', 'POST'])
def reg(r=None):
    if not int(r) in range(1, 6):
        abort(404)

    db = g.conn
    #files = db.execute('select * from file').fetchall()

    test = {}
    test['file'] = None
    test['count'] = None
    test['avg'] = None
    test['avgcdn'] = None
    if request.method == 'POST':
        down_fid = int(request.form['file'])
        test['file'] = files[down_fid]
        down_number = int(request.form['number'])
        time_no = 0
        time_cdn = 0
        for i in range(down_number):
            start_no = time.time()
            response1 = urllib2.urlopen('https://s3-ap-northeast-1.amazonaws.com/elen6776/' + files[down_fid])
            response1.read()
            shift = time.time() - start_no
            time_no += shift
            db.execute('insert into down(dlast, fid, rid, iscdn) values (%s, %s, %s, false)',
             [shift, down_fid + 1, r])

            start_cdn = time.time()
            response2 = urllib2.urlopen('https://d2rkoaja68rbuk.cloudfront.net/' + files[down_fid])
            response2.read()
            shift = (time.time() - start_cdn)
            time_cdn += shift
            db.execute('insert into down(dlast, fid, rid, iscdn) values (%s, %s, %s, true)',
             [shift, down_fid + 1, r])

        test['count'] = down_number
        test['avg'] = time_no / down_number
        test['avgcdn'] = time_cdn / down_number

    stat = {}
    for f in range(1, 6):
        stat[files[f-1]] = {}
        count = db.execute('select count(*) from down where fid=(%s) and rid=(%s) and iscdn=false', [f, r]).fetchone()[0]
        avg = 0
        avgcdn = 0
        if not count == 0:
            avg = db.execute('select avg(dlast) from down where fid=(%s) and iscdn=false and rid=(%s)', [f, r]).fetchone()[0]
            avgcdn = db.execute('select avg(dlast) from down where fid=(%s) and iscdn=true and rid=(%s)', [f, r]).fetchone()[0]
        stat[files[f-1]]['count'] = count;
        stat[files[f-1]]['avg'] = avg;
        stat[files[f-1]]['avgcdn'] = avgcdn;

    return render_template('region.html', files=files, regions=regions, stat=stat, rid=int(r), fid=range(5), test=test)

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using
        python server.py
    Show the help text using
        python server.py --help
    """

    HOST, PORT = host, port
    print "running on %s:%d" % (HOST, PORT)
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


  run()
