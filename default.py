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

from resources.lib.redditwallpaper import *
import xbmc


def ServiceLoop():
	''' Loop used by the service '''

	'''Never|30 Mins|Hour|3 Hours|Day|Week'''

	settings = get_settings()

	if settings.get('UpdateOnStart', True):

		Main(settings)

	while not xbmc.waitforAbort(60) and settings['UpdateFrequency'] != 0:

		settings = get_settings()

		if trigger_update(**settings):

			Main(settings)


def Main(settings):

	reddit = get_reddit()

	subreddit = get_sub(reddit, **settings)

	image_url_list = get_image_urls(subreddit, **settings)

	validated_url_list = validate_images(image_url_list, **settings)

	download_images(validated_url_list, **settings)

	store_lastupdated()



if __name__ == '__main__':
	
	settings = get_settings()

	Main(settings)
