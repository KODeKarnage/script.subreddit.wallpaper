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

#!/usr/bin/env python
# -*- coding: utf-8 -*-

import praw
import requests

from collections import namedtuple
from utils import log


Image = namedtuple('Image', 'image_id, raw_url, image_url, image_ext')


def _extract_image_url(url):
	''' Cleans the url and returns only the image link.
	'''

	if any([url.endswith('.jpg'), url.endswith('.png')]):

		return url

	elif all(['imgur.com' in url, '/a/' not in url, '/gallery/' not in url]):

		if url.endswith('/new'):

			url = url.rsplit('/', 1)[0]

		image_id = url.rsplit('/', 1)[1].rsplit('.', 1)[0]

		return 'http://i.imgur.com/%s.jpg' % image_id


def get_image_urls_from_subreddit(subreddit, toplast, topx, allow_naughty, **kwargs):
	''' Returns a list of Image tuples from the desired subreddit.

		Age restriction check is done at the earliest opportunity here.
	'''

	time_filters = ['hour', 'day', 'week', 'month', 'all']

	log('Getting top posts from /r/%s' % subreddit)

	links = subreddit.top(time_filters[int(toplast)], limit=int(topx))

	image_url_list = []

	for link in links:

		if link.over_18 and not allow_naughty:
			continue

		try:
			url = link.url[:link.url.index('?')]
		
		except ValueError:
			url = link.url

		except Exception as e:
			log_unhandledException('obtaining image link from url.')
			url = link.url				

		image_url = _extract_image_url(url)

		if not image_url:
			continue

		image_url_list.append( Image(image_id=link.id, raw_url=link.url, image_url=image_url, image_ext=image_url[-3:]) )

	return image_url_list


def get_subreddit(reddit, subreddit_string):

	return reddit.subreddit(subreddit_string)


def get_reddit():

	return praw.Reddit(user_agent='Get wallpaper from reddit', client_id='WCFt04Sg1ZOgOA', client_secret='dD6faoM8OrnDLl6qoOvstwgUXbE')

