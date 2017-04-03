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

from utils import log, right_now

from datetime import datetime, timedelta


def trigger_update(LastUpdate, UpdateFrequency, **kwargs):
	''' Returns a boolean indicating whether the current time is after the
		last updated time store in the kodi settings plus the desired delay between 
		update checks.
	'''

	# if the update frequency is never then return None
	if UpdateFrequency == 0: 
		return None

	# if the LastUpdate has not been set yet, then allow the trigger
	if LastUpdate == 'NotSet':
		return True

	try:
		LastUpdate = datetime.strptime(LastUpdate, '%Y-%m-%d %H:%M')

	except ValueError:
		log('Could not parse last update time: %s' % LastUpdate)
		return None

	except Exception as e:
		log_unhandledException('parsing last update time.')
		return None		

	'''Never|30 Mins|Hour|3 Hours|Day|Week'''
	deltas = {
				1: timedelta(minutes=30),
				2: timedelta(hours=1),
				3: timedelta(hours=3), 
				4: timedelta(hours=24), 
				5: timedelta(weeks=1)
				}

	delta = deltas.get(int(UpdateFrequency), None)

	if not delta:

		return

	return right_now(raw=True) > LastUpdate + delta
	
	
