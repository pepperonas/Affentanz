# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import biplist
import os.path

#
# Example settings file for dmgbuild
#

# Use like this: dmgbuild -s settings.py "Affentanz" affentanz.dmg

# You can actually use this file for your own application (not just TextEdit)
# by doing e.g.
#
#   dmgbuild -s settings.py -D app=/path/to/application.app "My Application" MyApp.dmg

# .. Useful stuff ..............................................................

application = defines.get('app', '/Users/martin/PycharmProjects/Affentanz/dist/Affentanz.app')
appname = os.path.basename(application)

def icon_from_app(app_path):
    plist_path = os.path.join(app_path, 'Contents', 'Info.plist')
    if os.path.exists(plist_path):
        with open(plist_path, 'rb') as f:
            plist = biplist.readPlist(f)
        
        if 'CFBundleIconFile' in plist:
            icon_name = plist['CFBundleIconFile']
            icon_root, icon_ext = os.path.splitext(icon_name)
            if not icon_ext:
                icon_ext = '.icns'
            icon_name = icon_root + icon_ext
            
            return os.path.join(app_path, 'Contents', 'Resources', icon_name)
    
    return None

# .. Basics ....................................................................

# Volume format (see hdiutil create -help)
format = defines.get('format', 'UDBZ')

# Volume size
size = defines.get('size', None)

# Files to include
files = [application]

# Symlinks to create
symlinks = {'Applications': '/Applications'}

# Volume icon
#
# You can either define icon, in which case that icon file will be copied to the
# image, *or* you can define badge_icon, in which case the icon file you specify
# will be used to badge the system's Removable Disk icon
#
#icon = '/path/to/icon.icns'
badge_icon = icon_from_app(application)

# Where to put the icons
icon_locations = {
    appname: (140, 120),
    'Applications': (500, 120)
}

# .. Window configuration ......................................................

# Background
#
# This is a STRING containing any of the following:
#
#    #3344ff          - web-style RGB color
#    #34f             - web-style RGB color, short form (#34f == #3344ff)
#    rgb(1,0,0)       - RGB color, each value is between 0 and 1
#    hsl(120,1,.5)    - HSL (hue saturation lightness) color
#    hwb(300,0,0)     - HWB (hue whiteness blackness) color
#    cmyk(0,1,0,0)    - CMYK color
#    goldenrod        - X11/SVG named color
#    builtin-arrow    - A simple built-in background with a blue arrow
#    /foo/bar/baz.png - The path to an image file
#
# The hue component in hsl() and hwb() may include a unit; it defaults to
# degrees ('deg'), but also supports radians ('rad') and gradians ('grad'
# or 'gon').
#
# Other color components may be expressed either in the range 0 to 1, or
# as percentages (e.g. 60% is equivalent to 0.6).
background = 'builtin-arrow'

show_status_bar = False
show_tab_view = False
show_toolbar = False
show_pathbar = False
show_sidebar = False
sidebar_width = 180

# Window position in ((x, y), (w, h)) format
window_rect = ((100, 100), (640, 280))

# Select the default view; must be one of
#
#    'icon-view'
#    'list-view'
#    'column-view'
#    'coverflow'
#
default_view = 'icon-view'

# General view configuration
show_icon_preview = False

# Set these to True to force inclusion of icon/list view settings (otherwise
# we only include settings for the default view)
include_icon_view_settings = True
include_list_view_settings = False

# .. Icon view configuration ...................................................

arrange_by = None
grid_offset = (0, 0)
grid_spacing = 100
scroll_position = (0, 0)
label_pos = 'bottom' # or 'right'
text_size = 16
icon_size = 128

# .. List view configuration ...................................................

# Column names are as per `man 1 ls`; valid names are:
#
#   name
#   date-modified
#   date-created
#   date-added
#   date-last-opened
#   size
#   kind
#   comments
#   version
#   contact
#
list_icon_size = 16
list_text_size = 12
list_scroll_position = (0, 0)
list_sort_by = 'name'
list_use_relative_dates = True
list_calculate_all_sizes = False,
list_columns = ('name', 'date-modified', 'size', 'kind', 'date-added')
list_column_widths = {
    'name': 300,
    'date-modified': 181,
    'date-created': 181,
    'date-added': 181,
    'date-last-opened': 181,
    'size': 97,
    'kind': 115,
    'comments': 300,
    'version': 75,
    'contact': 300,
}
list_column_sort_directions = {
    'name': 'ascending',
    'date-modified': 'descending',
    'date-created': 'descending',
    'date-added': 'descending',
    'date-last-opened': 'descending',
    'size': 'descending',
    'kind': 'ascending',
    'comments': 'ascending',
    'version': 'ascending',
    'contact': 'ascending',
}

# .. License configuration .....................................................

# Text in the license configuration is stored in the __license variable,
# and is used for the content of the "License" screen of the built dmg
__license = None

# .. Conclusion ................................................................

# You should not need to change anything past this point

# .. Auto-calculated settings ..................................................

# Some variables are just parts of paths but we don't to expose that as settings
applications_path = '/Applications'