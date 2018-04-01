from django.shortcuts import render
from django.utils.html import mark_safe

import os
import pkgutil
import pprint
import sys
import pwd

if sys.version_info[0] < 3:
    from cgi import escape
else:
    from html import escape

def dl(tuples):
    output = ''
    output += '<dl>\n'
    for title, description in tuples:
        if title:
            output += ' <dt>%s</dt>\n' % escape(title)
        if description:
            output += ' <dd>%s</dd>\n' % escape(description)
        output += '</dl>\n'
    return output

def group(seq):
    """(seq:(item, category)) -> {category:items}

    Groups items by supplied category, e.g.:
    group((e, e.tags[0]) for e in journal.get_recent_entries(100))

    Lifted from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/498223
    """
    result = {}
    for item, category in seq:
        result.setdefault(category, []).append(item)
    return result

def get_packages():
    return set([modname for importer, modname, ispkg in
    pkgutil.walk_packages(onerror=lambda x:x)
    if ispkg and '.' not in modname])

def format_packages():
    packages = group((pkg, pkg[0].lower()) for pkg in get_packages())
    # convert ('a',['apackage','anotherapackage]) into ('a', 'apackage, anotherapackage')
    packages = [(letter, ', '.join(pkgs)) for letter, pkgs in packages.items()]
    return '<h2>Installed Packages</h2>\n%s' % dl(sorted(packages))

def format_environ(environ):
    return '<h2>Environment (test)</h2>\n%s' % dl(sorted(environ.items()))

def format_python_path():
# differentiate between eggs and regular paths
    eggs = [p for p in sys.path if p.endswith('.egg')]
    paths = [p for p in sys.path if p not in eggs]
    return dl([('Paths', ',\n'.join(paths)),
    ('Eggs', ',\n'.join(eggs)),
    ])

def format_version():
    version, platform = sys.version.split('\n')
    sysname, nodename, release, osversion, machine = os.uname()
    return '<h2>Version</h2>\n%s' % dl([
    ('Python Version', version),
    ('Build Platform', platform),
    ('OS', sysname),
    ('OS Version', osversion),
    ('Machine Type', machine),
    ])

def format():
    output = ''
    output += 'Effective UID: ' + str(os.geteuid()) + " (" + pwd.getpwuid(os.geteuid())[0] + ")" + '<br>'
    output += '__file__: ' + __file__
    output += '<h1>Python Info</h1>\n'
    output += format_version()
    output += format_python_path()
    output += format_environ(os.environ)
    return output

def index(request):
    context = {
        'format': mark_safe(format()),
        'pkgs': mark_safe(format_packages()),
    }
    return render(request, 'info/index.html', context)
