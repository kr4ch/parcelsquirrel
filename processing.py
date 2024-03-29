import mysql.connector
from math import isnan
from itertools import chain, cycle

from db import *


# Global Variables
SHELF_1_DIM     = 255 # mm
SHELF_2_DIM     = 405 # mm
SHELF_3_DIM     = 825 # mm
SHELF_HEIGHT    = 335 # mm. Assumed to be the same for all 3 shelf types
SHELF_UNSORTED  = 0     # Virtual shelf to indicate new parcels that have not yet been sorted
SHELF_NIRVANA   = 40000 # Virtual shelf to indicate parcels that have presumably been collected but not checked out (empty shelf)
SHELF_COLLECTED = 50000 # Virtual shelf to indicate parcels that have already been collected
# RESERVED SHELVES: 0,1,2,3,50000
SHELF_1_LIST    = range(300,587)
### Using chain we can concatenate ranges. But unfortunately it behaves unexpectedly different from a range. When accessing sometimes we have to redefine the global variable
# !! When changing SHELF_2_LIST make sure to edit all instances in this file !!
SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))
SHELF_2_LIST_MIN = min(SHELF_2_LIST)
SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))
SHELF_2_LIST_MAX = max(SHELF_2_LIST)
SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))
SHELF_3_LIST    = range(100,250)

SHELF_ROVER    = 1 # Special shelf to collect all parcels for einheit "Rover"
SHELF_BEREICH  = 2 # Special shelf to collect all parcels for einheit "Bereich"
SHELF_OVERFLOW = 3 # Special (large!) shelf to collect overflow
SHELF_TOFIX    = 4 # Special shelf for parcels that need to be fixed manually (eg. invalid einheit entered)

EINHEIT_VALID_RANGE = range(0,1101) # 0..1100 are supposed to be valid einheit IDs, including 0 for "unassigned"

# Conservatism of the fillup sorting algorithm:
PARCEL_AREA_RESERVE = 0.8                   # We need this factor more area in a shelf. Can be changed to set how "conservative" to fill the shelves. Greater than 1 is conservative. Less than 1 is "optimistic"
REQ_SHELF_AREA      = 1/PARCEL_AREA_RESERVE # Shelf must be no more full than this to be considered for putting more parcels in

SHELF_MAX = 5000 # Maximum number of shelves that can ever exist physically

html_header = """<html>
<head>
<link rel="stylesheet" href="/static/styles/stylesheet.css">
</head>"""

html_header_simple = """<html>
   <head>
      <style>
        th, td {
          text-align: left;
          padding: 8px;
        }
        th {
          background-color: #D6EEEE;
        }
        td {
          background-color: #ebffff;
        }
        * {
        font-family: sans-serif;
        }
        .highlight-yellow {
          background-color: #ffff00;
        }
        .highlight-red {
          background-color: #ff0000;
        }    
        .highlight-green {
          background-color: #33ff00;
        }           
      </style>
   </head>"""

###############################################################################
# Data Processing
###############################################################################

def get_dim_of_shelf(shelf_number):
  """
  Returns the dimension of a shelf (30,45 or 90). If the requested number if not known returns -1
  """
  global SHELF_1_DIM, SHELF_2_DIM, SHELF_3_DIM, SHELF_1_LIST, SHELF_3_LIST
  SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))
  if shelf_number in SHELF_1_LIST:
    return SHELF_1_DIM
  elif shelf_number in SHELF_2_LIST:
    return SHELF_2_DIM
  elif shelf_number in SHELF_3_LIST:
    return SHELF_3_DIM
  else:
    return -1

def get_parcel_area(dim_1, dim_2, dim_3):
  """
  Return area required by this parcel. Longest dimension can be ignored because parcel can be longer than shelf
  """
  max_dim = max(dim_1, dim_2, dim_3)
  #print(f"DBG: max_dim={max_dim}")
  if max_dim == 0: max_dim = 1 # Avoid division by zero
  area = dim_1 * dim_2 * dim_3 / max_dim
  return area

def get_shelves():
  """
  Returns a HTML overview of all shelves and the parcels in them
  """
  global SHELF_1_DIM, SHELF_2_DIM, SHELF_3_DIM, SHELF_1_LIST, SHELF_3_LIST, SHELF_HEIGHT
  SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))

  parcels_count_in_shelves_30 = db_count_entries_where_in_range('parcels', 'shelf_selected', min(SHELF_1_LIST), max(SHELF_1_LIST))
  parcels_count_in_shelves_45 = db_count_entries_where_in_range('parcels', 'shelf_selected', SHELF_2_LIST_MIN, SHELF_2_LIST_MAX)
  parcels_count_in_shelves_90 = db_count_entries_where_in_range('parcels', 'shelf_selected', min(SHELF_3_LIST), max(SHELF_3_LIST))
  parcels_count_in_shelf_1 =    db_count_entries_where('parcels', 'shelf_selected', 1)
  parcels_count_in_shelf_2 =    db_count_entries_where('parcels', 'shelf_selected', 2)
  parcels_count_in_shelf_3 =    db_count_entries_where('parcels', 'shelf_selected', 3)
  parcels_count_in_shelf_4 =    db_count_entries_where('parcels', 'shelf_selected', 4)

  global html_header
  html = html_header_simple
  html += '<body><h1>Overview Parcels sorted into Shelves</h1><a href="/mungg">Back to start</a><br><br>'
  html+= '<table>'
  html += f'<tr><th>Shelf 1 (Rover):</th><td>{parcels_count_in_shelf_1} Parcels</td></tr>'
  html += f'<tr><th>Shelf 2 (Bereich):</th><td>{parcels_count_in_shelf_2} Parcels</td></tr>'
  html += f'<tr><th>Shelf 3 (Overflow):</th><td>{parcels_count_in_shelf_3} Parcels</td></tr>'
  html += f'<tr><th>Shelf 4 (Parcel-Clinic):</th><td>{parcels_count_in_shelf_4} Parcels</td></tr>'
  html += '</table><br>'
  html += f'<br><table><tr><th>Shelves 30cm</th><th>Shelves 45cm</th><th>Shelves 90cm</th></tr>'
  html += f'<tr><th>{parcels_count_in_shelves_30} Parcels</th><th>{parcels_count_in_shelves_45} Parcels</th><th>{parcels_count_in_shelves_90} Parcels</th></tr>'
  html += f'<tr><th>No. {min(SHELF_1_LIST)} - {max(SHELF_1_LIST)}</th><th>No. {SHELF_2_LIST_MIN} - {SHELF_2_LIST_MAX}</th><th>No. {min(SHELF_3_LIST)} - {max(SHELF_3_LIST)}</th></tr>'

  html += f'<tr></tr>'
  for i,j,k in zip(cycle(SHELF_1_LIST), SHELF_2_LIST, cycle(SHELF_3_LIST)):
    print(f"{i} {j} {k}")
    res_shelf_30 = db_select_from_table_where('parcels', 'shelf_selected', i)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_30:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_30 = shelf_area_used / (SHELF_1_DIM*SHELF_HEIGHT)
    res_shelf_45 = db_select_from_table_where('parcels', 'shelf_selected', j)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_45:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_45 = shelf_area_used / (SHELF_2_DIM*SHELF_HEIGHT)
    res_shelf_90 = db_select_from_table_where('parcels', 'shelf_selected', k)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_90:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_90 = shelf_area_used / (SHELF_3_DIM*SHELF_HEIGHT)

    html += f'<tr><td '
    if usage_shelf_30 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_30 > 0.01 and usage_shelf_30 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_30 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{i}">#{i}</a><br>{db_count_entries_where("parcels", "shelf_selected", i)} Parcels<br>{int(100*usage_shelf_30)}% full</td><td '
    if usage_shelf_45 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_45 > 0.01 and usage_shelf_45 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_45 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{j}">#{j}</a><br>{db_count_entries_where("parcels", "shelf_selected", j)} Parcels<br>{int(100*usage_shelf_45)}% full</td><td '
    if usage_shelf_90 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_90 > 0.01 and usage_shelf_90 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_90 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{k}">#{k}</a><br>{db_count_entries_where("parcels", "shelf_selected", k)} Parcels<br>{int(100*usage_shelf_90)}% full</td></tr>'
  html += '</table></body>'
  return html

