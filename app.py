from cgitb import html
from termios import TABDLY
from flask import Flask, request, render_template, url_for, redirect, jsonify, send_file
import pandas as pd
from io import BytesIO

from db import *
from processing import *

from datetime import datetime, timedelta

from urllib.parse import quote_plus, unquote_plus

from collections import deque

#plotting
import base64
import matplotlib.pyplot as plt


app = Flask(__name__)


# Global Variables
last_change = '-'
html_header = """<html>
<head>
<link rel="stylesheet" href="/static/styles/stylesheet.css">
</head>"""

checkin_einheit_q = deque([], maxlen = 10)

###############################################################################
# Routes
###############################################################################

# General landing page for clients
@app.route('/')
def index():
  return render_template('index.html')

# After clicking a button
@app.route('/', methods=['POST'])
def index_post():
  # Depending on which button was clicked forward to checkin or checkout
  if request.form['action'] == 'Check-In':
    return redirect(url_for('checkin'))
  elif request.form['action'] == 'Check-Out':
    return redirect(url_for('checkout'))
  else:
    return render_template('index.html')

@app.route('/mungg')
def admin():
  global last_change
  no_parcels_total, no_parcels_tobeassigned, no_parcels_tobesorted, no_parcels_sorted, no_parcels_collected, no_parcels_einheit0 = count_parcels()

  return render_template('mungg.html',
      last_change=last_change,
      no_parcels_total=no_parcels_total, no_parcels_tobeassigned=no_parcels_tobeassigned, no_parcels_tobesorted=no_parcels_tobesorted, no_parcels_sorted=no_parcels_sorted, no_parcels_collected=no_parcels_collected, no_parcels_einheit0=no_parcels_einheit0)

# List all known parcels
@app.route('/parcels')
def get_parcels():
  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  cursor.execute("SELECT * FROM parcels")

  row_headers=[x[0] for x in cursor.description] #this will extract row headers

  results = cursor.fetchall()
  cursor.close()
#  json_data=[]
#  for result in results:
#    json_data.append(dict(zip(row_headers,result)))
#  cursor.close()
#  return json.dumps(json_data)

  # Create table in HTML that lists all parcels
  parcel_table_html = '<h1>Parcel Overview</h1>'
  parcel_table_html += '<table><tr>'+' '.join(['<th>'+str(item)+'</th>' for item in row_headers]) + '</tr>'
  for row in results:
    this_parcel_id = row[0]
    parcel_table_html += '<tr>'+' '.join(['<td>'+str(item)+'</td>' for item in row]) + f'<td><a href="search/{this_parcel_id}">Edit</a></td></tr>'
  parcel_table_html += '</table><br><br><a href="/mungg">Back to start</a>'

  return parcel_table_html

# List all shelves
@app.route('/shelves')
def list_shelves():
  html = get_shelves()
  return html
  
# List all shelves proposed
@app.route('/shelves_proposed')
def list_shelves_proposed():
  html = get_shelves_proposed()
  return html

# Detail single shelf
@app.route('/shelf/<shelf_no>')
def shelf(shelf_no):
  html = get_shelf(shelf_no)
  return html

###############################################################################
# Initialize database (Deletes all existing records!) STEP 1
@app.route('/resetonlyifyoureallyreallywant')
def reset():
  return "WARNING!<br>IF YOU CONTINUE THIS WILL RESET THE DATABASE AND DELETE ALL DATA!<br><a href='initdb'>RESET DATABASE</a>"

# Initialize database (Deletes all existing records!) STEP 2
@app.route('/initdb')
def initdb():
  global last_change
  db_init()
  db_init_table_parcels()
  db_init_table_client_log()
  last_change = "Initialized database!"
  return 'Re-initialized database<br><br><a href="/mungg">Back to start</a>'
###############################################################################

# Create new parcel by entering all data by hand
@app.route('/newparcel')
def new_parcel():
  return render_template('new-parcel.html')

