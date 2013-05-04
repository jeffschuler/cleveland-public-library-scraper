from scrapeCplAccount import *
from cgi import parse_qs, escape

def application(environ, start_response):
    status = '200 OK'

    content_type = account_hash = account_id = account_pin = format = ''

    # Get GET params
    parameters = parse_qs(environ.get('QUERY_STRING', ''))
    if 'c' in parameters: # Content-type (html, js_html)
        content_type = escape(parameters['c'][0])
    if 'h' in parameters: # Account hash
        account_hash = escape(parameters['h'][0])
    if 'i' in parameters: # Account ID
        account_id = escape(parameters['i'][0])
    if 'p' in parameters: # Account PIN
        account_pin = escape(parameters['p'][0])
    if 'f' in parameters: # Format (table, list)
        format = escape(parameters['f'][0])

    if ((not account_hash) and (account_id and account_pin)):
        account_hash = add_account(account_id, account_pin)

    if content_type == 'js_html':
        content_type_str = 'text/javascript'
        output = go_render_js_html(account_hash, format)
    elif content_type == 'json':
        content_type_str = 'text/javascript'
        output = go_render_json(account_hash)
    else: # html
        content_type_str = 'text/html'
        output = go_render_html(account_hash, format)

    content_type_header = ('Content-Type', content_type_str)

    response_headers = [content_type_header, ('Content-Length', str(len(output)))]
    start_response(status, response_headers)

    return [output]


def go_render_html(account_hash, format='list'):
    """ Render as HTML, (in list or table format) """

    from tidylib import tidy_document

    output = '<html>'
    output += '<head>'
    output += '<title>CPL Account Info</title>'
    output += '<style type="text/css">'
    output += 'body { color: #1D1D1D; background-color: #F0EEE5; font-family: Tahoma,Arial,Trebuchet MS,sans-serif; font-size: 0.8em; margin: 20px 40px; }\n'
    output += 'li.libitem .author { font-size: .9em; text-align: right; }\n'
    output += '.caption { font-size: .85em; font-weight: bold }'
    output += '</style>'
    output += '</head>'
    output += '<body>'

    if (account_hash):
        output += go_render(account_hash)
    else:
        output += '<p>Account # and PIN needed.</p>'

    output += '</body></html>'

    document, errors = tidy_document(output)

    return document


def go_render_js_html(account_hash, format='list'):
    """ Render as JS that writes HTML, (in list or table format) """

    from string import replace

    output = 'var cpl_txt = \'\';'

    output += 'cpl_txt += \'<style type="text/css">\';'
    output += 'cpl_txt += \'li.libitem .author { font-size: .9em; text-align: right; } \';'
    output += 'cpl_txt += \'.caption { font-size: .85em; font-weight: bold } \';'
    output += 'cpl_txt += \'</style>\';'

    if (account_hash):
        account_info_html = go_render(account_hash)
        account_info_html = replace(account_info_html, '\'', '\\\'')
        output += 'cpl_txt += \'' + account_info_html + '\';'
    else:
        output += 'cpl_txt += \'Account # and PIN needed.\''

    output += 'document.write(cpl_txt);'

    return output

def go_render_json(account_hash):
    """ Render as JSON """
    
    import json

    if (account_hash):
        account_info = go_get_all(account_hash)
        output = json.write(account_info)
    else:
        output = ''
    
    return output