# Test if parcel already exists in database
def check_parcel_exists(parcel_id):
  return db_test_if_value_exists_in_column_in_table('parcels', 'parcel_id', f'{parcel_id}')

# Get all shelves that are PROPOSED (not sorted in!)
def get_shelves_proposed():
  """
  Returns a HTML overview of all shelves and the parcels in them
  """
  global SHELF_1_DIM, SHELF_2_DIM, SHELF_3_DIM, SHELF_1_LIST, SHELF_3_LIST, SHELF_HEIGHT
  SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))

  parcels_count_in_shelves_30 = db_count_entries_where_in_range('parcels', 'shelf_proposed', min(SHELF_1_LIST), max(SHELF_1_LIST))
  parcels_count_in_shelves_45 = db_count_entries_where_in_range('parcels', 'shelf_proposed', SHELF_2_LIST_MIN, SHELF_2_LIST_MAX)
  parcels_count_in_shelves_90 = db_count_entries_where_in_range('parcels', 'shelf_proposed', min(SHELF_3_LIST), max(SHELF_3_LIST))
  parcels_count_in_shelf_1 =    db_count_entries_where('parcels', 'shelf_proposed', 1)
  parcels_count_in_shelf_2 =    db_count_entries_where('parcels', 'shelf_proposed', 2)
  parcels_count_in_shelf_3 =    db_count_entries_where('parcels', 'shelf_proposed', 3)
  parcels_count_in_shelf_4 =    db_count_entries_where('parcels', 'shelf_proposed', 4)

  global html_header
  html = html_header_simple
  html += '<body><h1>Overview Parcels assigned (not sorted!) into shelves</h1><a href="/mungg">Back to start</a><br>'
  html+= '<table>'
  html += f'<tr><th>Shelf 1 (Rover):</th><td>{parcels_count_in_shelf_1} Parcels</td></tr>'
  html += f'<tr><th>Shelf 2 (Bereich):</th><td>{parcels_count_in_shelf_2} Parcels</td></tr>'
  html += f'<tr><th>Shelf 3 (Overflow):</th><td>{parcels_count_in_shelf_3} Parcels</td></tr>'
  html += f'<tr><th>Shelf 4 (Parcel-Clinic):</th><td>{parcels_count_in_shelf_4} Parcels</td></tr>'
  html += '</table><br>'
  html += f'<br><table><tr><th>Shelves 30cm</th><th>Shelves 45cm</th><th>Shelves 90cm</th></tr>'
  html += f'<tr><th>{parcels_count_in_shelves_30} Parcels</th><th>{parcels_count_in_shelves_45} Parcels</th><th>{parcels_count_in_shelves_90} Parcels</th></tr>'
  html += f'<tr><th>No. {min(SHELF_1_LIST)} - {max(SHELF_1_LIST)}</th><th>No. {SHELF_2_LIST_MIN} - {SHELF_2_LIST_MAX}</th><th>No. {min(SHELF_3_LIST)} - {max(SHELF_3_LIST)}</th></tr>'

  html += f'<tr></tr>'
  for i,j,k in zip(cycle(SHELF_1_LIST), SHELF_2_LIST, cycle(SHELF_3_LIST)):
    print(f"{i} {j} {k}")
    res_shelf_30 = db_select_from_table_where('parcels', 'shelf_proposed', i)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_30:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_30 = shelf_area_used / (SHELF_1_DIM*SHELF_HEIGHT)
    res_shelf_45 = db_select_from_table_where('parcels', 'shelf_proposed', j)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_45:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_45 = shelf_area_used / (SHELF_2_DIM*SHELF_HEIGHT)
    res_shelf_90 = db_select_from_table_where('parcels', 'shelf_proposed', k)
    shelf_area_used = 1 # Avoid div by zero
    for row in res_shelf_90:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      shelf_area_used += area_this_parcel
    usage_shelf_90 = shelf_area_used / (SHELF_3_DIM*SHELF_HEIGHT)

    html += f'<tr><td '
    if usage_shelf_30 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_30 > 0.01 and usage_shelf_30 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_30 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{i}">#{i}</a><br>{db_count_entries_where("parcels", "shelf_proposed", i)} Parcels<br>{int(100*usage_shelf_30)}% full</td><td '
    if usage_shelf_45 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_45 > 0.01 and usage_shelf_45 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_45 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{j}">#{j}</a><br>{db_count_entries_where("parcels", "shelf_proposed", j)} Parcels<br>{int(100*usage_shelf_45)}% full</td><td '
    if usage_shelf_90 < 0.01:
      html += 'class="highlight-green"'
    elif usage_shelf_90 > 0.01 and usage_shelf_90 < 0.5:
      html += 'class="highlight-yellow"'
    elif usage_shelf_90 > 0.5:
      html += 'class="highlight-red"'
    html += f'><a href="/shelf/{k}">#{k}</a><br>{db_count_entries_where("parcels", "shelf_proposed", k)} Parcels<br>{int(100*usage_shelf_90)}% full</td></tr>'
  html += '</table></body>'
  return html