# Create new parcel (after clicking SUBMIT)
@app.route('/newparcel', methods=['POST'])
def new_parcel_post():
  global last_change
  # Variable        gets data from form                 or uses default value if form is empty
  parcel_id       = request.form.get('parcel_id')       # Never use default value for parcel_id
  first_name      = request.form.get('first_name')      or '-'
  last_name       = request.form.get('last_name')       or '-'
  einheit_id      = request.form.get('einheit_id')      or '0'
  shelf_proposed  = request.form.get('shelf_proposed')  or '0'
  shelf_selected  = request.form.get('shelf_selected')  or '0'
  dim_1           = request.form.get('dim_1')           or '100'
  dim_2           = request.form.get('dim_2')           or '100'
  dim_3           = request.form.get('dim_3')           or '100'
  weight_g        = request.form.get('weight_g')        or '500'

  # Test if data is valid. Eg. if parcel_id is correct format
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret

  # Test if parcel_id already exists. We can not allow duplicates!
  ret = check_parcel_exists(parcel_id)
  if ret: return f'<b>ERROR:</b> parcel already exists! We can not allow duplicates of the same parcel_id<br><br><a href="/newparcel">try again</a><br><a href="/mungg">home</a>'

  ret = db_insert_into_table('parcels',
          ['parcel_id', 'first_name', 'last_name', 'einheit_id', 'shelf_proposed', 'shelf_selected', 'dim_1', 'dim_2', 'dim_3', 'weight_g'],
          [f'"{parcel_id}"', f'"{first_name}"', f'"{last_name}"', f'"{einheit_id}"', f'{shelf_proposed}', f'{shelf_selected}', f'{dim_1}', f'{dim_2}', f'{dim_3}', f'{weight_g}'])
  if ret:
    last_change = f"ERROR: Unable to manually add parcel {parcel_id}"

  last_change = f"SUCCESS manually adding parcel {parcel_id}"

  #return f'Added new parcel: parcel_id: {parcel_id} FirstName:{first_name} LastName: {last_name} einheit_id: {einheit_id} shelf_proposed: {shelf_proposed} shelf_selected: {shelf_selected} '\
  #              f'dim_1: {dim_1} dim_2: {dim_2} dim_3: {dim_3} weight_g: {weight_g}'
  return render_template('mungg.html')

# Create new parcel QUICK
@app.route('/newparcel_quick')
def new_parcel_quick():
  return render_template('new-parcel-quick.html')

@app.route('/newparcel_quick', methods=['POST'])
def new_parcel_quick_post():
  parcel_id       = request.form.get('parcel_id')
  return redirect(url_for('new_parcel_quick2',  parcel_id=f'{parcel_id}'))

@app.route('/newparcel_quick2/<parcel_id>')
def new_parcel_quick2(parcel_id):
  return render_template('new-parcel-quick2.html')

# Create new parcel QUICK (after clicking SUBMIT)
@app.route('/newparcel_quick2/<parcel_id>', methods=['POST'])
def new_parcel_quick_params_post(parcel_id):
  global last_change
  # Variable        gets data from form
  first_name      = '-'
  last_name       = '-'
  einheit_id      = request.form.get('einheit_id')
  shelf_proposed  = '0'
  shelf_selected  = '0'
  dim_1           = '0'
  dim_2           = '0'
  dim_3           = '0'
  weight_g        = '0'

  ret = db_insert_into_table('parcels',
          ['parcel_id', 'first_name', 'last_name', 'einheit_id', 'shelf_proposed', 'shelf_selected', 'dim_1', 'dim_2', 'dim_3', 'weight_g'],
          [f'"{parcel_id}"', f'"{first_name}"', f'"{last_name}"', f'"{einheit_id}"', f'{shelf_proposed}', f'{shelf_selected}', f'{dim_1}', f'{dim_2}', f'{dim_3}', f'{weight_g}'])
  if ret:
    last_change = f"ERROR: Unable to manually add parcel {parcel_id}"

  last_change = f"SUCCESS manually adding parcel {parcel_id}"

  #return f'Added new parcel: parcel_id: {parcel_id} FirstName:{first_name} LastName: {last_name} einheit_id: {einheit_id} shelf_proposed: {shelf_proposed} shelf_selected: {shelf_selected} '\
  #              f'dim_1: {dim_1} dim_2: {dim_2} dim_3: {dim_3} weight_g: {weight_g}'
  return render_template('new-parcel-quick.html')

# Search for a shelf
@app.route('/search_shelf')
def search_shelf():
  return render_template('search-shelf.html')

# Search for a parcel (after clicking SUBMIT)
@app.route('/search_shelf', methods=['POST'])
def search_shelf_post():
  shelf_no = request.form.get('shelf_no')

#  # Test if shelf is valid
#  ret = test_shelf_no_valid(shelf_no)
#  if ret: return ret + f'<br><a href="/search_shelf">try again</a>'

  return redirect(url_for('shelf',  shelf_no=f'{shelf_no}'))

