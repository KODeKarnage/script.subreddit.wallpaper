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

import requests

from utils import log

from io import BytesIO
from PIL import Image as PILIMAGE

import time

MBFACTOR = float(1 << 20)


def _validate_dimension(x, y, dimension, x_dim, y_dim, wriggle, **kwargs):
	''' Validates the provides image dimensions against those set by the user in the kodi settings.
	'''

	'''Any|Strictly 16x9|Roughly 16x9|Strictly 4x3|Roughly 4x3|Precisely...|Roughly...'''
	
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
	try:
		d = PILIMAGE.open(BytesIO(req.content)).size
	except IOError:
		log('IOError reading %s' % image.image_url)
		return

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
