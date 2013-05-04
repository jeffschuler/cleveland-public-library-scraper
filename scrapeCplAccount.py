#!/usr/bin/python

import urllib, string, re, cgi, datetime, time, md5, sqlite, pickle

SQLITE_DB_FILE = '/usr/local/www/cpl_account_info/cpl_account_info2.sqlite'

# Get our account number and PIN from a JSON conf file
import json
conf_file = open('cpl_conf.json')
conf_data = json.load(conf_file)
cplAcctNumStr = conf_data["account_id"]
cplPinNumStr = conf_data["pin"]

ACCOUNT_ID = conf_data["account_id"]
ACCOUNT_PIN = conf_data["pin"]
ACCOUNT_HASH = conf_data["hash"]

#======================

def db_connect():
    conn = sqlite.connect(SQLITE_DB_FILE)
    return conn

#def db_close(cursor):
#    cursor.close()

#======================

def db_create_table_accounts():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DROP TABLE accounts;')
    cur.execute('CREATE TABLE accounts (hash_hex VARCHAR(32), account_id VARCHAR(255), account_pin VARCHAR(255));')
    conn.commit()

def db_create_table_cache():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute('DROP TABLE cache;')
    cur.execute('CREATE TABLE cache (hash_hex VARCHAR(32), checkouts text, holds_available text, holds_waiting text, updated_datetime timestamp);')
    conn.commit()

def add_accounts():
    add_account(ACCOUNT_ID, ACCOUNT_PIN)

def db_create_dbs():
    db_create_table_accounts()
    db_create_table_cache()
    add_accounts()

#======================

"""
from scrapeCplAccount import *
db_show_all_accounts()
db_delete_all_accounts()
db_show_all_accounts()
"""

def db_lookup_account_from_hash(hash_hex):
    conn = db_connect()
    cur = conn.cursor()
    t = (hash_hex,)
    cur.execute("""SELECT account_id, account_pin FROM accounts WHERE hash_hex = %s;""", t)
    row = cur.fetchone()
    if (row):
        account_id, account_pin = row
        return {'hash_hex': hash_hex, 'account_id': account_id, 'account_pin': account_pin}
    else:
        return None

def db_lookup_account_from_account_id(account_id):
    conn = db_connect()
    cur = conn.cursor()
    t = (account_id,)
    cur.execute("""SELECT hash_hex, account_pin FROM accounts WHERE account_id = %s;""", t)
    row = cur.fetchone()
    if (row):
        hash_hex, account_pin = row
        return {'hash_hex': hash_hex, 'account_id': account_id, 'account_pin': account_pin}
    else:
        return None

def db_insert_account(hash_hex, account_id, account_pin):
    conn = db_connect()
    cur = conn.cursor()
    t = (hash_hex, account_id, account_pin,)
    cur.execute("""INSERT INTO accounts (hash_hex, account_id, account_pin) VALUES (%s,%s,%s);""", t)
    conn.commit()

def db_show_all_accounts():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""SELECT hash_hex, account_id, account_pin FROM accounts;""")
    print cur.fetchall()

def db_delete_account_by_hash(hash_hex):
    conn = db_connect()
    cur = conn.cursor()
    t = (hash_hex,)
    cur.execute("""DELETE FROM accounts WHERE hash_hex = %s;""", t)
    conn.commit()

def db_delete_account_by_account_id(account_id):
    conn = db_connect()
    cur = conn.cursor()
    t = (account_id,)
    cur.execute("""DELETE FROM accounts WHERE account_id = %s;""", t)
    conn.commit()

def db_delete_all_accounts():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""DELETE FROM accounts;""")
    conn.commit()

#======================

def db_cache_get(hash_hex, expired_limit_seconds=0):
    """ age_limit in seconds """
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""SELECT checkouts, updated_datetime FROM cache WHERE hash_hex = %s;""", (hash_hex,))
    row = cur.fetchone()
    if row:
        expired = False
        if (expired_limit_seconds != 0):
            timedelta_limit = datetime.timedelta(seconds=expired_limit_seconds)
            test = '2010-07-21T04:44:23.300016'
            updated_datetime_str = row[1]
            updated_datetime_str = updated_datetime_str[0:19]
            updated_time = time.strptime(updated_datetime_str, "%Y-%m-%dT%H:%M:%S")
            updated_datetime = datetime.datetime(updated_time[0],updated_time[1],updated_time[2],updated_time[3],updated_time[4],updated_time[5],updated_time[6])
            if ((datetime.datetime.now() - updated_datetime) >= timedelta_limit):
                expired = True
        if (not expired):
            return pickle.loads(row[0])
    return None

def db_cache_get_new(hash_hex, expired_limit_seconds=0):
    """ age_limit in seconds """
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""SELECT checkouts, holds_available, holds_waiting, updated_datetime FROM cache WHERE hash_hex = %s;""", (hash_hex,))
    row = cur.fetchone()
    if row:
        expired = False
        if (expired_limit_seconds != 0):
            timedelta_limit = datetime.timedelta(seconds=expired_limit_seconds)
            test = '2010-07-21T04:44:23.300016'
            updated_datetime_str = row[3]
            updated_datetime_str = updated_datetime_str[0:19]
            updated_time = time.strptime(updated_datetime_str, "%Y-%m-%dT%H:%M:%S")
            updated_datetime = datetime.datetime(updated_time[0],updated_time[1],updated_time[2],updated_time[3],updated_time[4],updated_time[5],updated_time[6])
            if ((datetime.datetime.now() - updated_datetime) >= timedelta_limit):
                expired = True
        if (not expired):
            cache_full = [pickle.loads(row[0]), pickle.loads(row[1]), pickle.loads(row[2])]
            return cache_full
    return None

def db_cache_set_new(hash_hex, cache_full):
    conn = db_connect()
    cur = conn.cursor()
    clear_cache_for_account(hash_hex)
    updated_datetime = datetime.datetime.now()
    items_checked_out_s = pickle.dumps(cache_full[0])
    items_on_hold_available_s = pickle.dumps(cache_full[1])
    items_on_hold_waiting_s = pickle.dumps(cache_full[2])
    t = (hash_hex, items_checked_out_s, items_on_hold_available_s, items_on_hold_waiting_s, updated_datetime.isoformat())
    cur.execute("""INSERT INTO cache (hash_hex, checkouts, holds_available, holds_waiting, updated_datetime) VALUES (%s,%s,%s,%s,%s);""", t)
    conn.commit()

def db_cache_set(hash_hex, checkouts):
    conn = db_connect()
    cur = conn.cursor()
    clear_cache_for_account(hash_hex)
    updated_datetime = datetime.datetime.now()
    checkouts_serialized = pickle.dumps(checkouts)
    t = (hash_hex, checkouts_serialized, updated_datetime.isoformat())
    cur.execute("""INSERT INTO cache (hash_hex, checkouts, updated_datetime) VALUES (%s,%s,%s);""", t)
    conn.commit()

def clear_cache_for_account(hash_hex):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""DELETE FROM cache WHERE hash_hex = %s;""", (hash_hex,))
    conn.commit()

def clear_all_cache():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""DELETE FROM cache;""")
    conn.commit()

"""
from scrapeCplAccount import *
db_show_all_cache()
account_hash='ed6697452c0fedd60126c01c5f917562'
lib_account = db_lookup_account_from_hash(account_hash)
libAcctInfoHtml = clean_account_page_html(get_raw_acct_html(lib_account['account_id'], lib_account['account_pin']))
checkedOutItems = get_checked_out_items_array(libAcctInfoHtml)
db_cache_set(account_hash, checkedOutItems)

from scrapeCplAccount import *
db_show_all_cache()
account_hash='ed6697452c0fedd60126c01c5f917562'
db_cache_get(account_hash)
db_cache_get(account_hash,1)
"""

