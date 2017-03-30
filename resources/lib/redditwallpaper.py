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
import shutil
import subprocess

from collections import namedtuple
from datetime import datetime, timedelta
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


def _extract_id_from_filename(filename):
	''' Extracts the image_id string from filename provided.
	'''

	if (filename.endswith('.png') or filename.endswith('.jpg')) and 'reddit_wp_' in filename:

		return re.sub(r'_\..*', '', re.sub(r'.*reddit_wp_', '', filename))


def _get_stored_image_ids(folder):
	''' Returns a list of image_id strings from the images that have been stored locally.
	'''

	image_ids = [ _extract_id_from_filename(x) for x in glob(os.path.join(folder, '*')) ]

	return [x for x in image_ids if x]


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

	links = subreddit.top(time_filters[int(toplast)], limit=int(topx))

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


def get_subreddit(reddit, subreddit_string):

	return reddit.subreddit(subreddit_string)


def get_reddit():

	return praw.Reddit(user_agent='Get wallpaper from reddit', client_id='WCFt04Sg1ZOgOA', client_secret='dD6faoM8OrnDLl6qoOvstwgUXbE')


def _validate_dimension(x, y, dimension, x_dim, y_dim, wriggle, **kwargs):
	''' Validates the provides image dimensions against those set by the user in the kodi settings.
	'''


	"Any|Strictly 16x9|Roughly 16x9|Strictly 4x3|Roughly 4x3|Precisely...|Roughly..."
	
	if dimension == 0: 	return 1	# Any

	try:  		ratio = float(x) / float(y)
	except: 	return None
	
	if   dimension == 1.0 and 1.76 < ratio < 1.78: 	return 1				# Strictly 16x9
	elif dimension == 2.0 and 1.70 < ratio < 1.86: 	return 1 				# Roughly 16x9
	elif dimension == 3.0 and 1.32 < ratio < 1.34: 	return 1				# Strictly 4x3
	elif dimension == 4.0 and 1.25 < ratio < 1.40: 	return 1				# Roughly 4x3
	elif dimension == 5.0 and x == int(x_dim) and y == int(y_dim): return 1	# Precisely...
	elif dimension == 6.0: 	# Roughly...

		try:		wriggle = (int(wriggle) / 100.0)
		except:		return None

		if x_dim * (1 - wriggle) < x < x_dim * (1 + wriggle):
			if y_dim * (1 - wriggle) < y < y_dim * (1 + wriggle):
				return 1

	return None


def _validate(image, min_size, max_size, **kwargs):
	''' Validates the image for fund size and image dimension.
	'''

	# test the image size in MB, skip it if it is too large or too small
	r = requests.head(image.image_url,headers={'Accept-Encoding': 'identity'})
	size = int(r.headers['content-length']) / MBFACTOR

	if not float(min_size) <= size <= float(max_size):
		log('File too large/small: %sMB  (%s)' % (size, image.image_url))
		return

	# check the dimensions of the image
	req  = requests.get(image.image_url, headers={'User-Agent':'Mozilla5.0(Google spider)','Range':'bytes=0-{}'.format(4096)})
	d = PILIMAGE.open(BytesIO(req.content)).size

	if not _validate_dimension(x=d[0], y=d[1], **kwargs):
		log('Wrong dimensions: %s  (%s)' % (str(d), image.image_url))
		return

	log('Valid: %s' % image.image_url)

	return image


def validate_images(image_url_list, **kwargs):
	''' Returns a list of images that pass the user requirements (validation)
	'''

	validated_url_list = [_validate(image, **kwargs) for image in image_url_list]

	return [ x for x in validated_url_list if x is not None]


def _download_folder_location(default_folder=True, alternative_location=None, **kwargs):
	''' Returns the user specified download location.
	'''

	if not default_folder and alternative_location is not None:
		return alternative_location
	else:
		return __scriptPath__


def _download(image, local_filename):
	''' Function that actually does the downloading of the individual images. 
	'''

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
	''' Downloads the images described in the validated_url_list.

		The contents of the storage folder is determined to ensure we are not downloading images
		we already have.

		The first image successfully downloaded is stored as the Principal Image.

		The Principal Image is always converted to a png file.
	'''


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
				log('Image failed to write to: %s' % local_filename)
				continue

		else:
			log('Image already available at: %s' % image.image_url)

		# if the principal image has not been set, then copy this image into the main wallpaper slot
		if set_principal_image:

			try:
				if image.image_ext == 'png':
					shutil.copy(local_filename, os.path.join(folder, 'REDDIT_WALLPAPER.png'))
				else:
					PILIMAGE.open(local_filename).save(os.path.join(folder, 'REDDIT_WALLPAPER.png'))
				
				set_principal_image = False

				log('Principal image assigned as: %s' % local_filename)

			except IOError:
				log('Principal image failed write: %s' % local_filename)
				continue

			# if the user does not want to retain local files, then delete the one that was just downloaded
			# and in any case stop processing images in the validated_url_list because we have our image already
			if not retain_all_images:
				try:
					os.remove(local_filename)
				except IOError:
					log('Failed to remove local file: %s' % local_filename)
				finally:
					break

	return set_principal_image

def _validate_setting(value):
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

	values = map(_validate_setting, [__setting__(key) for key in keys] )

	return dict(zip(keys, values))


def _right_now(raw=False):
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


def store_lastupdated():
	''' Stores the current time as the LastUpdate record in the kodi settings.
	'''

	__setthis__('LastUpdate', _right_now() )


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

	return _right_now(raw=True) > LastUpdate + delta
	
	
