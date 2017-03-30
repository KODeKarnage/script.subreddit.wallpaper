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

from glob import glob
from PIL import Image as PILIMAGE
import requests
import shutil
import os

from utils import log

import xbmc
import xbmcaddon

__addon__       = xbmcaddon.Addon()
__scriptPath__  = xbmc.translatePath( __addon__.getAddonInfo('profile') )



def _download_folder_location(default_folder=True, alternative_location=None, **kwargs):
	''' Returns the user specified download location.
	'''

	if not default_folder and alternative_location is not None:
		return alternative_location
	else:
		return __scriptPath__


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
				
				# set_principal_image only gets flipped if the Principal Image has been set
				set_principal_image = False

				log('Principal image assigned as: %s' % local_filename)

			except IOError:
				log('Principal image failed write: %s' % local_filename)

				# We have failed to set a Principal Image, move on and try the next url
				continue

			# if the user does not want to retain local files, then delete the one that was just downloaded
			if not retain_all_images:
				try:
					os.remove(local_filename)
				except IOError:
					log('Failed to remove local file: %s' % local_filename)
				finally:
					# Stop processing images in the validated_url_list because we have our image already.
					# We only reach here if set_principal_image has been flipped
					break