def db_show_all_cache():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""SELECT * FROM cache;""")
    print cur.fetchall()

#======================

"""
from scrapeCplAccount import *

ACCOUNT_HASH = ''

db_delete_all_accounts()
add_accounts()
db_lookup_account_from_hash(ACCOUNT_HASH)
db_show_all_accounts()
"""

def calc_account_hash(account_id, account_pin):
    m = md5.new(account_id + account_pin)
    #hash_bin = m.digest()
    return m.hexdigest()

def add_account(account_id, account_pin):
    hash_hex = calc_account_hash(account_id, account_pin)
    db_insert_account(hash_hex, account_id, account_pin)
    return hash_hex

#======================

def get_raw_acct_html(account_id, account_pin):
    """ Grab the html from the account page """
    account_page_url = 'http://search1.clevnet.org/web2/tramp2.exe/log_in?setting_key=CLEVNET&login=patron&begin=t&login_pin_required=t&screen=myaccount.html&userid='+account_id+'&pin='+account_pin
    return urllib.urlopen(account_page_url).read()

def clean_account_page_html(account_page_source):
    """ Strip out a lot of stuff we don't need from the account page HTML """
    account_page_source = re.sub("[\t\n\r]", "", account_page_source)
    account_page_source = re.sub(",23:59", "", account_page_source) #time in date due
    account_page_source = re.sub("Y</b>", "*_", account_page_source)        #overdue date due
    account_page_source = re.sub("</b>", "", account_page_source)
    account_page_source = re.sub("</*strong>", "", account_page_source)
    account_page_source = re.sub("&nbsp;", " ", account_page_source)
    account_page_source = re.sub("\[sound recording\]", "", account_page_source)
    account_page_source = re.sub("\[videorecording\]", "", account_page_source)
    account_page_source = re.sub("\(Motion picture\)", "", account_page_source)
    #account_page_source = re.sub("([0-9]+)/([0-9]+)/([0-9]+),([0-9]+):([0-9]+)", "
    return account_page_source

#======================

def get_checked_out_items_array(libAcctInfoHtml):
    """ Get array of checked-out items from the [cleaned-up] account page source """
    checkedOutStart = string.find(libAcctInfoHtml, 'Renewal Information')
    checkedOutStop = string.find(libAcctInfoHtml, 'Renew Selected Items', checkedOutStart-1)
    checkedOutItems = []
    if ((checkedOutStart >= 0) and (checkedOutStop >= 0)):
        libAcctCheckedOutHtml = (libAcctInfoHtml[checkedOutStart:checkedOutStop])

        libAcctCheckedOutHtml = re.sub(" \[sound recording\]", "", libAcctCheckedOutHtml)
        libAcctCheckedOutHtml = re.sub(" \([Mm]usical group\)", "", libAcctCheckedOutHtml)

        checkedOutMatches = re.findall("<TD.*?>(.*?)</td>", libAcctCheckedOutHtml)
        i = 0
        for tableItem in checkedOutMatches:
                if ((i % 10) == 0):
                    checkedOutItems.append({'title' : checkedOutMatches[i-9], 'author' : checkedOutMatches[i-8], 'media' : checkedOutMatches[i-7], 'dateDue' : checkedOutMatches[i-5]})
                i += 1
        for libItem in checkedOutItems:
            for k,v in libItem.iteritems():
                libItem[k] = string.rstrip(v)
    return checkedOutItems

"""
ACCOUNT_HASH = ''

from scrapeCplAccount import *

lib_account = db_lookup_account_from_hash(ACCOUNT_HASH)
account_info_html = get_cleaned_acct_html_sample()
#account_info_html = clean_account_page_html(get_raw_acct_html(lib_account['account_id'], lib_account['account_pin']))
items_checked_out = get_checked_out_items_array(account_info_html)
items_on_hold_available, items_on_hold_waiting = get_on_hold_items_array(account_info_html)
items_checked_out
items_on_hold_available
items_on_hold_waiting
render_holds_as_html_list(items_on_hold_available, items_on_hold_waiting)
"""

def get_on_hold_items_array(libAcctInfoHtml):
    """ Get array of on-hold items from the [cleaned-up] account page source """
    onHoldStart = string.find(libAcctInfoHtml, 'Available')
    onHoldStop = string.find(libAcctInfoHtml, 'request2', onHoldStart-1)
    onHoldAvailableItems = []
    onHoldWaitingItems = []
    if ((onHoldStart >= 0) and (onHoldStop >= 0)):
        libAcctOnHoldHtml = (libAcctInfoHtml[onHoldStart: onHoldStop])

        libAcctOnHoldHtml = re.sub("<TD class=\"defaultstyle\" align=\"left\"><input type=\"checkbox\"", "", libAcctOnHoldHtml)
        libAcctOnHoldHtml = re.sub("<b><center><font color=red>", "&nbsp;", libAcctOnHoldHtml)
        libAcctOnHoldHtml = re.sub("<b>", "", libAcctOnHoldHtml)
        libAcctOnHoldHtml = re.sub("<font.*?>", "", libAcctOnHoldHtml)
        libAcctOnHoldHtml = re.sub("</font>", "", libAcctOnHoldHtml)
        libAcctOnHoldHtml = re.sub("<center>", "", libAcctOnHoldHtml)

        onHoldTableFields = re.findall("<TD.*?>(.*?)</td>", libAcctOnHoldHtml)
        onHoldItems = []
        for i in range(0, len(onHoldTableFields), 6):
            onHoldItems.append({
                'title' : onHoldTableFields[i-6],
                'author' : onHoldTableFields[i-5],
                'pickup_location' : onHoldTableFields[i-4],
                'available' : onHoldTableFields[i-3],
                'position_in_queue' : onHoldTableFields[i-1]
                })
        for libItem in onHoldItems:
            for k,v in libItem.iteritems():
                libItem[k] = re.sub("\.$", "", v) #strip trailing periods
                libItem[k] = string.rstrip(v)
            libItem['pickup_location'] = get_branch_link(libItem['pickup_location'])
            if (libItem['available'] == 'Y'):
                onHoldAvailableItems.append(libItem)
            else:
                onHoldWaitingItems.append(libItem)
    return onHoldAvailableItems, onHoldWaitingItems

#======================

#def render_checkouts_as_html_table(checkedOutItems):
#    """ output checkouts as an HTML table (with h2 title) """
#    output = ''
#    output += '<h2>Checked-Out (%d)</h2>' % len(checkedOutItems)
#    output += '<table class="sortable" id="checked_out">'
#    output += '<tr><th>Title</th><th>Author/Composer</th><th>Media</th><th>Date Due</th></tr>'
#    k = 0
#    fieldNum = 0
#    for libItem in checkedOutItems:
#        for info in libItem:
#            fieldNum = fieldNum + 1
#            if (k % 2 == 0):
#                output += '<td class="tdLight">' + info + '</td>'
#            else:
#                output += '<td>' + info + '</td>'
#        output += '</tr>'
#        k = k + 1
#    output += '</table>'
#    return output