# Remove all parcels from this shelf
@app.route('/shelf_empty_parcels/<shelf_no>')
def emtpy_shelf(shelf_no):
  shelf = int(shelf_no)
  empty_parcels_in_shelf(shelf_no)
  return redirect(url_for('search_shelf'))

# Search for a parcel
@app.route('/search/<parcel_id>')
def search_parcel(parcel_id):
  return render_template('search.html', parcel_id=f'{parcel_id}')
  
# Search for a parcel (no parcel id)
@app.route('/search_no_id')
def search_parcel_no_id():
  return render_template('search.html')

# Search for a parcel (after clicking SUBMIT)
@app.route('/search/<parcel_id>', methods=['POST'])
def search_parcel_post(parcel_id):
  parcel_id = request.form.get('parcel_id')

  # Test if data is valid. Eg. if parcel_id is correct format
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_cmd)
  cursor.execute(sql_cmd)

  print(f"DBG: cursor={cursor}")

  row = cursor.fetchone()
  if row == None:
    print(f'ERROR: Unable to find parcel with id {parcel_id}')
    return f'ERROR: Unable to find parcel with id {parcel_id}<br><a href="/search_no_id">Search</a>"'

  for row in cursor:
    print(f"* {row}")
    #TODO: Test if multiple parcels match the searched id!

  # Get the values for the different columns. Make them safe for a URL with quote_plus. For example "/" can not be passed!
  parcel_id       = quote_plus(str(row[0]))
  first_name      = quote_plus(str(row[1]))
  last_name       = quote_plus(str(row[2]))
  einheit_id      = quote_plus(str(row[3]))
  shelf_proposed  = quote_plus(str(row[4]))
  shelf_selected  = quote_plus(str(row[5]))
  dim_1           = quote_plus(str(row[6]))
  dim_2           = quote_plus(str(row[7]))
  dim_3           = quote_plus(str(row[8]))
  weight_g        = quote_plus(str(row[9]))

  cursor.close()

  return redirect(url_for('edit_parcel',  parcel_id=f'{parcel_id}', first_name=f'{first_name}', last_name=f'{last_name}', \
                                          einheit_id=f'{einheit_id}', shelf_proposed=f'{shelf_proposed}', shelf_selected=f'{shelf_selected}', \
                                          dim_1=f'{dim_1}', dim_2=f'{dim_2}', dim_3=f'{dim_3}', weight_g=f'{weight_g}'))

# Search for a parcel (after clicking SUBMIT)
@app.route('/search_no_id', methods=['POST'])
def search_parcel_no_id_post():
  parcel_id = request.form.get('parcel_id')

  # Test if data is valid. Eg. if parcel_id is correct format
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret + '<br><br><a href="/search_no_id">Search</a>'

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_cmd)
  cursor.execute(sql_cmd)

  print(f"DBG: cursor={cursor}")

  row = cursor.fetchone()
  if row == None:
    print(f'ERROR: Unable to find parcel with id {parcel_id}')
    return f'ERROR: Unable to find parcel with id {parcel_id}<br><a href="/search_no_id">Search</a>"'

  for row in cursor:
    print(f"* {row}")
    #TODO: Test if multiple parcels match the searched id!

  # Get the values for the different columns. Make them safe for a URL with quote_plus. For example "/" can not be passed!
  parcel_id       = quote_plus(str(row[0]))
  first_name      = quote_plus(str(row[1]))
  last_name       = quote_plus(str(row[2]))
  einheit_id      = quote_plus(str(row[3]))
  shelf_proposed  = quote_plus(str(row[4]))
  shelf_selected  = quote_plus(str(row[5]))
  dim_1           = quote_plus(str(row[6]))
  dim_2           = quote_plus(str(row[7]))
  dim_3           = quote_plus(str(row[8]))
  weight_g        = quote_plus(str(row[9]))

  cursor.close()

  return redirect(url_for('edit_parcel',  parcel_id=f'{parcel_id}', first_name=f'{first_name}', last_name=f'{last_name}', \
                                          einheit_id=f'{einheit_id}', shelf_proposed=f'{shelf_proposed}', shelf_selected=f'{shelf_selected}', \
                                          dim_1=f'{dim_1}', dim_2=f'{dim_2}', dim_3=f'{dim_3}', weight_g=f'{weight_g}'))


