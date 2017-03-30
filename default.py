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

from resources.lib.utils import get_settings, register_updatetime, log
from resources.lib.reddit import get_reddit, get_subreddit, get_image_urls_from_subreddit
from resources.lib.trigger import trigger_update
from resources.lib.validate import validate_images
from resources.lib.download import download_images

import xbmc


def ServiceLoop():
	''' Loop used by the service '''

	'''Never|30 Mins|Hour|3 Hours|Day|Week'''

	settings = get_settings()

	if settings.get('UpdateOnStart', True):

		Main(settings)

	while not xbmc.Monitor().waitForAbort(60) and settings['UpdateFrequency'] != 0.0:

		# the waitForAbort block is released every 60 seconds so we can retrive updated settings
		# and check the trigger time has not been reached.
		settings = get_settings()

		if trigger_update(**settings):

			Main(settings)


def Main(settings):

	reddit = get_reddit()

	image_url_list = []
	
	subreddit_strings = settings['subreddit_string'].split(',')

	for subreddit_string in subreddit_strings:

		subreddit = get_subreddit(reddit, subreddit_string)

		image_url_list += get_image_urls_from_subreddit(subreddit, **settings)

	log('%s raw image urls identified' % len(image_url_list))

	validated_url_list = validate_images(image_url_list, **settings)

	log('%s validated image urls' % len(validated_url_list))

	download_images(validated_url_list, **settings)

	register_updatetime()

	log('Process Complete')


if __name__ == '__main__':
	
	settings = get_settings()

	log(settings)

	Main(settings)