def render_checkouts_as_html_list(checkedOutItems):
    """ output checkouts as an HTML list """
    output = ''
    output += '<p class="caption">Checked-out: (%d)</p>' % len(checkedOutItems)
    output += '<ul class="checkouts">'
    k = 0
    for libItem in checkedOutItems:
        if (k % 2 == 0):
            rowStripe = 'odd'
        else:
            rowStripe = 'even'
        output += '<li class="libitem ' + rowStripe + '">'
        output += '<div class="title">' + libItem['title'] + '</div>'
        output += '<div class="author">' + libItem['author'] + '</div>'
        output += '</li>'
        k = k + 1
    output += '</ul>'
    return output

#def render_holds_as_html_table(onHoldAvailableItems, onHoldWaitingItems):
#    """ output holds as an HTML table (with h2 title) """
#    output = ''
#    output += '<h2>On-Hold::Available (%d)</h2>' % len(onHoldAvailableItems)
#    output += '<table class="sortable" id="on_hold_available">'
#    output += '<tr><th>Title</th><th>Author/Composer</th><th>Library</th></tr>'
#    k = 0
#    for libItem in onHoldAvailableItems:
#        output += '<tr>'
#        for info in libItem[0:3]:
#            if (k % 2 == 0):
#                output += '<td class="tdLight">' + info + '</td>'
#            else:
#                output += '<td>' + info + '</td>'
#        output += '</tr>'
#        k = k + 1
#    output += '</table>'
#
#    output += '<br />'
#    output += '<h2>On-Hold::Waiting (%d)</h2>' % len(onHoldWaitingItems)
#
#    output += '<table class="sortable" id="on_hold_waiting">'
#    output += '<tr><th>Title</th><th>Author/Composer</th><th>Library</th><th># in Queue</th></tr>'
#    k = 0
#    for libItem in onHoldWaitingItems:
#        output += '<tr>'
#        for info in (libItem[0], libItem[1], libItem[2], libItem[4]):
#            if (k % 2 == 0):
#                output += '<td class="tdLight">' + info + '</td>'
#            else:
#                output += '<td>' + info + '</td>'
#        output += '</tr>'
#        k = k + 1
#    output += '</table>'
#    return output

def render_holds_as_html_list(onHoldAvailableItems, onHoldWaitingItems):
    """ output holds as an HTML list """
    output = ''

    output += '<p class="caption">On Hold - Available: (%d) :</p>' % len(onHoldAvailableItems)
    output += '<ul class="holds available">'
    k = 0
    for libItem in onHoldAvailableItems:
        if (k % 2 == 0):
            rowStripe = 'odd'
        else:
            rowStripe = 'even'
        output += '<li class="libitem ' + rowStripe + '">'
        output += '<div class="title">' + libItem['title'] + '</div>'
        output += '<div class="author">' + libItem['author'] + '</div>'
        output += '</li>'
        k = k + 1
    output += '</ul>'

    output += '<p class="caption">On Hold - Waiting: (%d) :</p>' % len(onHoldWaitingItems)
    output += '<ul class="holds waiting">'
    k = 0
    for libItem in onHoldWaitingItems:
        if (k % 2 == 0):
            rowStripe = 'odd'
        else:
            rowStripe = 'even'
        output += '<li class="libitem ' + rowStripe + '">'
        output += '<div class="title">' + libItem['title'] + '</div>'
        output += '<div class="author">' + libItem['author'] + '</div>'
        output += '</li>'
        k = k + 1
    output += '</ul>'

    return output

#def render_all_as_html(checkedOutItems, onHoldAvailableItems, onHoldWaitingItems):
#    """ output checkouts and holds in HTML """
#    render_checkouts_as_html_list(checkedOutItems)
#    render_holds_as_html_list(onHoldAvailableItems, onHoldWaitingItems)

#def print_calendar(checkedOutItems, account_id):
#""" Print VCal event for each due date """
#    output += 'BEGIN:VCALENDAR'
#    output += 'PRODID:-//jeffschuler.net//My CPL//EN'
#    output += 'VERSION:2.0'
#    output += 'CALSCALE:GREGORIAN'
#
#    now = datetime.datetime.utcnow()
#    nowIcalDateTimeStamp=now.strftime("%Y%m%dT%H%M%SZ")
#
#    k = 0
#    fieldNum = 0
#    for libItem in checkedOutItems:
#
#        itemName = libItem[0]
#        dueDateTimeString = time.strptime(libItem[3], "%m/%d/%Y")
#        dueIcalDateStamp = time.strftime("%Y%m%d", dueDateTimeString)
#
#        output += 'BEGIN:VTODO'
#        output += 'SEQUENCE:0'
#        uidPropStr = nowIcalDateTimeStamp+'_%d'%k+'@jeffschuler.net'
#        output += 'UID:'+uidPropStr
#        dtstampPropStr = nowIcalDateTimeStamp
#        output += 'DTSTAMP:'+dtstampPropStr
#        duePropStr = dueIcalDateStamp
#        output += 'DUE:'+duePropStr
#        output += 'STATUS:NEEDS-ACTION'
#        output += 'SUMMARY:CPL item due: "'+itemName+'"'
#        output += 'DESCRIPTION:CPL item due: "'+itemName+'"'
#        output += 'URL:http://myaccount.clevnet.org/htbin/netnotice/'+account_id
#        output += 'END:VTODO'
#        k = k + 1
#
#    output += 'END:VCALENDAR'

#======================

"""
from scrapeCplAccount import *
get_branch_link('CPL-CARNW')
"""

def get_branch_link(branch_str):
    branch_directory = {
        'CPL-MAIN'    : '<a href="http://www.cpl.org/BranchLocations/MainLibrary.aspx">Main Library</a>',
        'CPL-LEND'    : '<a href="http://www.cpl.org/BranchLocations/MainLibrary.aspx">Main Library</a>',
        'CPL-AV'      : '<a href="http://www.cpl.org/BranchLocations/MainLibrary.aspx">Main Library A/V</a>',
        'CPL-ADDISN'  : '<a href="http://www.cpl.org/BranchLocations/Branches/Addison.aspx">Addison</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Broadway.aspx">Broadway</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Brooklyn.aspx">Brooklyn</a>',
        'CPL-CARNW'   : '<a href="http://www.cpl.org/BranchLocations/Branches/CarnegieWest.aspx">Carnegie West</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Collinwood.aspx">Collinwood</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/East131stStreet.aspx">East 131st Street</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Eastman.aspx">Eastman</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Fleet.aspx">Fleet</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Fulton.aspx">Fulton</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/GardenValley.aspx">Garden Valley</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Glenville.aspx">Glenville</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/HarvardLee.aspx">Harvard-Lee</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Hough.aspx">Hough</a>',
        'CPL-JEFF'    : '<a href="http://www.cpl.org/BranchLocations/Branches/Jefferson.aspx">Jefferson</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/LangstonHughes.aspx">Langston Hughes</a>',
        'CPL-LORAIN'  : '<a href="http://www.cpl.org/BranchLocations/Branches/Lorain.aspx">Lorain</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/MartinLKingJr.aspx">Martin L. King, Jr.</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/MemorialNottingham.aspx">Memorial-Nottingham</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/MtPleasant.aspx">Mt. Pleasant</a>',
#                      : '<a href="http://www.cpl.org/TheLibrary/OhioLibraryfortheBlindandPhysicallyDisabled.aspx">Ohio Library for the Blind & Physically Disabled</a>',
#                      : '<a href="http://www.cpl.org/TheLibrary/SubjectsCollections/PublicAdministrationLibrary.aspx">Public Administration Library</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Rice.aspx">Rice</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Rockport.aspx">Rockport</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/South.aspx">South</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/SouthBrooklyn.aspx">South Brooklyn</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Sterling.aspx">Sterling</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Union.aspx">Union</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Walz.aspx">Walz</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/WestPark.aspx">West Park</a>',
#                      : '<a href="http://www.cpl.org/BranchLocations/Branches/Woodland.aspx">Woodland</a>',
        'CH-COV'      : '<a href="http://www.heightslibrary.org/hours.php#cov">Cleve Hts: Coventry</a>',
        'CH-MAIN'     : '<a href="http://www.cpl.org/BranchLocations/MainLibrary.aspx">Cleve Hts: Main</a>',
    }
    if (branch_directory.has_key(branch_str)):
        return branch_directory[branch_str]
    else:
        return branch_str