# Edit a parcel
@app.route('/edit/<parcel_id>/<first_name>/<last_name>/<einheit_id>/<shelf_proposed>/<shelf_selected>/<dim_1>/<dim_2>/<dim_3>/<weight_g>')
def edit_parcel(parcel_id, first_name, last_name, einheit_id, shelf_proposed, shelf_selected, dim_1, dim_2, dim_3, weight_g):
  # Remove quotes from making strings URL safe:
  parcel_id_uq       = unquote_plus(str(parcel_id))
  first_name_uq      = unquote_plus(str(first_name))
  last_name_uq       = unquote_plus(str(last_name))
  einheit_id_uq      = unquote_plus(str(einheit_id))
  shelf_proposed_uq  = unquote_plus(str(shelf_proposed))
  shelf_selected_uq  = unquote_plus(str(shelf_selected))
  dim_1_uq           = unquote_plus(str(dim_1))
  dim_2_uq           = unquote_plus(str(dim_2))
  dim_3_uq           = unquote_plus(str(dim_3))
  weight_g_uq        = unquote_plus(str(weight_g))

  return render_template('edit.html', parcel_id = parcel_id_uq, first_name = first_name_uq, last_name = last_name_uq,
                                      einheit_id = einheit_id_uq, shelf_proposed = shelf_proposed_uq, shelf_selected = shelf_selected_uq,
                                      dim_1 = dim_1_uq, dim_2 = dim_2_uq, dim_3 = dim_3_uq, weight_g = weight_g_uq)

# Edit a parcel (after clicking SUBMIT)
@app.route('/edit/<parcel_id_old>/<first_name_old>/<last_name_old>/<einheit_id_old>/<shelf_proposed_old>/<shelf_selected_old>/<dim_1_old>/<dim_2_old>/<dim_3_old>/<weight_g_old>', methods=['POST'])
def edit_parcel_post(parcel_id_old, first_name_old, last_name_old, einheit_id_old, shelf_proposed_old, shelf_selected_old, dim_1_old, dim_2_old, dim_3_old, weight_g_old):
  # Get new value from field or if none entered, keep old value from before
  # Never save an empty field, this will cause problems with parametrized urls
  parcel_id       = parcel_id_old # parcel id can not be changed. It is the main identifier of a parcel
  first_name      = request.form.get('first_name')      or first_name_old
  last_name       = request.form.get('last_name')       or last_name_old
  einheit_id      = request.form.get('einheit_id')      or einheit_id_old
  shelf_proposed  = request.form.get('shelf_proposed')  or shelf_proposed_old
  shelf_selected  = request.form.get('shelf_selected')  or shelf_selected_old
  dim_1           = request.form.get('dim_1')           or dim_1_old
  dim_2           = request.form.get('dim_2')           or dim_2_old
  dim_3           = request.form.get('dim_3')           or dim_3_old
  weight_g        = request.form.get('weight_g')        or weight_g_old

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_select_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_select_cmd)
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(f"EDITING {record}")

  # Update this single record
  sql_update_cmd = f'UPDATE parcels SET '\
                      f'first_name = "{first_name}", '\
                      f'last_name = "{last_name}", '\
                      f'einheit_id = "{einheit_id}", '\
                      f'shelf_proposed = {shelf_proposed}, '\
                      f'shelf_selected = {shelf_selected}, '\
                      f'dim_1 = {dim_1}, '\
                      f'dim_2 = {dim_2}, '\
                      f'dim_3 = {dim_3}, '\
                      f'weight_g = {weight_g} '\
                    f'WHERE parcel_id = "{parcel_id}"'
  print(sql_update_cmd)
  cursor.execute(sql_update_cmd)
  mydb.commit()

  # Test if it worked
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(record)

  cursor.close()
  
  global html_header
  html = html_header + f'<body>SUCCESS! Edited: {record}<br><br><a href="/search_no_id" class="movaButton" autofocus>Search</a><br><br><a href="/mungg" class="movaButton">Home</a></body></html>'
  return html


# Search and edit only einheit id
@app.route('/search_change_id')
def search_change_id():
  return render_template('search.html')