def get_shelf(shelf_no):
  """
  Returns a HTML view of the requested shelf number
  """
  global SHELF_1_LIST, SHELF_2_LIST, SHELF_3_LIST, SHELF_1_DIM, SHELF_2_DIM, SHELF_3_DIM

  shelf = int(shelf_no)
  parcel_count = db_count_entries_where('parcels', 'shelf_selected', shelf)

  if shelf in SHELF_1_LIST:
    shelf_dim = SHELF_1_DIM
  elif shelf in SHELF_2_LIST:
    shelf_dim = SHELF_2_DIM
  elif shelf in SHELF_3_LIST:
    shelf_dim = SHELF_3_DIM
  else:
    shelf_dim = "UNKNOWN"

  results = db_select_from_table_where('parcels', 'shelf_selected', shelf)

  global html_header
  html = html_header
  html += '<body><h1>Shelf Overview</h1><a href="/mungg">Back to start</a><br><a href="/shelves">Back to shelf overview</a><br>'
  html += f'<h2>Shelf #{shelf}</h2>'
  #html += f'<table><tr><th>Width</th><td>{int(int(shelf_dim)/10)} cm</td></tr>'
  html += f'<table>'
  html += f'<tr><th>Height</th><td>{int(SHELF_HEIGHT/10)} cm</td></tr>'
  html += f'<tr><th>Number of Parcels</th><td>{parcel_count}</td></tr>'
  html += f'<tr></tr>'
  html += f'<tr><th>List of Parcels</th></tr>'
  html += f'<tr><th>Parcel ID</th><th>Name</th><th>Einheit</th><th>Dimensions</th><th>Weight</th><th>Shelf Proposed</th></tr>'
  for row in results:
    parcel_id       = row[0]
    first_name      = row[1]
    last_name       = row[2]
    einheit_id      = row[3]
    shelf_proposed  = row[4]
    dim_1           = row[6]
    dim_2           = row[7]
    dim_3           = row[8]
    weight          = row[9]
    html += f'<tr><td>{parcel_id}</td><td>{first_name} {last_name}</td><td>{einheit_id}</td><td>{int(dim_1/10)}x{int(dim_2/10)}x{int(dim_3/10)} cm</td><td>{weight} g</td><td>{shelf_proposed}</td><td><a href="/search/{parcel_id}">Edit</a></td></tr>'
  html += f''
  html += f'</table>'

  html += f'<br><br><br><a href="/shelf_empty_parcels/{shelf_no}" class="movaButton">FACH LEEREN</a>(Achtung entfernt alle Pakete -> 40000)'
  html += '</body>'
  return html

def fix_parcels_missing_einheit():
  """
  Find all parcels that are missing einheit ID and allow editing them.
  """
  mydb = mysql.connector.connect(
    host="mysqldb",
    user="root",
    password="secret",
    database="inventory"
  )
  cursor = mydb.cursor()

  cursor.execute("SELECT * FROM parcels WHERE einheit_id = 0")

  row_headers=[x[0] for x in cursor.description] #this will extract row headers
  results = cursor.fetchall()
  cursor.close()

  # Create table in HTML that lists all parcels
  parcel_table_html = '<h1>Parcel Overview</h1>'
  parcel_table_html += '<table><tr>'+' '.join(['<th>'+str(item)+'</th>' for item in row_headers]) + '</tr>'
  for row in results:
    this_parcel_id = row[0]
    parcel_table_html += '<tr>'+' '.join(['<td>'+str(item)+'</td>' for item in row]) + f'<td><a href="search/{this_parcel_id}">Edit</a></td></tr>'
  parcel_table_html += '</table><br><br><a href="/mungg">Back to start</a>'

  return parcel_table_html

# DEPRECATED
#def assign_shelf_to_new_parcels():
#  """
#  Find all parcels that have not yet been assigned to a shelf (shelf_proposed) 
#  and assigns them.
#  """
#  assigned_count     = 0
#  assigned_parcel_id = []
#  assigned_shelf     = []
#  failed_count       = 0
#  failed_parcel_id   = []
#
#  SHELF_MAX = 5000 # Maximum number of shelves
#
#  # Find all parcels that have not been assigned to a shelf yet  
#  results = db_select_from_table_where('parcels', 'shelf_proposed', '0')
#
#  for row in results:
#    parcel_id_this  = row[0]
#    einheit_id_this = row[3]
#
#    # Determine which shelf this parcel should go on
#    results_einheit = db_select_from_table_where('parcels', 'einheit_id', f'{einheit_id_this}')
#    print(f"DBG: results_einheit={results_einheit}")
#
#    parcel_needs_shelf = True
#    
#    # Find if there are other parcels for the same einheit_id that have already a shelf_proposed
#    if not(results_einheit[0][0] == str(parcel_id_this) and len(results_einheit) == 1):
#      # There are already parcels for this einheit_id, check them all out
#      for row_einheit in results_einheit:
#        parcel_id_einheit      = row_einheit[0]
#        shelf_proposed_einheit = row_einheit[4]
#        # TODO: Check if there is enough space in this shelf
#        ## Get width of this shelf
#        ## Test if new parcel can fit
#
#        if parcel_id_einheit != parcel_id_this and shelf_proposed_einheit != 0 and shelf_proposed_einheit < SHELF_MAX and parcel_needs_shelf:
#            shelf_proposed = row_einheit[4]
#            print(f'Parcel {parcel_id_this} has already parcels for einheit {einheit_id_this} in shelf {shelf_proposed}')
#            parcel_needs_shelf = False
#
#    # This is the only parcel for this einheit_id
#    if parcel_needs_shelf:
#      # Put it into the next empty shelf
#      # TODO: Determine which shelf fits for this parcel size / weight
#
#      # Iterate through all shelves starting at 0 to find the first empty one
#      # TODO: Inefficient!
#      shelf_proposed = 1
#      while (db_test_if_value_exists_in_column_in_table('parcels', 'shelf_proposed', f'{shelf_proposed}')):
#        shelf_proposed += 1
#      print(f'Parcel {parcel_id_this} is the first for einheit {einheit_id_this} and was assigned to shelf {shelf_proposed}')
#
#    if shelf_proposed == 0:
#      print(f"ERROR: Unable to assign shelf to {parcel_id_this}")
#      failed_count += 1
#      failed_parcel_id.append(parcel_id_this)
#    else:
#      # Update this single record
#      ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', shelf_proposed, 'parcel_id', parcel_id_this)
#      if not ret:
#        print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id_this}")
#
#      assigned_count = assigned_count + 1
#      assigned_parcel_id.append(str(parcel_id_this))
#      assigned_shelf.append(str(shelf_proposed))
#  
#  # Generate overview of which shelfs have been assigned
#  html_string = f'Assigned shelf to {assigned_count} parcels:<br><br>'
#  for i in range(assigned_count):
#    html_string += f'ID: {assigned_parcel_id[i]}: Shelf {assigned_shelf[i]}<br>'
#  if failed_count > 0:
#    html_string += f'<br><b>FAILED</b> to assign shelf to {failed_count} parcels:' + '<br>'.join(failed_parcel_id)
#  html_string += '<br><br><a href="/mungg">Back to start</a>'
#
#  summary_string = f"Assigned {assigned_count} parcels to a shelf."
#  if failed_count > 0:
#    summary_string += f"<br>ERROR {failed_count} failed to assign!"
#
#  return html_string, summary_string