#======================


#### MAIN ####

"""
ACCOUNT_HASH = ''

from scrapeCplAccount import *

hash_hex = ACCOUNT_HASH
go_render(hash_hex)

lib_account = db_lookup_account_from_hash(hash_hex)
account_info_html = get_cleaned_acct_html_sample()
#account_info_html = clean_account_page_html(get_raw_acct_html(lib_account['account_id'], lib_account['account_pin']))
items_checked_out = get_checked_out_items_array(account_info_html)
items_on_hold_available, items_on_hold_waiting = get_on_hold_items_array(account_info_html)
items_on_hold_waiting

checkedOutItems = get_checked_out_items_array(libAcctInfoHtml)
render_checkouts_as_html_list(checkedOutItems)

"""

def go_render_checkouts_html(account_hash):
    checkedOutItems = db_cache_get(account_hash, 10800)
    if not checkedOutItems:
        lib_account = db_lookup_account_from_hash(account_hash)
        libAcctInfoHtml = clean_account_page_html(get_raw_acct_html(lib_account['account_id'], lib_account['account_pin']))
        checkedOutItems = get_checked_out_items_array(libAcctInfoHtml)
        db_cache_set(account_hash, checkedOutItems)
    return render_checkouts_as_html_list(checkedOutItems)

def go_get_all(account_hash):
    cache_full = db_cache_get_new(account_hash, 10800)
    if cache_full:
        [items_checked_out, items_on_hold_available, items_on_hold_waiting] = cache_full
    else:
        lib_account = db_lookup_account_from_hash(account_hash)
        libAcctInfoHtml = clean_account_page_html(get_raw_acct_html(lib_account['account_id'], lib_account['account_pin']))
        items_checked_out = get_checked_out_items_array(libAcctInfoHtml)
        items_on_hold_available, items_on_hold_waiting = get_on_hold_items_array(libAcctInfoHtml)
        cache_full = [items_checked_out, items_on_hold_available, items_on_hold_waiting]
        db_cache_set_new(account_hash, cache_full)
    return cache_full

def go_render(account_hash):
    [items_checked_out, items_on_hold_available, items_on_hold_waiting] = go_get_all(account_hash)
    output = render_checkouts_as_html_list(items_checked_out)
    output += render_holds_as_html_list(items_on_hold_available, items_on_hold_waiting)
    return output

def go_render_checkouts_html_jenita(account_hash):
    libAcctInfoHtml = clean_account_page_html(get_raw_acct_html(ACCOUNT_ID, ACCOUNT_PIN))
    checkedOutItems = get_checked_out_items_array()
    return render_checkouts_as_html_list(checkedOutItems)

def go_render_checkouts_html_sample(account_hash):
    checkedOutItems = get_checked_out_items_array_sample()
    return render_checkouts_as_html_list(checkedOutItems)

#print go_render_checkouts_html(ACCOUNT_ID, ACCOUNT_PIN)

#onHoldAvailableItems, onHoldWaitingItems = get_on_hold_items(libAcctInfoHtml)

#display_lib_acct_info(checkedOutItems, onHoldAvailableItems, onHoldWaitingItems)
#print_calendar(checkedOutItems)


def get_checked_out_items_array_sample():
    return [{'media': 'BOOK', 'author': 'Karre, Andrew.', 'dateDue': '7/24/2010', 'title': 'The complete guide to home wiring : including information on home electronics & wireless technology'}, {'media': 'BOOK', 'author': 'Gibson, William, 1948-', 'dateDue': '8/2/2010', 'title': 'Neuromancer'}, {'media': 'BOOK', 'author': 'Frederick, Gail Rahn.', 'dateDue': '7/17/2010', 'title': 'Beginning smartphone web development : building JavaScript, CSS, HTML and Ajax-based applications for iPhone, Android, Palm Pre, Blackberry, Windows Mobile and Nokia S60'}, {'media': 'BOOK', 'author': 'Gerber, Michael E.', 'dateDue': '7/24/2010', 'title': "The E-myth revisited : why most small businesses don't work and what to do about it"}, {'media': 'BOOK', 'author': 'Deleuze, Gilles.', 'dateDue': '7/24/2010', 'title': 'What is philosophy?'}, {'media': 'CD', 'author': 'Jordan, Stanley.', 'dateDue': '7/24/2010', 'title': 'State of nature'}, {'media': 'BOOK', 'author': 'Rushforth, Keith.', 'dateDue': '7/24/2010', 'title': 'National Geographic field guide to the trees of North America'}, {'media': 'BOOK', 'author': 'Johnston, Larry.', 'dateDue': '7/24/2010', 'title': 'Wiring : [step-by-step instructions]'}]