# Search and edit only einheit id (after clicking SUBMIT)
@app.route('/search_change_id', methods=['POST'])
def search_parcel_change_id_post():
  parcel_id = request.form.get('parcel_id')

  # Test if data is valid. Eg. if parcel_id is correct format
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret + '<br><br><a href="/search_change_id">Search</a>'

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_cmd)
  cursor.execute(sql_cmd)

  print(f"DBG: cursor={cursor}")

  row = cursor.fetchone()
  if row == None:
    print(f'ERROR: Unable to find parcel with id {parcel_id}')
    return f'<b>ERROR: Unable to find parcel with id {parcel_id}</b><br><a href="/search_change_id">Search</a>"'

  for row in cursor:
    print(f"* {row}")
    #TODO: Test if multiple parcels match the searched id!

  # Get the values for the different columns. Make them safe for a URL with quote_plus. For example "/" can not be passed!
  parcel_id       = quote_plus(str(row[0]))
  einheit_id      = quote_plus(str(row[3]))

  cursor.close()

  return redirect(url_for('edit_parcel_change_id',  parcel_id=f'{parcel_id}', einheit_id=f'{einheit_id}'))


# Edit a parcel
@app.route('/edit_change_id/<parcel_id>/<einheit_id>/')
def edit_parcel_change_id(parcel_id, einheit_id):
  # Remove quotes from making strings URL safe:
  parcel_id_uq       = unquote_plus(str(parcel_id))
  einheit_id_uq      = unquote_plus(str(einheit_id))

  return render_template('edit_change_id.html', parcel_id = parcel_id_uq, einheit_id = einheit_id_uq)

# Edit a parcel (after clicking SUBMIT)
@app.route('/edit_change_id/<parcel_id>/<einheit_id_old>/', methods=['POST'])
def edit_parcel_post_change_id(parcel_id, einheit_id_old):
  # Get new einheit id OR set einheit_id_old if none given
  einheit_id      = request.form.get('einheit_id')    or einheit_id_old

  if int(einheit_id) < 0 or int(einheit_id) > 1100:
    return f'<b>ERROR:</b> Invalid einheit_id: {einheit_id}. Must be between 0 and 1100. <a href="\search_change_id">try again</a>'

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_select_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_select_cmd)
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(f"EDITING {record}")

  # Update this single record
  sql_update_cmd = f'UPDATE parcels SET '\
                      f'einheit_id = "{einheit_id}" '\
                    f'WHERE parcel_id = "{parcel_id}"'
  print(sql_update_cmd)
  cursor.execute(sql_update_cmd)
  mydb.commit()

  # Test if it worked
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(record)

  cursor.close()
  
  return redirect(url_for('search_change_id'))

#############################################
# Upload / Download / Export Functionality
#############################################

# Upload of Excel as specified by Swiss Post
@app.route("/upload_post", methods=['GET', 'POST'])
def upload_post():
  global last_change
  html = 'ERROR: Unable to upload file. WARNING: Can only work with Excel coming from Swiss Post! Not with previously exported file!'
  if request.method == 'POST':
    print(request.files['file'])
    f = request.files['file']
    data_xls = pd.read_excel(f)
    html, string = upload_post_parcels_to_db(data_xls.to_dict())
    last_change = string
    return html
  return '''
  <!doctype html>
  <title>Upload an excel file coming from Swiss Post</title>
  <h1>Excel file upload (xls, xlsx, xlsm, xlsb, odf, ods or odt)</h1>
  <form action="" method=post enctype=multipart/form-data>
  <p><input type=file name=file><input type=submit value=Upload>
  </form>
  '''

# Import Excel that was Exported before (see /export)
@app.route("/import", methods=['GET', 'POST'])
def import_excel():
  global last_change
  html = 'ERROR: Unable to import file. WARNING: Can only work with previously EXPORTED file! Not with the file coming from Swiss Post!'
  if request.method == 'POST':
    print(request.files['file'])
    f = request.files['file']
    data_xls = pd.read_excel(f)
    html, string = import_parcels_to_db(data_xls.to_dict())
    last_change = string
    return html
  return '''
  <!doctype html>
  <title>Import an excel file that was previously exported</title>
  <b>WARNING: This will delete all parcels that are currently in the database!</b>
  <h1>Reset DB and import file (xls, xlsx, xlsm, xlsb, odf, ods or odt)</h1>
  <form action="" method=post enctype=multipart/form-data>
  <p><input type=file name=file><input type=submit value=Upload>
  </form>
  '''
@app.route("/export", methods=['GET'])
def export_records():
  return download_tables_as_xlsx(['parcels', 'client_log'], 'bula_post_parcels.xlsx')

###############################################################################
# Processing
###############################################################################

# Fix missing einheit ID
@app.route('/einheit')
def fix_einheit():
  global last_change
  html_string = fix_parcels_missing_einheit()
  return html_string

# DEPRECATED
#@app.route('/assign')
#def assign_shelf():
#  global last_change
#  html_string, summary_string = assign_shelf_to_new_parcels()
#  last_change = summary_string
#  return html_string

