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

import os
import praw
import re
import requests
import subprocess
import sys
import time

from collections import namedtuple
from glob import glob
from io import BytesIO
from PIL import Image as PILIMAGE

import xbmc
import xbmcaddon

__addon__              = xbmcaddon.Addon()
__scriptPath__         = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__setting__            = __addon__.getSetting

MBFACTOR = float(1 << 20)

Image = namedtuple('Image', 'image_id, raw_url, image_url, image_ext')

def log(logmsg):
	xbmc.log(msg = 'Reddit Wallpaper: ' + str(logmsg))

def _extract_image_url(url):

	if any([url.endswith('.jpg'), url.endswith('.png')]):

		return url

	elif all(['imgur.com' in url, '/a/' not in url, '/gallery/' not in url]):

		if url.endswith('/new'):

			url = url.rsplit('/', 1)[0]

		image_id = url.rsplit('/', 1)[1].rsplit('.', 1)[0]

		return 'http://i.imgur.com/%s.jpg' % image_id


def _extract_id_from_filename(filename):

	if (filename.endswith('.png') or filename.endswith('.jpg')) and 'reddit_wp_' in filename:

		return re.sub(r'_\..*', '', re.sub(r'.*reddit_wp_', '', filename))


def _get_stored_image_ids(folder):

	image_ids = [ _extract_id_from_filename(x) for x in glob(os.path.join(folder, '*')) ]

	return [x for x in image_ids if x]


def get_image_urls(subreddit, toplast='day', topx=10, allow_naughty=False, **kwargs):

	links = subreddit.top(toplast, limit=topx)

	image_url_list = []

	for link in links:

		if link.over_18 and not allow_naughty:
			continue

		try:
			url = link.url[:link.url.index('?')]
		
		except ValueError:
			url = link.url

		image_url = _extract_image_url(url)

		if not image_url:
			continue

		image_url_list.append( Image(image_id=link.id, raw_url=link.url, image_url=image_url, image_ext=image_url[-3:]) )

	return image_url_list


def get_sub(reddit, subreddit_string='wallpapers', **kwargs):

	return reddit.subreddit(subreddit_string)


def get_reddit():

	return praw.Reddit(user_agent='Get wallpaper from reddit', client_id='WCFt04Sg1ZOgOA', client_secret='dD6faoM8OrnDLl6qoOvstwgUXbE')


def download_images(image_url_list, default_folder='true', alternative_location=None , StoreImages='true', **kwargs):

	if default_folder != 'true' and alternative_location is not None:
		folder = alternative_location
	else:
		folder = __scriptPath__

	# get list of ids for the stored images
	stored_image_ids = _get_stored_image_ids(folder)

	top_slot = image_url_list[0]

	principal_image = True

	# ignore the image if it is already stored
	image_url_list = [x for x in image_url_list if x.image_id not in stored_image_ids]

	# process the urls remaining in image list
	for image in image_url_list:

		log(image.image_url)

		# test the image size, skip it if it is too large
		r = requests.head(image.image_url,headers={'Accept-Encoding': 'identity'})
		size = int(r.headers['content-length']) / MBFACTOR

		if float(kwargs['max_size']) < size or size < float(kwargs['min_size']):
			log('File too large: %sMB' % size)
			continue

		# check the dimensions of the image
		req  = requests.get(image.image_url, headers={'User-Agent':'Mozilla5.0(Google spider)','Range':'bytes=0-{}'.format(4096)})
		dims = PILIMAGE.open(BytesIO(req.content)).size

		if dims[0] != 1920 or dims[1] != 1080: 
			log('Wrong dimensions: %s' % str(dims))
			continue
	
		# grab the image
		res = requests.get(image.image_url, allow_redirects=False)

		# if successfull, then save the image
		if res.status_code == requests.codes.ok:

			# store the images
			if StoreImages:

				filename = 'reddit_wp_%s_.%s' % (image.image_id, image.image_ext)

				filename = os.path.join(folder, filename)

				with open(filename, 'wb') as fo:
					for chunk in res.iter_content(4096):
						fo.write(chunk)

			# if the principal image has not been assigned then save this image in the number one slot today
			if principal_image:

				PILIMAGE.open(filename).save(os.path.join(folder, 'REDDIT_WALLPAPER.png'))

				principal_image = False

	# if the principal image was not set from the newly downloaded images, then use the already downloaded top_slot image
	if principal_image and top_slot:

		filename = 'reddit_wp_%s_.%s' % (top_slot.image_id, top_slot.image_ext)
		filename = os.path.join(folder, filename)

		PILIMAGE.open(filename).save(os.path.join(folder, 'REDDIT_WALLPAPER.png'))


def get_settings():

	keywords = ['UpdateOnStart', 'allow_naughty', 'StoreImages', 'topx', 'max_size', 'min_size',
				'subreddit_string', 'alternative_location', 'default_folder']

	return {kw: __setting__(kw) for kw in keywords}