def get_cleaned_acct_html_sample():
    return '<HTML><!--Copyright 1996-2003 Sirsi Corporation. All rights reserved. Removal of this notice violates applicable copyright laws.--><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"><!--U_ENG_iFILES/MyAccount.html--><META HTTP-EQUIV="REFRESH" CONTENT="600 ;URL=/web2/tramp2.exe/log_out/A05l3fe7.000"><HEAD><style type="text/css">a:link, a:active {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}a:visited {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}a:hover {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}body {margin:-10px 0px 0px -10px;background-color: #FFFFFF;color: #000000;}html body {margin: 10px 10px 10px 10px;background-color: #FFFFFF;color: #000000;}p, td {font-family: Verdana, Helvetica, Arial, sans-serif;}th {font-family: Verdana, Helvetica, Arial, sans-serif;text-align: left;vertical-align: top;}label {font-family: Verdana, Helvetica, Arial, sans-serif;font-weight: bold;}legend {font-family: Verdana, Helvetica, Arial, sans-serif;font-weight: bold;}fieldset {border-style: none;border-width: 0px;}form {margin: 0px 0px 0px 0px;}ul {  margin-left: 0px;}.bibinfo {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #FFFFFF;color: #000000;border-width: 0px;border-style: none;margin: 5px 5px 5px 5px;text-align: left;width: 100%;}.bibinfo2 {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #FFFFFF;color: #000000;margin: 10px 30px 10px 30px;}.summary {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;border-width: 1px;border-style: solid;padding: 5px 5px 5px 5px;margin: 10px 5px 5px 10px;}.rootbarcell {font-family: Verdana, Helvetica, Arial, sans-serif;text-align: center;font-size: 16px;color: #333367;background-color: #7ba596;letter-spacing: 0px;margin: 5px 5px 5px 5px;} /* Use these rootbar declaration for CSS2 browsers */a:link.blastoff, a:visited.blastoff, a:active.blastoff {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold; color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}a:hover.blastoff {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold; color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;} a:link.rootbar, a:visited.rootbar, a:active.rootbar {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;font-weight: normal;color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}a:hover.rootbar {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;font-weight: normal;color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}.defaultstyle {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;vertical-align: top;}.bannerstyle {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #333367;color: #ffffff;vertical-align: middle;}th.defaultstyle {white-space: nowrap;text-align: right;}.enrichheader, .enrichheader a {background-color: #DBE9DF; color: #333367; font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;padding: 5px 0px 0px 0px;}.enrichsubheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;}.enrichcontent {background-color: #DBE9DF; color: #000000; font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;vertical-align: top;padding: 0px 0px 5px 5px;} .enrichmentservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 10px;color: #000000;border-width: 1px;border-style: solid;text-align: left;} .enrichtagline {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 10px;font-weight: normal;background-color: #FFFFFF;color: #888888;}.footer {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: normal; }.gatewaystyle, .gatewaystyle a:link, .gatewaystyle a:visited, .gatewaystyle a:active, .gatewaystyle a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #333367;color: #ffffff;font-weight: bold;margin: 0px 0px 0px 0px;}.bold, .bold a:link, .bold a:visited, .bold a:active, .bold a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 14px;font-weight: bold;background-color: #DBE9DF;color: #000000;margin: 0px 0px 0px 0px;}.bold2, .bold a:link, .bold a:visited, .bold a:active, .bold a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 14px;font-weight: bold;background-color: #ffffff;color: #000000;margin: 0px 0px 0px 0px;}.header {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 14px;font-weight: bold;letter-spacing: 2px; background-color: #7ba596;color: #333367;}div.header {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;font-weight: bold;letter-spacing: 2px; background-color: #333367;color: #FFFFFF;padding: 3px 3px 3px 3px;}.holdingsheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;font-weight: bold;background-color: #FFFFFF;color: #333367;}.holdingslist {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;}.holdingslisthigh {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #dbe9df;color: #000000;}th.holdingslist {white-space: nowrap;text-align: right;vertical-align: top;}.indented {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #FFFFFF;color: #000000;margin-left: 10px;vertical-align: top;}.itemlisting, label.itemlisting {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 13px;background-color: #FFFFFF;color: #000000;vertical-align: top;font-weight: normal;}.itemlisting2, label.itemlisting2 {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;background-color: #EFEFEF;color: #000000;vertical-align: top;font-weight: normal;}input.itemdetails {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;background-color: #0099CC;color: #FFFFFF;width: 75px;margin: 5px 0px 5px 0px;display: block;}td.itemservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;}div.itemservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;text-align: left;border-width: 1px;border-style: solid;padding: 7px 7px 7px 7px;margin: 0px 0px 0px 0px;}div.itemservices a:link, div.itemservices a:visited, div.itemservices a:active {display: block;margin: 3px 0px 3px 0px;}div.itemservices a:hover {background-color: #DBE9DF;color: #000000;display: block;margin: 3px 0px 3px 0px;}div.options {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;border-width: 1px;border-style: solid;padding: 5px 5px 5px 5px;margin: 10px 5px 5px 10px;}.overdue, .error {color: #CC0000;}.pagecontainer {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;color: #000000;border-width: 2px;border-style: solid;width: 95%;}.pagecontainer3pg {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;color: #000000;border-width: 1px;border-style: solid;width: 95%;}.rsvholdings {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: bold;background-color: #EEEEEE;color: #000000;} .searchheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px; background-color: #7ba596;color: #333367;padding: 3px 0px 3px 3px;width: 100%;}.searchcontent {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;padding: 3px 3px 3px 3px;vertical-align: middle;white-space: nowrap;}.searchcontent2 {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;font-weight: bold;padding: 3px 3px 3px 3px;vertical-align: middle;white-space: nowrap;}table.searchcontent {width: 99%;}th.searchcontent {text-align: right;width: 30%;}.searchservices {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #DBE9DF;color: #000000;border-width: 1px;border-style: solid;}input.searchbutton {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 14px;font-weight: bold;background-color: #333367;color: #FFFFFF;vertical-align: middle;margin: 5px;}input.searchbuttonsmall {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #333367;color: #FFFFFF;vertical-align: middle;margin: 5px;}a:link.searchlinks, a:active.searchlinks, a:visited.searchlinks {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;text-decoration: none;background-color: #EEEEEE;color: #333367;}a:hover.searchlinks {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;text-decoration: underline;background-color: #EEEEEE;color: #000000;}.subheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #EEEEEE;color: #000000;margin-left: 2px;}.searchsum {color: #000000;font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;text-align: center;background-color: #DBE9DF;}.small {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: normal; }.titlebar {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 18px;font-weight: bold;letter-spacing: 3px;background-color: #7ba596;color: #333367;text-align: center;margin: 0px;}.vreference {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #333367;color: #FFFFFF;}.vreference input {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #FFFFFF;color: #333367;margin: 3px 3px 3px 3px;}.vreference textarea {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #FFFFFF;color: #333367;width: 125px;height: 50px;margin: 3px 3px 3px 3px;}.unformatted {font-family: "Courier New", Courier, monospace; font-size: 12px;font-weight: normal; vertical-align: top;}.viewmarcheader, .viewmarcheader a {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;background-color: #FFFFFF;color: #996600;}.viewmarctags {   vertical-align: top;   font-family: Verdana, Arial, Helvetica, sans-serif;    font-size: 10px;   background-color: #FFFFFF;   color: #000000; }th.viewmarctags {white-space: nowrap;text-align: right;vertical-align: top;}.virtualreference {border-style: none;border-width: 0px;padding: 1px 5px 1px 5px;}.contentholder {padding: 10px 10px 10px 10px;position: relative;}.tabholder {padding: 0px 0px 0px 0px;position: relative;z-index: 2;}.tab {border-style: outset;border-bottom-style: none;border-width: 2px;border-color: #999999;line-height: 150%;text-align: center;padding: 0px 0px 3px 0pxmargin-right: 0px;cursor: pointer;cursor: hand;font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #ffffff;color: #333367; }.panelholder {position: relative;top: -2px;z-index: 1;visibility: visible;display: block;color: #000000;background-color: #FFFFFF;}.panel {position: relative;color: #000000;background-color: #ffffff;border: 2px;border-color: #999999;border-style: outset;top: 0;left: 0;padding: 10px 10px 10px 10px;display: none;}</style><TITLE>Patron Account Information - Web2</title>.<script type="text/javascript" language="JavaScript"><!--function WinOpenQ(){ Queue=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=queue.html","Queue","status,resize,height=350,width=500,menu,scrollbars,resizable"); Queue.focus();}//--></script></head><body><noscript>Your browser does not support JavaScript and this application utilizes JavaScript to build content and provide links to additional information. You should either enable JavaScript in your browser settings or use a browser that supports JavaScript in order to take full advantage of this application.</noscript><a name="top"></a><div class="pagecontainer"><head></head><body text="#ffffff" link="#ffffff" vlink="#ffffff" alink="#ffffff"><table border=0 width=100%><tr><td width=70% align=left><IMG BORDER="0" SRC="/html/CLEVNET/Graphics/banner_clevnet.gif" ALT="CLEVNET"></td><td width=30% align=right colspan=2><a href="/html/CLEVNET/Graphics/link.html"><IMG BORDER="0" SRC="/html/CLEVNET/Graphics/banner_library.gif" ALT="Your Library"></a></td></tr><tr><td align=left bgcolor="#7ba596"><IMG BORDER="0" SRC="/html/CLEVNET/Graphics/banner_title.gif" ALT="Library Catalog"></td><td align=middle bgcolor="#333367"><HTML><!--Copyright 1996-2003 Sirsi Corporation. All rights reserved. Removal of this notice violates applicable copyright laws.--><!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"><!--U_ENG_iFILES/Login.html--><HEAD><style type="text/css">a:link, a:active {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}a:visited {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}a:hover {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: normal;text-decoration: underline;color: #000000;}body {margin:-10px 0px 0px -10px;background-color: #FFFFFF;color: #000000;}html body {margin: 10px 10px 10px 10px;background-color: #FFFFFF;color: #000000;}p, td {font-family: Verdana, Helvetica, Arial, sans-serif;}th {font-family: Verdana, Helvetica, Arial, sans-serif;text-align: left;vertical-align: top;}label {font-family: Verdana, Helvetica, Arial, sans-serif;font-weight: bold;}legend {font-family: Verdana, Helvetica, Arial, sans-serif;font-weight: bold;}fieldset {border-style: none;border-width: 0px;}form {margin: 0px 0px 0px 0px;}ul {  margin-left: 0px;}.bibinfo {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #FFFFFF;color: #000000;border-width: 0px;border-style: none;margin: 5px 5px 5px 5px;text-align: left;width: 100%;}.bibinfo2 {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #FFFFFF;color: #000000;margin: 10px 30px 10px 30px;}.summary {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;border-width: 1px;border-style: solid;padding: 5px 5px 5px 5px;margin: 10px 5px 5px 10px;}.rootbarcell {font-family: Verdana, Helvetica, Arial, sans-serif;text-align: center;font-size: 16px;color: #333367;background-color: #7ba596;letter-spacing: 0px;margin: 5px 5px 5px 5px;} /* Use these rootbar declaration for CSS2 browsers */a:link.blastoff, a:visited.blastoff, a:active.blastoff {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold; color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}a:hover.blastoff {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold; color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;} a:link.rootbar, a:visited.rootbar, a:active.rootbar {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;font-weight: normal;color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}a:hover.rootbar {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;font-weight: normal;color: #333367;background-color: #7ba596;text-decoration: underline;white-space: nowrap;margin: 0px 7px 0px 7px;}.defaultstyle {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;vertical-align: top;}.bannerstyle {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #333367;color: #ffffff;vertical-align: middle;}th.defaultstyle {white-space: nowrap;text-align: right;}.enrichheader, .enrichheader a {background-color: #DBE9DF; color: #333367; font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;padding: 5px 0px 0px 0px;}.enrichsubheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;}.enrichcontent {background-color: #DBE9DF; color: #000000; font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;vertical-align: top;padding: 0px 0px 5px 5px;} .enrichmentservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 10px;color: #000000;border-width: 1px;border-style: solid;text-align: left;} .enrichtagline {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 10px;font-weight: normal;background-color: #FFFFFF;color: #888888;}.footer {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: normal; }.gatewaystyle, .gatewaystyle a:link, .gatewaystyle a:visited, .gatewaystyle a:active, .gatewaystyle a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;background-color: #333367;color: #ffffff;font-weight: bold;margin: 0px 0px 0px 0px;}.bold, .bold a:link, .bold a:visited, .bold a:active, .bold a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 14px;font-weight: bold;background-color: #DBE9DF;color: #000000;margin: 0px 0px 0px 0px;}.bold2, .bold a:link, .bold a:visited, .bold a:active, .bold a:hover {font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 14px;font-weight: bold;background-color: #ffffff;color: #000000;margin: 0px 0px 0px 0px;}.header {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 14px;font-weight: bold;letter-spacing: 2px; background-color: #7ba596;color: #333367;}div.header {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;font-weight: bold;letter-spacing: 2px; background-color: #333367;color: #FFFFFF;padding: 3px 3px 3px 3px;}.holdingsheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;font-weight: bold;background-color: #FFFFFF;color: #333367;}.holdingslist {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;}.holdingslisthigh {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #dbe9df;color: #000000;}th.holdingslist {white-space: nowrap;text-align: right;vertical-align: top;}.indented {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #FFFFFF;color: #000000;margin-left: 10px;vertical-align: top;}.itemlisting, label.itemlisting {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 13px;background-color: #FFFFFF;color: #000000;vertical-align: top;font-weight: normal;}.itemlisting2, label.itemlisting2 {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;background-color: #EFEFEF;color: #000000;vertical-align: top;font-weight: normal;}input.itemdetails {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;background-color: #0099CC;color: #FFFFFF;width: 75px;margin: 5px 0px 5px 0px;display: block;}td.itemservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;}div.itemservices {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;text-align: left;border-width: 1px;border-style: solid;padding: 7px 7px 7px 7px;margin: 0px 0px 0px 0px;}div.itemservices a:link, div.itemservices a:visited, div.itemservices a:active {display: block;margin: 3px 0px 3px 0px;}div.itemservices a:hover {background-color: #DBE9DF;color: #000000;display: block;margin: 3px 0px 3px 0px;}div.options {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 11px;color: #000000;border-width: 1px;border-style: solid;padding: 5px 5px 5px 5px;margin: 10px 5px 5px 10px;}.overdue, .error {color: #CC0000;}.pagecontainer {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;color: #000000;border-width: 2px;border-style: solid;width: 95%;}.pagecontainer3pg {background-color: #FFFFFF;font-family: Verdana, Helvetica, Arial, sans-serif;font-size: 12px;color: #000000;border-width: 1px;border-style: solid;width: 95%;}.rsvholdings {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: bold;background-color: #EEEEEE;color: #000000;} .searchheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px; background-color: #7ba596;color: #333367;padding: 3px 0px 3px 3px;width: 100%;}.searchcontent {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;padding: 3px 3px 3px 3px;vertical-align: middle;white-space: nowrap;}.searchcontent2 {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #ffffff;color: #000000;font-weight: bold;padding: 3px 3px 3px 3px;vertical-align: middle;white-space: nowrap;}table.searchcontent {width: 99%;}th.searchcontent {text-align: right;width: 30%;}.searchservices {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #DBE9DF;color: #000000;border-width: 1px;border-style: solid;}input.searchbutton {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 14px;font-weight: bold;background-color: #333367;color: #FFFFFF;vertical-align: middle;margin: 5px;}input.searchbuttonsmall {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #333367;color: #FFFFFF;vertical-align: middle;margin: 5px;}a:link.searchlinks, a:active.searchlinks, a:visited.searchlinks {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;text-decoration: none;background-color: #EEEEEE;color: #333367;}a:hover.searchlinks {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;text-decoration: underline;background-color: #EEEEEE;color: #000000;}.subheader {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;background-color: #EEEEEE;color: #000000;margin-left: 2px;}.searchsum {color: #000000;font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 11px;text-align: center;background-color: #DBE9DF;}.small {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;font-weight: normal; }.titlebar {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 18px;font-weight: bold;letter-spacing: 3px;background-color: #7ba596;color: #333367;text-align: center;margin: 0px;}.vreference {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #333367;color: #FFFFFF;}.vreference input {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #FFFFFF;color: #333367;margin: 3px 3px 3px 3px;}.vreference textarea {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 10px;text-decoration: none;font-weight: normal;letter-spacing: 0px;background-color: #FFFFFF;color: #333367;width: 125px;height: 50px;margin: 3px 3px 3px 3px;}.unformatted {font-family: "Courier New", Courier, monospace; font-size: 12px;font-weight: normal; vertical-align: top;}.viewmarcheader, .viewmarcheader a {font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;letter-spacing: 2px;background-color: #FFFFFF;color: #996600;}.viewmarctags {   vertical-align: top;   font-family: Verdana, Arial, Helvetica, sans-serif;    font-size: 10px;   background-color: #FFFFFF;   color: #000000; }th.viewmarctags {white-space: nowrap;text-align: right;vertical-align: top;}.virtualreference {border-style: none;border-width: 0px;padding: 1px 5px 1px 5px;}.contentholder {padding: 10px 10px 10px 10px;position: relative;}.tabholder {padding: 0px 0px 0px 0px;position: relative;z-index: 2;}.tab {border-style: outset;border-bottom-style: none;border-width: 2px;border-color: #999999;line-height: 150%;text-align: center;padding: 0px 0px 3px 0pxmargin-right: 0px;cursor: pointer;cursor: hand;font-family: Verdana, Helvetica, Arial, sans-serif; font-size: 12px;font-weight: bold;background-color: #ffffff;color: #333367; }.panelholder {position: relative;top: -2px;z-index: 1;visibility: visible;display: block;color: #000000;background-color: #FFFFFF;}.panel {position: relative;color: #000000;background-color: #ffffff;border: 2px;border-color: #999999;border-style: outset;top: 0;left: 0;padding: 10px 10px 10px 10px;display: none;}</style><TITLE>Login to Web2</title><META HTTP-EQUIV="REFRESH" CONTENT="600 ;URL=/web2/tramp2.exe/log_out/A05l3fe7.000"><script type="text/javascript" language="JavaScript"><!--function WinOpen(){ Help=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=/Help/Help.html#MyAccount","Help","status,resize,height=250,width=500,menu,scrollbars,resizable"); Help.focus();}function WinOpenPIN(){ Help=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=/Help/pin.html","PIN","status,resize,height=300,width=500,menu,scrollbars,resizable"); Help.focus();}function WinOpen2(){ Status=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=/Help/Status.html","Status","status,resize,height=250,width=600,menu,scrollbars,resizable"); Status.focus();}function WinOpen3(){ CLEVNET=open("http://www.clevnet.org/participating_libraries.php","CLEVNET","status,resize,height=550,width=600,menu,scrollbars,resizable"); CLEVNET.focus();}function WinOpen4(){ Renew=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=/Help/Renew.html","Renew","status,resize,height=250,width=600,menu,scrollbars,resizable"); RenewT.focus();}function WinOpen5(){ Hold=open("/web2/tramp2.exe/goto/A05l3fe7.000?screen=/Help/hold_periods.html","Hold","status,resize,height=600,width=600,menu,scrollbars,resizable"); Hold.focus();}function renewall(){if (confirm("Are you sure you want to renew all items?") ){location.href="/web2/tramp2.exe/renew_hasnow/A05l3fe7.000?hasnow=all&screen=MyAccount.html";}else{}}function renew(){var numChecked = 0;var myForm = document.hasnow;for(var index = 0; index < myForm.length; index++){var type = myForm[index].type;if(type == "checkbox"){//alert(type);//alert(myForm[index].value);if(myForm[index].checked){numChecked++;break;}}}if(numChecked == 0){alert("Please select a title to renew.");}}function cancelall(){if (confirm("Are you sure you want to cancel all requests?") ){location.href="/web2/tramp2.exe/cancel_request/A05l3fe7.000?request=all&screen=MyAccount.html";}else{}}function cancel(){var numChecked = 0;var myForm = document.requests;for(var index = 0; index < myForm.length; index++){var type = myForm[index].type;if(type == "checkbox"){//alert(type);//alert(myForm[index].value);if(myForm[index].checked){numChecked++;break;}}}if(numChecked == 0){alert("Please select a title to cancel.");}}//--></script></head><BODY><noscript>Your browser does not support JavaScript and this application utilizes JavaScript to build content and provide links to additional information. You should either enable JavaScript in your browser settings or use a browser that supports JavaScript in order to take full advantage of this application.</noscript><table border=0><!----><tr valign=middle><td align=center><A HREF="/web2/tramp2.exe/log_out/A05l3fe7.000" onClick="javascript:window.close();"><IMG BORDER="0" SRC="/html/CLEVNET/Graphics/LOGOFF.gif" ALT="Log Off"></a></td></tr><!----></table></form></div></body></html><td align=right bgcolor="#333367"><center><a href="/html/CLEVNET/Graphics/link.html"><IMG BORDER="0" SRC="/html/CLEVNET/Graphics/lib_logo.gif" ALT="Local Library Logo"></a></td></tr></table><a name="skipnav"></a><table border="0" width=100% align="center" title=""><tr><td class="bold2" align=center><font size=4>My Account</font></td></tr> <tr><td class="defaultstyle"><table border="0" cellpadding="2" cellspacing="0" width=100%><tr><td class="header">Address/Contact Information</tr><tr><td class="defaultstyle">Schuler, Jeffrey W<br>2167 W 30 St<br>Cleveland OH<br>44113<br><br>Phone:  216-367-2167<br>Email:    jeff@jeffschuler.net<br><br><br><FORM ACTION="/web2/tramp2.exe/goto/A05l3fe7.000" METHOD="POST" ENCTYPE="application/x-www-form-urlencoded"><INPUT TYPE="hidden" NAME="screen" VALUE="PatronEditPIN.html"><INPUT TYPE="submit" NAME="ChangePIN" VALUE="Change Your PIN" class="searchbutton"><br />PINs must be 4-10 characters long.<br />They are case-insensitive, and you can use a combination of letters and numbers.</form><br><tr><td class="header">Account Status Summary</tr><tr>   <td class="indented">You will receive your library notices by: <font color="#333367" size=2><b>EMAIL<br></font>Your account status is:<font color="#333367" size=2><b>OK<br></font>You have <a href="#charges"><b> 8</a> items checked out<br> <br>You have <a href="#bills"> <b>$1.40</a> in fines or fees<br><br></td> </tr></table><br><a name="charges"></a><form action="/web2/tramp2.exe/form/A05l3fe7.000" method="post" ENCTYPE="application/x-www-form-urlencoded">    <table border="2" cellpadding="2" cellspacing="0" width=100%>     <tr>      <td colspan="10" class="header">Checkouts</td></tr>     <tr><tr><td colspan="10" class="subheader"><label>Sort by: </label><form action="/web2/tramp2.exe/form/A05l3fe7.000" name="hasnow" method="post" enctype="application/x-www-form-urlencoded"><select Name="hasnow_sort_field"><OPTION VALUE="sort_date_due">Date Due</option><OPTION VALUE="title">Title</option><OPTION VALUE="author">Author</option></select><input type=hidden name="buttons" value="sort_hasnows=goto screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="sort_hasnows" VALUE="Sort Now"></td></tr><tr>      <td class="subheader" ></td>      <td class="subheader" >Title</td><td class="subheader" >Author</td><td class="subheader" >Item Format</td><td class="subheader" >Barcode Number</td><td class="subheader">Due Date</td><td class="subheader">Amount Owed</td><td class="subheader">From</td><td class="subheader">Times Renewed</td><td class="subheader">Renewal Information</td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009171458830:1"/> </td><TD class="defaultstyle" align="left">The E-myth revisited : why most small businesses don\'t work and what to do about it </td><TD class="defaultstyle" align="left">Gerber, Michael E.</td><TD class="defaultstyle" align="left">BOOK </td><TD class="defaultstyle" align="left">0009171458830 </td><TD class="defaultstyle" align="left">7/24/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-MAIN </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009112458493:1"/> </td><TD class="defaultstyle" align="left">What is philosophy? </td><TD class="defaultstyle" align="left">Deleuze, Gilles.</td><TD class="defaultstyle" align="left">BOOK </td><TD class="defaultstyle" align="left">0009112458493 </td><TD class="defaultstyle" align="left">7/24/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-MAIN </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009207891236:1"/> </td><TD class="defaultstyle" align="left">National Geographic field guide to the trees of North America </td><TD class="defaultstyle" align="left">Rushforth, Keith.</td><TD class="defaultstyle" align="left">BOOK </td><TD class="defaultstyle" align="left">0009207891236 </td><TD class="defaultstyle" align="left">7/24/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-CARNW </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009204737259:1"/> </td><TD class="defaultstyle" align="left">Wiring : [step-by-step instructions] </td><TD class="defaultstyle" align="left">Johnston, Larry.</td><TD class="defaultstyle" align="left">BOOK </td><TD class="defaultstyle" align="left">0009204737259 </td><TD class="defaultstyle" align="left">7/24/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-CARNW </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009187272373:1"/> </td><TD class="defaultstyle" align="left">The complete guide to home wiring : including information on home electronics & wireless technology </td><TD class="defaultstyle" align="left">Karre, Andrew.</td><TD class="defaultstyle" align="left">BOOK </td><TD class="defaultstyle" align="left">0009187272373 </td><TD class="defaultstyle" align="left">7/24/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-CARNW </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009182378340:1"/> </td><TD class="defaultstyle" align="left">Jeff Buckley  : live in Chicago </td><TD class="defaultstyle" align="left">Buckley, Jeff, 1966-1997.</td><TD class="defaultstyle" align="left">F-DVD </td><TD class="defaultstyle" align="left">0009182378340 </td><TD class="defaultstyle" align="left">7/27/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-CARNW </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009211865689:1"/> </td><TD class="defaultstyle" align="left">Ninja  </td><TD class="defaultstyle" align="left">Weldon, Les.</td><TD class="defaultstyle" align="left">NHDVD </td><TD class="defaultstyle" align="left">0009211865689 </td><TD class="defaultstyle" align="left">7/27/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-GARVLY </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><TD class="defaultstyle" align="left"><INPUT TYPE="CHECKBOX" NAME="HASNOW" VALUE="0009207031809:1"/> </td><TD class="defaultstyle" align="left">Grey Gardens  </td><TD class="defaultstyle" align="left">Coatsworth, David.</td><TD class="defaultstyle" align="left">F-DVD </td><TD class="defaultstyle" align="left">0009207031809 </td><TD class="defaultstyle" align="left">7/27/2010 </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left">CPL-CARNW </td><TD class="defaultstyle" align="left"> </td><TD class="defaultstyle" align="left"> </td></tr><tr><td> </td></tr><tr><td colspan=10 align="center" class="defaultstyle"><input type=hidden name="buttons" value="Renew=renew_hasnow screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="Renew" class=searchbutton VALUE="Renew Selected Items"><input type=hidden name="buttons" value="RenewAll=renew_hasnow hasnow=all screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="RenewAll" class=searchbutton VALUE="Renew All Items"></td></tr></form></table><br><A NAME=requests><FORM ACTION="/web2/tramp2.exe/form/A05l3fe7.000" METHOD="post" ENCTYPE="application/x-www-form-urlencoded"> <table border="2" cellpadding="2" cellspacing="0" width=100%>     <tr>      <td colspan="4" class="header">Holds</td><td colspan="3" class="header" align=right><A HREF="javascript:WinOpenQ()">\'Position in Queue\' is back but please click here to learn more about it.</a></tr>     <tr><tr><td colspan="7" class="subheader"><FORM ACTION="/web2/tramp2.exe/form/A05l3fe7.000" METHOD="post" ENCTYPE="application/x-www-form-urlencoded"><b>Sort by:<select name="request_sort_field"><OPTION VALUE="date_placed">Date Placed</option><OPTION VALUE="title">Title</option><OPTION VALUE="pickup_library">Pickup Location</option></select><input type=hidden name="buttons" value="sort_requests=goto screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="sort_requests" class=searchbutton VALUE="Sort Now"></td></tr><tr><td class="subheader" ></td><td class="subheader" width=30%>Title</td><td class="subheader" width=20%>Author</td><td class="subheader">Pickup Location</td><td class="subheader" >Available</td><td class="subheader">Date Placed</td><td class="subheader">Position in Queue</td></tr><tr><TD class="defaultstyle" align="left"><input type="checkbox" name="request" value="0009138821930"/><TD class="defaultstyle" align="left">Count zero </td><TD class="defaultstyle" align="left">Gibson, William, 1948- </td> <TD class="defaultstyle" align="left">CPL-CARNW </td> <TD class="defaultstyle" align="left"><font size=3 color="#333367"><b><center> </font></td><TD class="defaultstyle" align="left">7/19/2010 </td><TD class="defaultstyle" align="center"><b><center>1 </font></td></tr><tr><td> </td></tr><tr><td colspan=7 align="center" class="defaultstyle"><input type=hidden name="buttons" value="request2=cancel_request screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="request2" class=searchbutton VALUE="Cancel Selected Holds"><br></td></tr></form></table><br><A name=bills>    <table border="2" cellpadding="2" cellspacing="0" width=100%>     <tr>      <td colspan="5" class="header">Bills</td></tr><tr><tr><td colspan=5 class="subheader"><FORM ACTION="/web2/tramp2.exe/form/A05l3fe7.000" METHOD="post" ENCTYPE="application/x-www-form-urlencoded"><label>Sort by: </label><select Name="feefine_sort_field"><OPTION VALUE="amount_owed">Amount</option><OPTION VALUE="title">Title</option></select><input type=hidden name="buttons" value="sort_feefine=goto screen=MyAccount.html"><INPUT TYPE=SUBMIT NAME="sort_feefine" class=searchbutton VALUE="Sort Now"></td></tr>      <td class="subheader"  width=30%>Title</td><td class="subheader" width=20% >Author</td><td class="subheader">item_number</td><td class="subheader">Reason</td><td class="subheader">Amount</td></tr><TR><TD class="defaultstyle" align="left">Rework </td><TD class="defaultstyle" align="left">Fried, Jason.</td><TD class="defaultstyle" align="left">33235500583086</td><TD class="defaultstyle" align="left">OVERDUE </td><TD class="defaultstyle" align="left">$0.20 </TD></TR><TR><TD class="defaultstyle" align="left">Rework </td><TD class="defaultstyle" align="left">Fried, Jason.</td><TD class="defaultstyle" align="left">33235500583086</td><TD class="defaultstyle" align="left">OVERDUE </td><TD class="defaultstyle" align="left">$1.00 </TD></TR><TR><TD class="defaultstyle" align="left">Beginning smartphone web development : building JavaScript, CSS, HTML and Ajax-based applications for iPhone, Android, Palm Pre, Blackberry, Windows Mobile and Nokia S60 </td><TD class="defaultstyle" align="left">Frederick, Gail Rahn.</td><TD class="defaultstyle" align="left">0009213031553</td><TD class="defaultstyle" align="left">OVERDUE </td><TD class="defaultstyle" align="left">$0.20 </TD></TR><tr><td> </td></tr></form></table><br></td></tr></table><br><head></head><table border="0" cellpadding="0" cellspacing="0" width=100%><div class="searchservices"><tr><td align="center" class="gatewaystyle" >Copyright \xc2\xa9 Board of Trustees, Cleveland Public Library |3.3.1.0 (545)</td></tr></table></div></body></html>'