def assign_shelf_to_new_parcels_fillup():
  """
  Goal is to assign all parcels to a shelf but keep used shelfs to a minimum.
  Go through all unassigned parcels and collect all parcels that are from a einheit:
  - Fill up existing shelves of this einheit
  - Assing the remaining parcels to empty shelves and try to fill them optimally
  A conservatism factor (~1.2) is used to account for parcels not filling out shelves perfectly
  """
  global PARCEL_AREA_RESERVE, SHELF_MAX
  global SHELF_HEIGHT, REQ_SHELF_AREA
  global SHELF_1_DIM, SHELF_2_DIM, SHELF_3_DIM, SHELF_1_LIST, SHELF_2_LIST, SHELF_3_LIST, SHELF_HEIGHT

  assigned_count     = 0
  assigned_parcel_id = []
  assigned_shelf     = []
  failed_count       = 0
  failed_parcel_id   = []  
  empty_subresults = False
  
  # Generate overview of which shelfs have been assigned
  html_string = ''

  # Find all parcels that have not been assigned to a shelf yet  
  results = db_select_from_table_where('parcels', 'shelf_proposed', '0')
  print(results)
  # Determine which einheit_ids are in the unassigned parcels
  einheit_id_list = []
  for row in results:
    einheit_id = row[3]
    if einheit_id not in einheit_id_list:
      einheit_id_list.append(einheit_id)
  print(f"Einheiten Total to be sorted: {len(einheit_id_list)}")

  # Iterate through every einheit that has parcels to be sorted
  for einheit_id in einheit_id_list:
    print(f"DBG: working on einheit {einheit_id}")
    # Get all unassigned parcels for this einheit
    subresults = db_select_from_table_where_and('parcels', 'shelf_proposed', '0', 'einheit_id', einheit_id)
    print(f"working on einheit {einheit_id} with {len(subresults)} parcels")

    # Special case: all parcels for einheit "0" are NOT sorted into a shelf!
    EINHEIT_EMPTY_LIST = ['0', 0, 'nan', 'None']
    if str(einheit_id) in EINHEIT_EMPTY_LIST:
      # do nothing
      continue # Skipped all parcels for einheit "empty"

    # Special case: all parcels for einheit "rover" go into a special shelf
    EINHEIT_ROVER_LIST = ['rover', 'Rover', 'r', 'R']
    global SHELF_ROVER
    if str(einheit_id) in EINHEIT_ROVER_LIST:
      for row in subresults:
        parcel_id = row[0]
        print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {SHELF_ROVER}")
        # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
        ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_ROVER, 'parcel_id', parcel_id)
        if not ret:
          print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
        else:
          assigned_count = assigned_count + 1
          assigned_parcel_id.append(str(parcel_id))
          assigned_shelf.append(str(SHELF_ROVER))
      continue # Sorted all parcels for einheit "rover"

    # Special case: all parcels for einheit "bereich" go into a special shelf
    EINHEIT_BEREICH_LIST = ['bereich', 'Bereich', 'b', 'B']
    global SHELF_BEREICH
    if str(einheit_id) in EINHEIT_BEREICH_LIST:
      for row in subresults:
        parcel_id = row[0]
        print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {SHELF_BEREICH}")
        # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
        ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_BEREICH, 'parcel_id', parcel_id)
        if not ret:
          print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
        else:
          assigned_count = assigned_count + 1
          assigned_parcel_id.append(str(parcel_id))
          assigned_shelf.append(str(SHELF_BEREICH))
      continue # Sorted all parcels for einheit "bereich"

    # Special case: all parcels for unknown einheit (eg. 'XY') go on a special shelf to be fixed manually
    # This is determined if they are not an integer and have not been handled above (eg. rover or bereich)
    global SHELF_TOFIX
    if not einheit_id.isnumeric():
      print(f"DBG: found einheit {einheit_id} has unknown einheit (not rover, not bereich and non-integer)")
      for row in subresults:
        parcel_id = row[0]
        print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {SHELF_TOFIX}")
        # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
        ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_TOFIX, 'parcel_id', parcel_id)
        if not ret:
          print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
        else:
          assigned_count = assigned_count + 1
          assigned_parcel_id.append(str(parcel_id))
          assigned_shelf.append(str(SHELF_TOFIX))
      continue # Sorted all parcels with unknown bereich

    # Special case: einheit_id must be in range to be valid, else  sort it out to be fixed manually
    global EINHEIT_VALID_RANGE
    if not int(einheit_id) in EINHEIT_VALID_RANGE:
      print(f"DBG: found einheit {einheit_id} out of valid range")
      for row in subresults:
        parcel_id = row[0]
        print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {SHELF_TOFIX}")
        # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
        ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_TOFIX, 'parcel_id', parcel_id)
        if not ret:
          print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
        else:
          assigned_count = assigned_count + 1
          assigned_parcel_id.append(str(parcel_id))
          assigned_shelf.append(str(SHELF_TOFIX))
      continue # Sorted all parcels with bereich out of range
  
    # General Idea:
    ## 1. Ignore the highest dimension for every parcel (long parcels will stick out of a shelf)
    ## 2. Calculate the area for every parcel of einheit
    ## 2A. Add reserve, eg. 20%
    ## 3. Try to fit parcels into other shelfs that are already used by this einheit
    ## 4. Try to fit in a single shelf of size 30, if not fits then 45 else 90
    ## (5. If does not fit into single shelf, subtract area for largest shelf and go back to 4.)

    # Get the area of all parcels for this einheit
    area_parcels_this_einheit = 0
    for row in subresults:
      area_this_parcel = get_parcel_area(row[6], row[7], row[8])
      area_parcels_this_einheit += area_this_parcel

    print(f"Total area required for einheit {einheit_id} is {area_parcels_this_einheit:0.2f} mm^2")
    print(f"We require actually {area_parcels_this_einheit*PARCEL_AREA_RESERVE:0.2f} mm^2")

    # Determine which shelf this parcel should go on

    ## Find if there are other parcels for the same einheit_id that are already placed in a shelf
    ## Ignore parcels that are not yet sorted (0) and that are already taken out (50000)
    global SHELF_COLLECTED, SHELF_UNSORTED, SHELF_NIRVANA
    results_einheit = db_select_from_table_where_and_not_and_not_and_not('parcels', 'einheit_id', f'{einheit_id}', 'shelf_selected', SHELF_UNSORTED, 'shelf_selected', SHELF_COLLECTED, 'shelf_selected', SHELF_NIRVANA)
    #print(f"DBG: results_einheit={results_einheit}")
    if results_einheit == []:
      print(f"No shelves found for einheit {einheit_id}")

    # For every shelf that is already used by this einheit:
    for row_einheit in results_einheit:
      # Stop if all parcels have been sorted
      if area_parcels_this_einheit <= 0:
        print(f"DBG: Sorted all parcels for einheit {einheit_id}")
        break

      parcel_id_einheit      = row_einheit[0]
      shelf_proposed_einheit = row_einheit[4]
      shelf_selected_einheit = row_einheit[5]

      # Check if there is enough space in this shelf to fit more parcels

      ## Find out how much space is already used in this shelf
      results_shelf = db_select_from_table_where('parcels', 'shelf_selected', shelf_selected_einheit)
      shelf_area_used = 0
      for row in results_shelf:
        area_this_parcel = get_parcel_area(row[6], row[7], row[8])
        shelf_area_used += area_this_parcel

      # Only consider this already used shelf if at least xx empty (given by factor REQ_SHELF_AREA)
      dim_this_shelf = get_dim_of_shelf(shelf_selected_einheit)
      if dim_this_shelf == -1:
        print(f"ERROR: unable to determine dimension of shelf {shelf_selected_einheit}")
        failed_count  += 1
        break
      max_shelf_area = dim_this_shelf * SHELF_HEIGHT
      if (shelf_area_used > REQ_SHELF_AREA * max_shelf_area):
        # Use this shelf
        shelf_area_left = max_shelf_area - shelf_area_used
        
        # Go through parcels of this einheit and sort them into this shelf until there is no more space
        subresults_tmp = db_select_from_table_where_and('parcels', 'shelf_proposed', '0', 'einheit_id', einheit_id)
        for row in subresults_tmp:
          parcel_id         = row[0]
          area_this_parcel  = get_parcel_area(row[6], row[7], row[8])

          # Do we have space left in this shelf?
          if shelf_area_left/PARCEL_AREA_RESERVE > area_this_parcel:
            # Sort parcel into this shelf
            shelf_area_left           -= area_this_parcel
            area_parcels_this_einheit -= area_this_parcel
            # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
            ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', shelf_proposed_einheit, 'parcel_id', parcel_id)
            if not ret:
              print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
            else:
              assigned_count = assigned_count + 1
              assigned_parcel_id.append(str(parcel_id))
              assigned_shelf.append(str(shelf_proposed_einheit))
    
    # Finished filling up all existing shelves of this einheit, or no shelves exist for this einheit
  	
    if area_parcels_this_einheit <= 0:
      # All parcels for this einheit_id have been processed
      print(f"All parcels for einheit {einheit_id} could be sorted into existing shelves!")
      break # Stop here for this einheit_id
    
    # We need one (or more) fresh shelves for the remaining parcels of this einheit
    print(f"DBG: area required in fresh shelves: {area_parcels_this_einheit*PARCEL_AREA_RESERVE:0.2f} mm^2")

    # As long as there are parcels left, sort them in:
#    if empty_subresults:
#      empty_subresults = False
#      break
    #iteration_cnt = 0
    if area_parcels_this_einheit > 0:
    #  iteration_cnt += 1
    #  if iteration_cnt > 100:
    #    print(f"ERROR: Can not find any shelf for parcels of einheit {einheit_id} (Iteration overflow)")
    #    html_string   += f"ERROR: Can not find a shelf for parcels of einheit {einheit_id}!"
    #    failed_count  += 1
    #    break # Avoid infinite loop
      # Can we fit the remaining parcels in the smallest shelf?
      if area_parcels_this_einheit*PARCEL_AREA_RESERVE < SHELF_1_DIM*SHELF_HEIGHT:
        shelf_list = SHELF_1_LIST
        print("Need a 30cm shelf")
      elif area_parcels_this_einheit*PARCEL_AREA_RESERVE < SHELF_2_DIM*SHELF_HEIGHT:
        shelf_list = SHELF_2_LIST
        print("Need a 45cm shelf")
      else:
        shelf_list = SHELF_3_LIST 
        print("Need a 90cm shelf")

      print(f"DBG: working on einheit {einheit_id}")

      # Find the first shelf that is empty
      for shelf_no in shelf_list:
        if not db_test_if_value_exists_in_column_in_table('parcels', 'shelf_proposed', f'{shelf_no}'):
          print(f"DBG: found that shelf {shelf_no} is empty. area_parcels_this_einheit={area_parcels_this_einheit}")
          # Stop condition: If we have sorted all parcels, stop going through the shelves
          if area_parcels_this_einheit <= 0:
            break

          # Found an empty shelf. Sort parcels in as long as there is space
          dim_this_shelf = get_dim_of_shelf(shelf_no)
          max_shelf_area = dim_this_shelf * SHELF_HEIGHT
          shelf_area_left = max_shelf_area

          # Go through parcels of this einheit and sort them into this shelf until there is no more space
          subresults_tmp = db_select_from_table_where_and('parcels', 'shelf_proposed', '0', 'einheit_id', einheit_id)
          print(f"DBG: working on {subresults_tmp}")
          if len(subresults_tmp) == 0:
            empty_subresults = True
            break
          for row in subresults_tmp:
            parcel_id         = row[0]
            area_this_parcel  = get_parcel_area(row[6], row[7], row[8])

            print(f"DBG: try to sort {parcel_id} into shelf {shelf_no}")

            # Do we have space left in this shelf?
            if shelf_area_left/PARCEL_AREA_RESERVE > area_this_parcel:
              # Sort parcel into this shelf
              shelf_area_left           -= area_this_parcel
              area_parcels_this_einheit -= area_this_parcel
              print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {shelf_no}")
              # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
              ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', shelf_no, 'parcel_id', parcel_id)
              if not ret:
                print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
              else:
                assigned_count = assigned_count + 1
                assigned_parcel_id.append(str(parcel_id))
                assigned_shelf.append(str(shelf_no))

            else:
              # If no more space, stop trying to fit parcels into this shelf
              print(f"No more space left in shelf {shelf_no}. Parcel {parcel_id} will be sorted into shelf 3")
              # parcel is too big for 90cm shelf, sort it into a special shelf
              SHELF_TOO_LARGE = 3
              ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_TOO_LARGE, 'parcel_id', parcel_id)
              if not ret:
                print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
              else:
                assigned_count = assigned_count + 1
                assigned_parcel_id.append(str(parcel_id))
                assigned_shelf.append(str(SHELF_ROVER))
              break

      # We got here because there are no more shelves available (all are filled)
      # Try to fill smaller shelves
      SHELF_2_LIST    = chain(range(800,911), range(587,634), range(912,939), range(1000,1030), range(2000,2080))
      
      print(f"WARNING: All shelves of the requested type are filled up! Trying to fill parcels for einheit {einheit_id} into other shelves")

      for shelf_no in chain(SHELF_1_LIST, SHELF_2_LIST, SHELF_3_LIST):
        # try to fit left-over parcels into any shelf that has enough space left

        # Find empty shelf
        if not db_test_if_value_exists_in_column_in_table('parcels', 'shelf_proposed', f'{shelf_no}'):
          print(f"DBG: found that shelf {shelf_no} is empty. Left-over area_parcels_this_einheit={area_parcels_this_einheit}")

          # Stop condition: If we have sorted all parcels, stop going through the shelves
          if area_parcels_this_einheit <= 0:
            print(f"DBG: Sorted all parcels for einheit {einheit_id}")
            break

          # Found an empty shelf. Sort parcels in as long as there is space
          dim_this_shelf = get_dim_of_shelf(shelf_no)
          print(f"dim_this_shelf={dim_this_shelf}")
          max_shelf_area = dim_this_shelf * SHELF_HEIGHT
          shelf_area_left = max_shelf_area

          # Go through parcels of this einheit and sort them into this shelf until there is no more space
          subresults_tmp = db_select_from_table_where_and('parcels', 'shelf_proposed', '0', 'einheit_id', einheit_id)
          print(f"DBG: working on {subresults_tmp}")
          if len(subresults_tmp) == 0:
            empty_subresults = True
            break
          for row in subresults_tmp:
            parcel_id         = row[0]
            area_this_parcel  = get_parcel_area(row[6], row[7], row[8])

            print(f"DBG: try to sort {parcel_id} into shelf {shelf_no}")
            print(f"DBG: shelf_area_left/PARCEL_AREA_RESERVE={shelf_area_left/PARCEL_AREA_RESERVE} ? area_this_parcel={area_this_parcel}")

            # Do we have space left in this shelf?
            if shelf_area_left/PARCEL_AREA_RESERVE > area_this_parcel:
              # Sort parcel into this shelf
              shelf_area_left           -= area_this_parcel
              area_parcels_this_einheit -= area_this_parcel
              print(f"Sorting parcel {parcel_id} for einheit {einheit_id} into shelf {shelf_no}")
              # Update the parcels shelf_proposed and add them to assigned_count, assigned_parcel_id, assigned_shelf
              ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', shelf_no, 'parcel_id', parcel_id)
              if not ret:
                print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
              else:
                assigned_count = assigned_count + 1
                assigned_parcel_id.append(str(parcel_id))
                assigned_shelf.append(str(shelf_no))