@app.route('/assign_fillup')
def assign_shelf_fillup():
  global last_change
  html_string, summary_string = assign_shelf_to_new_parcels_fillup()
  last_change = summary_string
  return html_string

# Sort a parcel - search it
@app.route('/sort_search')
def sort_search():
  return render_template('sort-search.html')

# Sort a parcel - search it (after clicking SUBMIT)
@app.route('/sort_search', methods=['POST'])
def sort_search_post():
  parcel_id = request.form.get('parcel_id')

  # Test if data is valid. Eg. if parcel_id is correct format
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_cmd)
  cursor.execute(sql_cmd)

  print(f"DBG: cursor={cursor}")

  row = cursor.fetchone()
  if row == None:
    print(f'ERROR: Unable to find parcel with id {parcel_id}')
    return f'ERROR: Unable to find parcel with id {parcel_id}<br><a href="/sort_search">go back</a>"'

  for row in cursor:
    print(f"* {row}")
    #TODO: Test if multiple parcels match the searched id!

  # Get the values for the different columns. Make them safe for a URL with quote_plus. For example "/" can not be passed!
  parcel_id       = quote_plus(str(row[0]))
  shelf_proposed  = quote_plus(str(row[4]))
  shelf_selected  = quote_plus(str(row[5]))
  first_name      = quote_plus(str(row[1]))
  last_name       = quote_plus(str(row[2]))
  einheit_id      = quote_plus(str(row[3]))

  cursor.close()

  return redirect(url_for('sort_edit',  parcel_id=f'{parcel_id}', shelf_proposed=f'{shelf_proposed}', shelf_selected=f'{shelf_selected}', first_name=f'{first_name}', last_name=f'{last_name}', einheit_id=f'{einheit_id}'))

# Sort a parcel - edit it
@app.route('/sort_edit/<parcel_id>/<shelf_proposed>/<shelf_selected>/<first_name>/<last_name>/<einheit_id>')
def sort_edit(parcel_id, shelf_proposed, shelf_selected, first_name, last_name, einheit_id):
  SHELF_MAX = 5000
  SHELF_SORTED = 5000
  # Remove quotes from making strings URL safe:
  parcel_id_uq        = unquote_plus(str(parcel_id))
  shelf_proposed_uq   = unquote_plus(str(shelf_proposed))
  shelf_selected_uq   = unquote_plus(str(shelf_selected))
  first_name_uq       = unquote_plus(str(first_name))
  last_name_uq        = unquote_plus(str(last_name))
  einheit_id_uq       = unquote_plus(str(einheit_id))

  if int(shelf_selected_uq) != 0 and int(shelf_selected_uq) < SHELF_MAX:
    note = f"WARNING: This parcel has already been sorted into shelf {shelf_selected_uq}"
  elif shelf_selected == SHELF_SORTED:
    note = "WARNING: This parcel has already been checked out!"
  else:
    note = ""

  return render_template('sort-edit.html', parcel_id = parcel_id_uq, shelf_proposed = shelf_proposed_uq, shelf_selected = shelf_selected_uq, note=note, first_name = first_name_uq, last_name = last_name_uq, einheit_id = einheit_id_uq)

# Sort a parcel - edit it (after clicking SUBMIT)
@app.route('/sort_edit/<parcel_id>/<shelf_proposed>/<shelf_selected>/<first_name>/<last_name>/<einheit_id>', methods=['POST'])
def sort_edit_post(parcel_id, shelf_proposed, shelf_selected, first_name, last_name, einheit_id):
  global last_change
  shelf_selected  = request.form.get('shelf_selected')

  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  if not checkTableExists(mydb, "parcels"):
      return f'ERROR: table "parcels" does not exist!'

  # Check if we have a parcel in our table that matches parcel_id
  sql_select_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
  print(sql_select_cmd)
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(f"EDITING {record}")

  # Update this single record
  sql_update_cmd = f'UPDATE parcels SET '\
                      f'shelf_selected = {shelf_selected} '\
                    f'WHERE parcel_id = "{parcel_id}"'
  print(sql_update_cmd)
  cursor.execute(sql_update_cmd)
  mydb.commit()

  # Test if it worked
  cursor.execute(sql_select_cmd)
  record = cursor.fetchone()
  print(record)
  cursor.close()

  last_change = f"Sorted parcel {record} into shelf {shelf_selected}"

  # Add entry into client log to indicate shelf was sorted
  # TODO: how to determine client (sorter) id?
  # TODO: Consider also saving the stored shelf number?
  client_id = 0
  store_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  db_insert_into_table('client_log', ['client_id', 'store_time', 'parcel_id'], [f'{client_id}', f'"{store_time}"', f'"{parcel_id}"'])

  #return f'SUCCESS! Sorted parcel {record} to shelf {shelf_selected}. Proposed shelf was {shelf_proposed}<br><br><a href="/mungg>Home</a>'
  return redirect(url_for('sort_search'))

