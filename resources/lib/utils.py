#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2017 KodeKarnage
#
#  This Program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2, or (at your option)
#  any later version.
#
#  This Program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with XBMC; see the file COPYING.  If not, write to
#  the Free Software Foundation, 675 Mass Ave, Cambridge, MA 02139, USA.
#  http://www.gnu.org/copyleft/gpl.html
#


from datetime import datetime
import time

import xbmc
import xbmcaddon

__addon__      = xbmcaddon.Addon()
__setting__    = __addon__.getSetting
__setthis__    = __addon__.setSetting
__scriptPath__ = xbmc.translatePath( __addon__.getAddonInfo('profile') )


def log(logmsg):

	xbmc.log(msg = 'Reddit Wallpaper: ' + str(logmsg), level=xbmc.LOGDEBUG)


def right_now(raw=False):
	''' Returns the current time. 
		raw=True will return the raw datetime, but default is to convert it into a string.

		Sometimes dt.now() throws some sort of "lock" error,
		so we will give the function 1 second to throw errors and retrieve the time.
	'''

	for _ in range(5):
		try:
			if raw:
				return datetime.now()
			else:
				return datetime.now().strftime('%Y-%m-%d %H:%M')
		except:
			log('Error updating update time.')
			time.sleep(0.2)


def _convert_setting(value):
	''' Used by the get_settings function to validate the settings from kodi.
	'''

	try:
		return float(value)
	except ValueError:
		pass

	if value == 'true':  return True
	if value == 'false': return False

	return value


def get_settings():
	''' This function retrieves and validates the user settings from KODI.
		- string booleans are changed to actual booleans
		- all strings that can be turned into floats are converted
	Returns a dictionary of setting key and value pairs.		
	'''

	keys = ['UpdateOnStart', 'UpdateFrequency', 'LastUpdate',
			'allow_naughty', 'retain_all_images',
			'topx', 'toplast',
			'subreddit_string', 'alternative_location', 'default_folder',
			'max_size', 'min_size',
			'dimension', 'x_dim', 'y_dim', 'wriggle'
				]

	values = map(_convert_setting, [__setting__(key) for key in keys] )

	return dict(zip(keys, values))


def register_updatetime():
	''' Stores the current time as the LastUpdate record in the kodi settings.
	'''

	__setthis__('LastUpdate', right_now() )

