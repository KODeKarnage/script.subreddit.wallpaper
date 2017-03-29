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

from datetime import datetime as dt
from collections import namedtuple
from glob import glob
from io import BytesIO
from PIL import Image as PILIMAGE

import xbmc
import xbmcaddon

__addon__              = xbmcaddon.Addon()
__scriptPath__         = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__setting__            = __addon__.getSetting
__setthis__            = __addon__.setSetting

MBFACTOR = float(1 << 20)

Image = namedtuple('Image', 'image_id, raw_url, image_url, image_ext')


def log(logmsg):

	xbmc.log(msg = 'Reddit Wallpaper: ' + str(logmsg), level=xbmc.LOGDEBUG)


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


def get_image_urls(subreddit, toplast, topx, allow_naughty, **kwargs):

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


def _test_dimension(x, y, dimension, x_dim, y_dim, wriggle, **kwargs):

	"Any|Strictly 16x9|Roughly 16x9|Strictly 4x3|Roughly 4x3|Precisely...|Roughly..."
	
	if dimension == 0: 	return 1	# Any

	try:  		ratio = float(x) / float(y)
	except: 	return None
	
	if   dimension == 1 and 1.76 < ratio < 1.78: 	return 1				# Strictly 16x9
	elif dimension == 2 and 1.70 < ratio < 1.86: 	return 1 				# Roughly 16x9
	elif dimension == 3 and 1.32 < ratio < 1.34: 	return 1				# Strictly 4x3
	elif dimension == 4 and 1.25 < ratio < 1.40: 	return 1				# Roughly 4x3
	elif dimension == 5 and x == int(x_dim) and y == int(y_dim): return 1	# Precisely...
	elif dimension == 6: 	# Roughly...

		try:		wriggle = (int(wriggle) / 100.0)
		except:		return None

		if x_dim * (1 - wriggle) < x < x_dim * (1 + wriggle):
			if y_dim * (1 - wriggle) < y < y_dim * (1 + wriggle):
				return 1

	return None


def _validate(image, min_size, max_size, **kwargs):

	# test the image size in MB, skip it if it is too large or too small
	r = requests.head(image.image_url,headers={'Accept-Encoding': 'identity'})
	size = int(r.headers['content-length']) / MBFACTOR

	if not float(min_size) <= size <= float(max_size):
		log('File too large/small: %sMB  (%s)' % (size, image.image_url))
		return

	# check the dimensions of the image
	req  = requests.get(image.image_url, headers={'User-Agent':'Mozilla5.0(Google spider)','Range':'bytes=0-{}'.format(4096)})
	d = PILIMAGE.open(BytesIO(req.content)).size

	if not _test_dimension(x=d[0], y=d[1], **kwargs):
		log('Wrong dimensions: %s  (%s)' % (str(d), image.image_url))
		return

	log('Valid: %s' % image.image_url)

	return image


def validate_images(image_url_list, **kwargs):

	validated_url_list = [_validate(image, **kwargs) for image in image_url_list]

	return [ x for x in validated_url_list if x not None]


def _download_folder_location(default_folder=True, alternative_location=None, **kwargs):
	'''Set the download location'''

	if not default_folder and alternative_location is not None:
		return alternative_location
	else:
		return __scriptPath__


def _download(image, local_filename):

		# request the complete image
		response = requests.get(image.image_url, allow_redirects=False)

		# if the request fails, raise error which will prompt a move to the next image in the list
		if response.status_code != requests.codes.ok:

			raise requests.exceptions.HTTPError

		# write the file to disk
		with open(local_filename, 'wb') as f:
			for chunk in response.iter_content(4096):
				f.write(chunk)


def download_images(validated_url_list, retain_all_images=True, set_principal_image=True, **kwargs):

	# set the download location
	folder = _download_folder_location(**kwargs)

	# get list of ids for the images stored in the folder
	stored_image_ids = _get_stored_image_ids(folder)

	# process the urls remaining in image list
	for image in validated_url_list:

		# construct the new filename
		local_filename = os.path.join(folder, 'reddit_wp_%s_.%s' % (image.image_id, image.image_ext))

		# if the image is not already stored, then download it
		if image.image_id not in stored_image_ids:

			try:
				_download(image, local_filename)

			except requests.exceptions.HTTPError:
				log('Image failed to download: %s' % image.image_url)
				continue

			except IOError:
				log('Image failed to write: %s' % local_filename)
				continue

		# if the principal image has not been set, then copy this image into the main wallpaper slot
		if set_principal_image:

			try:
				PILIMAGE.open(local_filename).save(os.path.join(folder, 'REDDIT_WALLPAPER.png'))
				set_principal_image = False

				log('Principal image changed to: %s' % local_filename)

			except IOError:
				log('Principal image failed write: %s' % local_filename)
				continue

			# if the user does not want to retain local files, then delete the one that was just downloaded
			# and in any case stop processing images in the validated_url_list
			if not retain_all_images:
				try:
					os.remove(local_filename)
				except IOError:
					log('Failed to remove local file: %s' % local_filename)
				finally:
					break


def _validate_setting(value):

	try:
		return float(value)
	except ValueError:
		return value

	if value == 'true':  return True
	if value == 'false': return False


def get_settings():


	keys = ['UpdateOnStart', 'allow_naughty', 'retain_all_images', 'topx', 'toplast',
			'subreddit_string', 'alternative_location', 'default_folder',
			'max_size', 'min_size',
			'dimension', 'x_dim', 'y_dim', 'wriggle'
				]

	values = map(_validate_setting, [__setting__(key) for key in keys] )

	return dict(zip(keys, values))


def _right_now():

	for _ in range(5):
		try:
			return dt.now().strftime('%Y-%m-%d %H:%M')
		except:
			log('Error updating update time.')
			time.sleep(1)


def store_lastupdated():

		__setthis__('LastUpdate', _right_now() )


def trigger_update(LastUpdate, UpdateFrequency, **kwargs):
	'''Never|30 Mins|Hour|3 Hours|Day|Week'''

	# if the update frequency is never then return None
	if UpdateFrequency == 0: 
		return None

	# if the LastUpdate has not been set yet, then allow the trigger
	if LastUpdate == 'NotSet':
		return True

	try:
		LastUpdate = dt.strptime(LastUpdate, '%Y-%m-%d %H:%M')

	except ValueError:
		log('Could not parse last update time: %s' % LastUpdate)
		return None

	timedelta = {
					1: dt.timedelta(minutes=30),
					2: dt.timedelta(hours=1),
					3: dt.timedelta(hours=3), 
					4: dt.timedelta(hours=24), 
					5: dt.timedelta(weeks=1)
					}

	delta = timedelta(UpdateFrequency, None)

	if not delta:

		return

	return _right_now() < LastUpdate + delta
	
	