###############################################################################
# Client access (Check-In / Check-Out)
###############################################################################

# Check-In client
@app.route('/checkin')
def checkin():
  return render_template('checkin.html')

# Check-In client (after clicking SUBMIT)
@app.route('/checkin', methods=['POST'])
def checkin_post():
  client_id = request.form.get('client_id')
  # TODO: Check if client id is valid

  checkin_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

  db_insert_into_table('client_log', ['client_id', 'checkin_time'], [f'"{client_id}"', f'"{checkin_time}"'])

  return redirect(url_for('client_search'))

# Client search by einheit ID
@app.route('/client_search')
def client_search():
  return render_template('client-search.html')

# Client search (after clicking SUBMIT)
@app.route('/client_search', methods=['POST'])
def client_search_post():
  global checkin_einheit_q
  einheit_id = request.form.get('einheit_id')
  checkin_einheit_q.append(einheit_id)
  # TODO: Check if einheit id is valid

  SHELF_MAX = 5000

  # Find all parcels for this einheit ID
  results = db_select_from_table_where('parcels', 'einheit_id', f'{einheit_id}')
  print(f'{results}')

  unsorted_parcels = 0
  global html_header
  html = html_header + "\n<body>\n"
  if results == []:
    html += f'Sorry, there are no parcels for einheit {einheit_id}'
  else:
    html += f'The parcels for einheit {einheit_id} can be found in shelves:<br><br>'
    shelf_list = []
    for row in results:
      shelf_selected = row[5]
      shelf_list.append(shelf_selected)
      # Test if a parcel has not yet been sorted into a shelf
      if shelf_selected == 0:
        unsorted_parcels += 1
        if unsorted_parcels < 2:
          html += "Some parcels have not yet been sorted. Please come back later<br><br>"
      # Report a shelf only once
      elif shelf_list.count(shelf_selected) == 1 and shelf_selected < SHELF_MAX:
        html += f'Shelf #{shelf_selected}<br>'
  html += '<br><br><a href="checkin" class="movaButton">Restart</a></body></html>'

  return html

# Check-Out client
@app.route('/checkout')
def checkout():
  return render_template('checkout.html')

# Check-Out client (after clicking SUBMIT)
@app.route('/checkout', methods=['POST'])
def checkout_post():
  client_id = request.form.get('client_id')
  # TODO: Check if client id is valid

  return redirect(url_for('checkout_parcel', client_id=client_id))

# Client checkout parcels
@app.route('/checkout_parcel/<client_id>')
def checkout_parcel(client_id):
  return render_template('checkout-parcel.html')

