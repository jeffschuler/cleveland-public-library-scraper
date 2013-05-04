#!/usr/bin/python

import urllib2, re, time
import urllib
from urllib import urlencode
from BeautifulSoup import BeautifulSoup

# Get our account number and PIN from a JSON conf file
import json
conf_file = open('cpl_conf.json')
conf_data = json.load(conf_file)
cplAcctNumStr = conf_data["account_id"]
cplPinNumStr = conf_data["pin"]

##
# Skip all this:
##

#url = 'http://myaccount.clevnet.org/htbin/netnotice/' + cplAcctNumStr
#page = urllib2.urlopen(url)
#
#soup = BeautifulSoup(page)
##print soup.prettify()
#
#auth_form_hidden_field_1_name="sss"
#auth_form_hidden_field_1_value = soup.find(attrs={"name" : auth_form_hidden_field_1_name})['value']
#
#auth_form_name="GetPIN"
#auth_form_action="http://clvms1.cpl.org/htbin/netnotice/auth"
#auth_form_password_input_name="uPin"
#auth_form_password_input_pass=cplPinNumStr
#
#auth_form_hidden_field_2_name="phase"
#auth_form_hidden_field_2_value="auth"
#
#####
#
#formValues = {auth_form_password_input_name : auth_form_password_input_pass,
#          auth_form_hidden_field_1_name : auth_form_hidden_field_1_value,
#          auth_form_hidden_field_2_name : auth_form_hidden_field_2_value }
#
#formData = urllib.urlencode(formValues)
#formRequest = urllib2.Request(auth_form_action, formData)
#formRequestResponse = urllib2.urlopen(formRequest)
#theResponsePage = formRequestResponse.read()
#
#soup2 = BeautifulSoup(theResponsePage)
#print soup2
#
#
##<HTML>
##<BODY>
##<form name="Get_PIN" action="http://clvms1.cpl.org/htbin/netnotice/auth">
##PIN #: <input name="uPin" type="password">
##<input type="hidden" name="sss" value="00003E4C">
##<input type="hidden" name="phase" value="auth">
##<input type="submit">
##</BODY></HTML>

##
# ...Because we really only need to do this:
##

#http://search1.clevnet.org/web2/tramp2.exe/log_in?setting_key=CLEVNET&login=patron&begin=t&login_pin_required=t&screen=myaccount.html&userid=ACCTNUM&pin=PIN

formValues = {
    'setting_key' : 'CLEVNET',
    'login' : 'patron',
    'begin' : 't',
    'login_pin_required' : 't',
    'screen' : 'myaccount.html',
    'userid' : cplAcctNumStr,
    'pin' : cplPinNumStr
    }

formData = urllib.urlencode(formValues)
formRequest = urllib2.Request('http://search1.clevnet.org/web2/tramp2.exe/log_in', formData)
formRequestResponse = urllib2.urlopen(formRequest)
responsePage = formRequestResponse.read()

soup = BeautifulSoup(responsePage)
print soup.prettify()