#            else:            
#              # if too big, then put in shelf 3
#              # If no more space, stop trying to fit parcels into this shelf
#              print(f"No more space left in shelf {shelf_no}. Parcel {parcel_id} will be sorted into shelf 3")
#              # parcel is too big for 90cm shelf, sort it into a special shelf
#              SHELF_TOO_LARGE = 3
#              ret = db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_TOO_LARGE, 'parcel_id', parcel_id)
#              if not ret:
#                print(f"ERROR: Unable to change shelf_proposed for parcel_id {parcel_id}")
#              else:
#                assigned_count = assigned_count + 1
#                assigned_parcel_id.append(str(parcel_id))
#                assigned_shelf.append(str(SHELF_ROVER))
#              break
          


      


  # Fill out the overview of sorted parcels
  for i in range(assigned_count):
    html_string += f'ID: {assigned_parcel_id[i]}: Shelf {assigned_shelf[i]}<br>'
  if failed_count > 0:
    html_string += f'<br><b>FAILED</b> to assign shelf to {failed_count} parcels:' + '<br>'.join(failed_parcel_id)
  
  html_string += f'<br><br>Assigned shelf to {assigned_count} parcels'
  html_string += '<br><br><a href="/mungg">Back to start</a>'

  summary_string = f"Assigned {assigned_count} parcels to a shelf."
  if failed_count > 0:
    summary_string += f"<br>ERROR: {failed_count} failed to assign!"

  return html_string, summary_string

