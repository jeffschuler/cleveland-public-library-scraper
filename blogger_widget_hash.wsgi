from scrapeCplAccount import calc_account_hash
from cgi import parse_qs, escape
from tidylib import tidy_document

def application(environ, start_response):
    status = '200 OK'
    start_response('200 OK', [('Content-Type', 'text/html')])

    account_hash = ''
    account_id = ''
    account_pin = ''

    # Get GET params
    parameters = parse_qs(environ.get('QUERY_STRING', ''))
    if 'i' in parameters:
        account_id = escape(parameters['i'][0])
    if 'p' in parameters:
        account_pin = escape(parameters['p'][0])

    output = '<html>'
    output += '<head>'
    output += '<title>CPL Account Info Widget</title>'
    output += '<style type="text/css">'
    output += 'li.libitem .author { font-size: .9em; text-align: right; }\n'
    output += '.caption { font-size: .85em; font-weight: bold }'
    output += '</style>'
    output += '</head>'
    output += '<body>'

    #output += '<p>'
    #output += 'id = ' + account_id + '<br />'
    #output += 'pin = ' + account_pin
    #output += '</p>'

    if (account_id and account_pin):
        account_hash = calc_account_hash(account_id, account_pin)

    if (account_hash):
        output += '<p>Account hash: ' + account_hash + '</p>'
        output += '<p>Choose the title for your widget and add it:</p>'
        output += '<form method="POST" action="http://www.blogger.com/add-widget">'
        output += '  <input type="hidden" name="widget.content" value="&lt;script type=\'text/javascript\' src=\'http://cpl.digmob.org/cpl_account_info_js?h=' + account_hash + '\'&gt;&lt;/script&gt;"/>'
        output += '  <input type="hidden" name="widget.template" value="&lt;data:content/&gt;" />'
        output += '  <input type="hidden" name="infoUrl" value="http://cpl.digmob.org/blogger_widget_info.html"/>'
        output += '  <!-- <input type="hidden" name="logoUrl" value="http://www.blogger.com/img/icon_logo32.gif"/> -->'
        output += '  <table>'
        output += '    <tr>'
        output += '      <td>Title:</td>'
        output += '      <td><input type="text" name="widget.title" value="My Checkouts/Holds at the Cleveland Public Library" size="40" maxlength="100" /></td>'
        output += '    </tr>'
        output += '  </table>'
        output += '  <input type="submit" name="go" value="Add CPL Account Info Widget" />'
        output += '  <!-- http://www.blogger.com/img/add/add2blogger_sm_w.gif -->'
        output += '</form>'
    else:
        output += '<p>Account # and PIN needed.</p>'

    output += '</body></html>'

    document, errors = tidy_document(output)

    response_headers = [('Content-type', 'text/html'),
                        ('Content-Length', str(len(document)))]
    start_response(status, response_headers)

    return [document]