# Client checkout parcels (after clicking SUBMIT)
@app.route('/checkout_parcel/<client_id>', methods=['POST'])
def checkout_parcel_post(client_id):
  parcel_id = request.form.get('parcel_id')
  if parcel_id == '':
    return 'Finished checking out parcels<br><br><a href="/checkout" class="movaButton">Restart</a>'
  ret = test_parcel_id_valid(parcel_id)
  if ret: return ret

  # Find the parcel and check if it can be checked out
  SHELF_CHECKED_OUT = 50000
  results = db_select_from_table_where('parcels', 'parcel_id', f'{parcel_id}')
  print(f'{results}')

  # Handle parcel not found
  if not db_test_if_value_exists_in_column_in_table('parcels', 'parcel_id', f'{parcel_id}'):
    return f'ERROR: Parcel can not be found!<br><br><a href="/checkout_parcel/{client_id}">try again</a>'

  # Handle parcel not yet sorted or already checked out
  shelf_proposed = results[0][4]
  shelf_selected = results[0][5]
  print(f'shelf_proposed={shelf_proposed} shelf_selected={shelf_selected}')
  if (shelf_proposed == 0):
    return f'ERROR: Parcel has not yet been processed!<br><br><a href="/checkout_parcel/{client_id}">try again</a>'
  if (shelf_proposed == 50000 or shelf_proposed == 40000):
    return f'ERROR: Parcel has already been checked out!<br><br><a href="/checkout_parcel/{client_id}">try again</a>'
  if (shelf_selected == 0):
    return f'ERROR: Parcel has not yet been sorted into shelf {shelf_proposed}!<br><br><a href="/checkout_parcel/{client_id}">try again</a>'
  if (shelf_selected == 50000 or shelf_selected == 40000):
    return f'ERROR: Parcel has already been checked out!<br><br><a href="/checkout_parcel/{client_id}">try again</a>'

  # All checks have passed, the client can check out the parcel

  # Set the shelf_proposed and shelf_selected to 50000 to mark as "checked out"
  db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_CHECKED_OUT, 'parcel_id', f'{parcel_id}')
  db_update_column_for_record_where_column_has_value('parcels', 'shelf_selected', SHELF_CHECKED_OUT, 'parcel_id', f'{parcel_id}')

  # Insert entry into client log to indicate parcel was checked out
  checkout_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
  db_insert_into_table('client_log', ['client_id', 'checkout_time', 'parcel_id'], [f'"{client_id}"', f'"{checkout_time}"', f'"{parcel_id}"'])

  # Depending on the users intention either check out another parcel or return to start
  if request.form['action'] == 'Next':
    # Direct to this route again
    return redirect(url_for('checkout_parcel', client_id=client_id))
  elif request.form['action'] == 'Done':
    global html_header
    return html_header + "\n<title>ParcelSquirrel Check-Out</title><h1>Danke / Merci / Grazie / Grazia</h1>\n" + '<p class="movaFormularTitel">Finished checking out parcels</p><br><a href="/checkout" class="movaButton">Restart</a></body></html>'
  else:
    print("ERROR: Unknown submit name")
  return redirect(url_for('checkout'))

@app.route('/checkin_einheit_log')
def checkin_einheit_log():
  global checkin_einheit_q, html_header
  html = html_header + "<body>"
  html += f'<title>ParcelSquirrel Checkin Log</title><meta http-equiv="refresh" content="5"><h1>Anzeige der lezten 10 Einheiten vom Checkin</h1>'
  for einheit in checkin_einheit_q:
    html += f'{einheit}<br>'
  html += '</body></html>'
  return html

# List client log
@app.route('/clientlog')
def client_log():
  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()
  cursor.execute("SELECT * FROM client_log")

  row_headers=[x[0] for x in cursor.description] #this will extract row headers
  results = cursor.fetchall()

  # Create table in HTML with the log
  html = '<h1>Log</h1>'
  html += '<table><tr><th>#</th>'+' '.join(['<th>'+str(item)+'</th>' for item in row_headers]) + '</tr>'
  for row in results:
    this_parcel_id = row[0]
    html += f'<tr><td>{results.index(row)}</td>'+' '.join(['<td>'+str(item)+'</td>' for item in row])
  html += '</table><br><br><a href="/mungg">Back to start</a>'

  return html

@app.route("/statistics")
def statistics():
  return render_template('statistics.html')

@app.route("/plot")
def plot():
  fig, ax = plt.subplots()

  # Get all dates
  DATETIME_LOWER = datetime(2022, 1, 1)
  results = db_select_from_table_greater_than('client_log', 'store_time', DATETIME_LOWER)
  print(results)
  dates_list = []
  for row in results:
    date = row[3]
    if date not in dates_list:
      dates_list.append(date)

  counts_list = []
  dates_list_days = []
  for date in dates_list:
    date_rounded_day = date.strptime(date.strftime("%Y-%m-%d"), "%Y-%m-%d")
    if date_rounded_day not in dates_list_days:
      dates_list_days.append(date_rounded_day)
      date_lower  = date.strptime(date.strftime("%Y-%m-%d"), "%Y-%m-%d") # round down to the day
      date_upper  = date_lower + timedelta(days=1)
      counts_list.append(db_count_entries_where_in_range('client_log', 'store_time', date_lower, date_upper))

  print(dates_list)
  print(dates_list_days)
  print(counts_list)
  ax.plot(dates_list_days, counts_list, "x")
  fig.suptitle("Parcels processed per day")
  ax.set_title("Parcels SORTED per day")

  plt.xticks(dates_list_days)

  #ax.plot([1, 2])
  # Save it to a temporary buffer.
  buf = BytesIO()
  fig.savefig(buf, format="png")
  buf.seek(0)

  return send_file(buf, mimetype="image/png")



if __name__ == "__main__":
  app.run(host ='0.0.0.0')