# Keep current database and add parcels from Post
def upload_post_parcels_to_db(parcel_dict):
  # Keep a list of which parcels where imported into the db and which were skipped
  parcels_imported_count = 0
  parcels_imported_list  = []
  parcels_skipped_count  = 0
  parcels_skipped_list   = []
  parcels_skipped_cause  = []

  # We need all columns in the Excel sheet to be able to process it. Check and abort if not all are available
  required_keys = [False,False,False,False,False,False,False,False]
  for key in parcel_dict:
    if key   == 'IC':         required_keys[0] = True # Parcel ID
    elif key == 'NAME3':      required_keys[1] = True # First Name
    elif key == 'STRASSE':    required_keys[2] = True # Last Name / Vulgo
    elif key == 'NAME2':      required_keys[3] = True # Einheit ID
    elif key == 'DIM_1':      required_keys[4] = True # Dimension 1 in mm
    elif key == 'DIM_2':      required_keys[5] = True # Dimension 2 in mm
    elif key == 'DIM_3':      required_keys[6] = True # Dimension 3 in mm
    elif key == 'GEWICHT':    required_keys[7] = True # Weight in gram
    else: print(f"WARNING: Unknown column in table: {key}")
  
  if not all(required_keys):
    return "<h1>ERROR: Missing column in Excel sheet! Need (IC, NAME3, STRASSE, NAME2, DIM_1, DIM_2, DIM_3, GEWICHT)<h1>", ""

  print(parcel_dict)

  parcel_count = len(parcel_dict['IC'])

  for i in range(parcel_count):
    # If cell is empty, it will give us 'NaN'. Convert it to 0.
    # TODO: Generate warning if we get a NaN!
    parcel_id  = str(parcel_dict['IC'][i] if isinstance(parcel_dict['IC'][i], int) else 0)            # Expect int
    first_name = str(parcel_dict['NAME3'][i])                                                         # Expect string
    last_name  = str(parcel_dict['STRASSE'][i])                                                       # Expect string
    einheit_id = str(parcel_dict['NAME2'][i])                                                         # Expect string
    dim_1      = str(int(parcel_dict['DIM_1'][i]) if not isnan(parcel_dict['DIM_1'][i]) else 0)       # Expect float
    dim_2      = str(int(parcel_dict['DIM_2'][i]) if not isnan(parcel_dict['DIM_2'][i]) else 0)       # Expect float
    dim_3      = str(int(parcel_dict['DIM_3'][i]) if not isnan(parcel_dict['DIM_3'][i]) else 0)       # Expect float
    weight_g   = str(parcel_dict['GEWICHT'][i] if isinstance(parcel_dict['GEWICHT'][i], int) else 0)  # Expect int
    
    # Test if data is valid. Eg. if parcel_id is correct format
    ret = test_parcel_id_valid(parcel_id)
    if ret: return ret, ""

    # Test if parcel_id already exists, we dont want any duplicates
    mydb = mysql.connector.connect(
      host="mysqldb",
      user="root",
      password="secret",
      database="inventory"
    )
    cursor = mydb.cursor()

    if not checkTableExists(mydb, "parcels"):
        return f'ERROR: table "parcels" does not exist!', ""

    sql_cmd = f"SELECT * FROM parcels WHERE parcel_id = '{parcel_id}'"
    print(sql_cmd)
    cursor.execute(sql_cmd)    
    row = cursor.fetchone()
    if row != None:
      print(f'ERROR: There is already a parcel with id {parcel_id}')
      parcels_skipped_count += 1
      parcels_skipped_list.append(str(parcel_id))
      parcels_skipped_cause.append("Duplicate Parcel ID")
      continue # skip inserting the parcel into the db

    else:
      print("No duplicate parcel ids found (this is good!)")

    # Now insert the new parcel into the db
    # Note: shelf_proposed and shelf_selected are empty after import!
    sql_cmd =  f'INSERT INTO '\
                  'parcels '\
                    '(parcel_id, first_name, last_name, einheit_id, shelf_proposed, shelf_selected, dim_1, dim_2, dim_3, weight_g) '\
                'VALUES ('\
                  f'"{parcel_id}", '\
                  f'"{first_name}", '\
                  f'"{last_name}", '\
                  f'"{einheit_id}", '\
                  f'0, '\
                  f'0, '\
                  f'{dim_1}, '\
                  f'{dim_2}, '\
                  f'{dim_3}, '\
                  f'{weight_g})'
    print(sql_cmd)
    cursor.execute(sql_cmd)
    mydb.commit()
    cursor.close()

    parcels_imported_count += 1
    parcels_imported_list.append(str(parcel_id))

  html_imported_parcels = "<h1>DONE importing parcels from Excel upload</h1><br>"
  html_imported_parcels += f"TOTAL \t({parcel_count}) parcels found in Excel file<br>"
  html_imported_parcels += f"SUCCESS \t({parcels_imported_count}) have been imported<br>"
  html_imported_parcels += f"FAIL \t({parcels_skipped_count}) have been skipped (eg. because of duplicate parcel id)<br><br>List of fails:"
  for i in range(len(parcels_skipped_list)):
    html_imported_parcels += f'<br>\t{parcels_skipped_list[i]} (Cause: {parcels_skipped_cause[i]})'
  html_imported_parcels += f"<br><br>List of successes:<br>" + '<br>\t'.join(parcels_imported_list) + '<br><br><a href="/mungg">Back to start</a>'

  import_parcels_string = f"Imported parcels from Excel Sheet. Of a total {parcel_count} parcels succesfully imported {parcels_imported_count}."
  if parcels_skipped_count > 0:
    import_parcels_string += f" {parcels_skipped_count} failed to import!"

  return html_imported_parcels, import_parcels_string

# Reset database and Import parcels. Excel file was previously exported to excel
def import_parcels_to_db(parcel_dict):
  parcels_imported_count = 0

  # Reset the parcel database. Keep log
  db_init()
  db_init_table_parcels()

  # We need all columns in the Excel sheet to be able to process it. Check and abort if not all are available
  required_keys = [False,False,False,False,False,False,False,False,False,False]
  for key in parcel_dict:
    if key   == 'parcel_id':      required_keys[0] = True # Parcel ID
    elif key == 'first_name':     required_keys[1] = True # First Name
    elif key == 'last_name':      required_keys[2] = True # Last Name / Vulgo
    elif key == 'einheit_id':     required_keys[3] = True # Einheit ID
    elif key == 'shelf_proposed': required_keys[4] = True # Shelf proposed
    elif key == 'shelf_selected': required_keys[5] = True # Shelf selected
    elif key == 'dim_1':          required_keys[6] = True # Dimension 1 in mm
    elif key == 'dim_2':          required_keys[7] = True # Dimension 2 in mm
    elif key == 'dim_3':          required_keys[8] = True # Dimension 3 in mm
    elif key == 'weight_g':       required_keys[9] = True # Weight in gram
    else: print(f"WARNING: Unknown column in table: {key}")
  
  if not all(required_keys):
    return "<h1>ERROR: Missing column in Excel sheet!<h1>", ""

  print(parcel_dict)

  parcel_count = len(parcel_dict['parcel_id'])

  for i in range(parcel_count):
    # If cell is empty, it will give us 'NaN'. Convert it to 0.
    # TODO: Generate warning if we get a NaN!
    parcel_id       = str(parcel_dict['parcel_id'][i] if isinstance(parcel_dict['parcel_id'][i], int) else 0)                  # Expect int
    first_name      = str(parcel_dict['first_name'][i])                                                                 # Expect string
    last_name       = str(parcel_dict['last_name'][i])                                                                  # Expect string
    einheit_id      = str(parcel_dict['einheit_id'][i])
    shelf_proposed  = str(int(parcel_dict['shelf_proposed'][i]) if not isnan(parcel_dict['shelf_proposed'][i]) else 0)  # Expect float
    shelf_selected  = str(int(parcel_dict['shelf_selected'][i]) if not isnan(parcel_dict['shelf_selected'][i]) else 0)  # Expect float
    dim_1           = str(int(parcel_dict['dim_1'][i]) if not isnan(parcel_dict['dim_1'][i]) else 0)                    # Expect float
    dim_2           = str(int(parcel_dict['dim_2'][i]) if not isnan(parcel_dict['dim_2'][i]) else 0)                    # Expect float
    dim_3           = str(int(parcel_dict['dim_3'][i]) if not isnan(parcel_dict['dim_3'][i]) else 0)                    # Expect float
    weight_g        = str(parcel_dict['weight_g'][i] if isinstance(parcel_dict['weight_g'][i], int) else 0)             # Expect int
    
    # Test if data is valid. Eg. if parcel_id is correct format
    ret = test_parcel_id_valid(parcel_id)
    if ret: return ret, ""

    # Test if parcel_id already exists, we dont want any duplicates
    mydb = mysql.connector.connect(
      host="mysqldb",
      user="root",
      password="secret",
      database="inventory"
    )
    cursor = mydb.cursor()

    if not checkTableExists(mydb, "parcels"):
        return f'ERROR: table "parcels" does not exist!', ""

    # Now insert the new parcel into the db
    sql_cmd =  f'INSERT INTO '\
                  'parcels '\
                    '(parcel_id, first_name, last_name, einheit_id, shelf_proposed, shelf_selected, dim_1, dim_2, dim_3, weight_g) '\
                'VALUES ('\
                  f'"{parcel_id}", '\
                  f'"{first_name}", '\
                  f'"{last_name}", '\
                  f'"{einheit_id}", '\
                  f'{shelf_proposed}, '\
                  f'{shelf_selected}, '\
                  f'{dim_1}, '\
                  f'{dim_2}, '\
                  f'{dim_3}, '\
                  f'{weight_g})'
    print(sql_cmd)
    cursor.execute(sql_cmd)
    mydb.commit()
    cursor.close()

    parcels_imported_count += 1

  html_imported_parcels = "<h1>DONE reset DB and importing parcels from Excel upload</h1><br>"
  html_imported_parcels += f"TOTAL \t({parcel_count}) parcels found in Excel file<br>"
  html_imported_parcels += f"SUCCESS \t({parcels_imported_count}) have been imported<br>"

  import_parcels_string = f"Reset DB and imported parcels from Excel Sheet. Of a total {parcel_count} parcels succesfully imported {parcels_imported_count}."

  return html_imported_parcels, import_parcels_string

def count_parcels():
  global SHELF_COLLECTED
  no_parcels_total        = db_count_entries('parcels')
  no_parcels_tobeassigned = db_count_entries_where_and('parcels', 'shelf_selected', '0', 'shelf_proposed', '0')
  no_parcels_tobesorted   = db_count_entries_where_and_not('parcels', 'shelf_selected', '0', 'shelf_proposed', '0')
  no_parcels_sorted       = db_count_entries_where_not_and_not('parcels', 'shelf_selected', '0', 'shelf_proposed', str(SHELF_COLLECTED))
  no_parcels_collected    = db_count_entries_where_and('parcels', 'shelf_selected', str(SHELF_COLLECTED), 'shelf_proposed', str(SHELF_COLLECTED))
  no_parcels_einheit0     = db_count_entries_where_or('parcels', 'einheit_id', '0', 'einheit_id', 'nan')
  return no_parcels_total, no_parcels_tobeassigned, no_parcels_tobesorted, no_parcels_sorted, no_parcels_collected, no_parcels_einheit0

def test_shelf_no_valid(shelf_no):
  global SHELF_1_LIST, SHELF_2_LIST, SHELF_3_LIST
  list_all_shelves = chain(SHELF_1_LIST, SHELF_2_LIST, SHELF_3_LIST)
  if not int(shelf_no) in list_all_shelves:
    return f'<b>ERROR:</b> Unknown shelf! ({shelf_no})'

def empty_parcels_in_shelf(shelf_no):
  global SHELF_NIRVANA
  results = db_select_from_table_where('parcels', 'shelf_selected', shelf_no)

  for res in results:
    parcel_id = res[0]
    # Set the shelf_proposed and shelf_selected to 40000 to mark as "collected but not checked-out"
    db_update_column_for_record_where_column_has_value('parcels', 'shelf_proposed', SHELF_NIRVANA, 'parcel_id', f'{parcel_id}')
    db_update_column_for_record_where_column_has_value('parcels', 'shelf_selected', SHELF_NIRVANA, 'parcel_id', f'{parcel_id}')

# delete duplicates of parcels
def delete_duplicates_parcel(parcel_id):
  count = db_count_entries_where("parcels", "parcel_id", parcel_id)
  db_delete_from_table_where('parcels', 'parcel_id', parcel_id)

  html = f"Total {count} Duplikate von Paket {parcel_id} gelöscht.<br>Vergiss nicht das Paket neu zu erfassen!"
  return html

def get_duplicates_parcel_id():
  ret = db_get_duplicates("parcels", "parcel_id")