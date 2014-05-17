#!/usr/bin/python
# -*- coding: utf-8 -*-

#  Copyright (C) 2013 KodeKarnage
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


import xbmc
import json
import xbmcaddon
import xbmcgui
import os
import sys
import smtplib
from email.mime.text import MIMEText
import shutil
import re

__addon__   = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
scriptPath       = __addon__.getAddonInfo('path')
__setting__ = __addon__.getSetting
lang        = __addon__.getLocalizedString
progress    = xbmcgui.DialogProgress()
dialog = xbmcgui.Dialog()
THUMBS_CACHE_PATH = xbmc.translatePath( "special://profile/Thumbnails" )

user_data = xbmc.translatePath( "special://userdata")
cachefile = os.path.join(user_data,'addon_data',os.path.basename(scriptPath),'cachefile.txt')
searchfile = os.path.join(user_data,'addon_data',os.path.basename(scriptPath),'searchfile.txt')


__resource__     =  os.path.join(scriptPath, 'resources')
sys.path.append(__resource__)


extensions     = []
items_selected = []


def correct_bool(boolean):
	return True if boolean == 'true' else False

logging  = correct_bool(__setting__('log'))

def log(message):
	if logging:
		xbmc.log(msg = 'LooseFiles -=- ' + str(message))

other_ext = __setting__('formats')

if other_ext:
	extras = other_ext.split(',')
	extensions += extras

avi  = correct_bool(__setting__('avi'))
mkv  = correct_bool(__setting__('mkv'))
mpg  = correct_bool(__setting__('mpg'))
mpeg = correct_bool(__setting__('mpeg'))
mp4  = correct_bool(__setting__('mp4'))
wmv  = correct_bool(__setting__('wmv'))
mov  = correct_bool(__setting__('mov'))


to_email = correct_bool(__setting__('to_email'))
to_disk  = correct_bool(__setting__('to_disk'))
address = __setting__('address')
location = __setting__('location')

size = __setting__('size')

if size == '0':
	size = 'off'
elif size == '1':
	size = 10485760
elif size == '2':
	size = 10485760 * 5
elif size == '3':
	size = 10485760 * 10
elif size == '4':
	size = 10485760 * 50
elif size == '5':
	size = 10485760 * 100
else:
	size = 'off'

searchstring = ''
rescan = True
search = 'Loose'
af_list = ''
bail = False


eps_query  = {"jsonrpc": "2.0","method": "VideoLibrary.GetEpisodes","params": {"properties": ["file"]},"id": "1"}
get_movies = {"jsonrpc": "2.0",'id': 1, "method": "VideoLibrary.GetMovies",   "params": { "properties" : ["file"] }}

str_ext = ['avi','mkv','mpg','mpeg','mp4','wmv','mov']
def_ext = [avi,mkv,mpg,mpeg,mp4,wmv,mov]

for i, v in enumerate(def_ext):
	if v:
		extensions.append(str_ext[i])

log(extensions)




def jq(query):
	xbmc_request = json.dumps(query)
	#log(xbmc_request)
	result = xbmc.executeJSONRPC(xbmc_request)
	#log(result)
	return json.loads(result)['result']


def filter_file(full_file, extensions):
	global search
	global searchwords

	# check file extension
	fileName, fileExtension = os.path.splitext(full_file)

	if not fileExtension:
		log('no extension')
		return

	if fileExtension[1:] not in extensions:
		log(str(fileExtension[1:]) + ' not in allowable extensions')
		return

	if size != 'off':
		# check file size
		fsize = os.stat(full_file).st_size
		if fsize < size:
			log(str(fsize) + ' too small')
			return

	path, filenom = os.path.split(fileName)

	if search:
		if any(word.lower() not in filenom.lower() for word in searchwords):
			return

	return [filenom,fileExtension,path,full_file]


def filter_list():
	global searchwords

	new_list = []

	with open(cachefile,'r') as f:
		l = f.readlines()

		for af in l:
			fileName, fileExtension = os.path.splitext(af)
			path, filenom = os.path.split(fileName)

			if all(word.lower() in filenom.lower() for word in searchwords) and [filenom,fileExtension,path,af] not in new_list:
				new_list.append([filenom,fileExtension,path,af])
					
	return new_list


def scan_files(library_paths, extensions):
	# get all the video source directories
	# traverse them, get all the file names

	all_files = []
	files = []
	dirs = []

	q = {"jsonrpc": "2.0","id": 1, "method": "Files.GetSources","params": {"media": "video"}}
	res = jq(q)
	if 'sources' in res and res['sources']:
		for s in res['sources']:
			dirs.append(s['file'])

	count = 0
	while dirs:
		base_path = dirs[0]
		q = {"jsonrpc": "2.0","id": 1, "method": "Files.GetDirectory","params": {"directory":"", "media": "files", "properties":["file"]}}
		q['params']['directory'] = base_path
		res = jq(q)
		##log(str(base_path) + ' contains files')
		##log(res)
		del dirs[0]

		if 'files' in res and res['files']:
			for f in res['files']:
				if f['filetype'] == 'directory':
					if f['file'] not in dirs:
						dirs.append(f['file'])
				else:
					full_file = os.path.join(base_path,f['file'])
					all_files.append(full_file)

					count += 1
					if count % 50 == 0:
						progress.update(0,lang(32062),f['file'])


					if full_file in library_paths:
						continue

					file_tup = filter_file(full_file, extensions)
					if not file_tup:
						continue

					if file_tup not in files:
						files.append(file_tup)

	for x in files:
		#log(str(x[3]) + '\n')
		pass

	with open(cachefile, 'w+') as f:
		for a in all_files:
			f.write(a + '\n')

	return files


def scan_library():
	library_paths = []
	res = jq(eps_query)
	progress.update(0,lang(32063))
	if 'episodes' in res and res['episodes']:
		for ep in res['episodes']:
			if 'file' in ep and ep['file']:

				# insert rar/zip fix here
				library_paths.append(ep['file'])
	return library_paths


def send_output(recipient, files):
	paths = [x[3] for x in files]
	paths.sort(key = lambda y : y.lower())

	if to_email and address:
		try:

			#body = '<table border="1">'
			body = '<table>'

			for x in paths:
				body += '<tr><td>%s</td></tr>' % x
			body += '</table>'

			msg = MIMEText(body, 'html')
			msg['Subject'] = lang(32064)
			msg['From'] = 'Script.LooseFiles'
			msg['To'] = recipient
			msg['X-Mailer'] = lang(32064)

			smtp = smtplib.SMTP('gmail-smtp-in.l.google.com')
			smtp.sendmail(msg['From'], msg['To'], msg.as_string(9))
			smtp.quit()
			log('email sent')

		except:
			pass

	if to_disk and location:
		try:
			with open(os.path.join(location,'LooseFilesOutput.txt'), 'w') as f:
				for x in paths:
					f.write(str(x) + '\n')
		except:
			pass


class yGUI(xbmcgui.WindowXMLDialog):

	def __init__(self, strXMLname, strFallbackPath, strDefaultName, data=[]):
		self.data = data
		self.data.sort(key = lambda y : y[0].lower())
		self.running = True
		self.playing = False
		self.refresh = False
		self.change = False


	def onInit(self):
		log('window_init')
		self.ok = self.getControl(5)
		self.ok.setLabel(lang(32067))
		self.hdg = self.getControl(1)
		self.hdg.setLabel(lang(32068))
		self.hdg.setVisible(True)
		self.name_list = self.getControl(6)
		self.name_list.reset()
		self.x = self.getControl(3)
		self.x.setVisible(False)

		self.itemcount = 0

		for i, file_tup in enumerate(self.data):
			f = file_tup[3]

			# thumbs not working.
			#get_thumb = jq('{ "jsonrpc": "2.0", "method": "Files.GetFileDetails", "params": { "file": "C:\testTV\Air\Season1\Air S01E14 fartsjesus.avi", "media": "files", "properties": ["thumbnail"] } , "id": 49152 }' )
			#self.thumb = os.path.join(THUMBS_CACHE_PATH,xbmc.getCacheThumbName(f)[0],xbmc.getCacheThumbName(f))


			self.title  = file_tup[0]
			self.tmp    = xbmcgui.ListItem(label=self.title) #, thumbnailImage=self.thumb)
			self.name_list.addItem(self.tmp)
			self.itemcount += 1

			if i in items_selected:
				self.name_list.getListItem(i).select(True)

		self.ok.controlRight(self.name_list)
		self.setFocus(self.name_list)

		log('window_init_End')


	def onAction(self, action):
		actionID = action.getId()
		if (actionID in (10, 92)):
			#self.close()
			self.running = False

	def process_itemlist(self, set_to):
		for itm in range(self.item_count):
			if set_to == True:
				self.name_list.getListItem(itm).select(True)
			else:
				self.name_list.getListItem(itm).select(False)

	def onClick(self, controlID):
		log('controlid = ' + str(controlID))
		self.pos    = self.name_list.getSelectedPosition()
		log('position selected = ' + str(self.pos))

		if controlID == 5:

			self.running = False

		elif controlID in [117, 101] and not contextagogone:
			log('context menu')

			contextagogone = True
			myContext = contextwindow('contextwindow.xml', scriptPath, 'Default')
			myContext.doModal()

			if self.contextoption:
				if self.contextoption == 110:
					self.rename()
				elif self.contextoption == 220:
					self.move()

			del myContext
			contextagogone = False
		else:

			# play the video
			self.play()


	def onAction(self, Action):

		contextagogone = False

		if Action in [10,92]:
			self.close()

		elif Action in [117, 101] and not contextagogone:
			log('context menu')
	
			self.pos    = self.name_list.getSelectedPosition()

			contextagogone = True
			myContext = contextwindow('contextwindow.xml', scriptPath, 'Default')
			myContext.doModal()

			if myContext.contextoption:
				if myContext.contextoption == 110:
					self.rename()
				elif myContext.contextoption == 220:
					self.move()

			del myContext





	def play(self):
		self.pos    = self.name_list.getSelectedPosition()
		avi = self.data[self.pos][3].replace("\\","\\\\")
		log(avi)
		xbmc.Player().play(avi)
		self.playing = True


	def move(self):
		new_location = dialog.browse(3,lang(32074), 'videos','', False, False, self.data[self.pos][2])
		if new_location:

			new_full_path = os.path.join(new_location,self.data[self.pos][0]+self.data[self.pos][1])

			try:
				shutil.move( self.data[self.pos][3] , new_full_path )
			except IOError:
				# on error escape, notify via dialog.ok
				log('permission error')
				dialog.ok('Loose Files',lang(32073))
			else:

				# change labels
				f[self.pos][2] = new_location
				f[self.pos][3] = new_full_path

				# change the item to selected
				items_selected.append(self.pos)

				self.change = True

				myWindow.refresh = True


	def rename(self):
		log(self.data[self.pos][0])
		choose_name = xbmc.Keyboard(self.data[self.pos][0],lang(32075))
		choose_name.doModal()
		if choose_name.isConfirmed():
			are_you_sure = dialog.yesno(lang(32076) % self.data[self.pos][0],lang(32077),'%s' % choose_name.getText())
			if are_you_sure:
				log('yes, im sure')
				new_full_path = os.path.join(self.data[self.pos][2],choose_name.getText()+self.data[self.pos][1])

				log(self.data[self.pos][3])
				log(new_full_path)

				# insert rename function here
				try:
					shutil.move( self.data[self.pos][3] , new_full_path )
				except IOError:
					# on error escape, notify via dialog.ok
					log('permission error')
					dialog.ok('Loose Files',lang(32073))
				else:

					# change labels
					f[self.pos][0] = choose_name.getText()
					f[self.pos][3] = new_full_path

					# change the item to selected
					items_selected.append(self.pos)

					self.change = True

					myWindow.refresh = True


class lfmenu(xbmcgui.WindowXMLDialog):

	def onInit(self):
		log('window_init')
		global searchstring
		global rescan
		global search

		self.getControl(10).setLabel(lang(32083))
		self.getControl(1110).setLabel(lang(32084))
		self.getControl(1120).setLabel(lang(32085))
		self.getControl(1130).setLabel(lang(32086))

		log('window_init_End')

	def onAction(self, action):
		actionID = action.getId()
		if (actionID in (10, 92)):
			global bail
			bail = True
			self.close()

	def onClick(self, controlID):
		global searchstring
		global rescan
		global search

		if controlID == 10:
			searchstring = ''
			search = False
			self.close()
		elif controlID == 1110:
			search = 'Loose'
			self.close()
		elif controlID == 1120:
			search = 'All'
			self.close()
		elif controlID == 1130:
			cont = self.getControl(1130)
			if cont.getLabel() == lang(32086):
				cont.setLabel(lang(32087))
				rescan = False
			else:
				cont.setLabel(lang(32086))
				rescan = True


class searchwindow(xbmcgui.WindowXMLDialog):

	def onInit(self):
		log('window_init')
		self.prevs = []

		self.getControl(10).setLabel(lang(32080))

		with open(searchfile, 'a+') as f:
			self.prevtot = f.readlines()

			self.prevs = [x.rstrip('\n') for x in self.prevtot]

		self.controls = [1001,1002,1003,1004,1005,1006,1007,1008,1009,1010]
		for c in self.controls[len(self.prevs):]:
			self.getControl(c).setEnabled(False)
			self.getControl(c).setVisible(False)

		if self.prevs:
			for i, c in enumerate(self.controls[:len(self.prevs)]):
				self.getControl(c).setLabel(self.prevs[i])

		self.getControl(220).setEnabled(False)

		log('window_init_End')


	def onClick(self, controlID):

		global searchstring

		if controlID == 10:
			searchstring = dialog.input('New Search')
		elif controlID == 220:
			pass
		elif controlID in self.controls:
			searchstring = self.getControl(controlID).getLabel()
		self.save_search(searchstring)
		self.close()



	def onAction(self, action):
		actionID = action.getId()
		if (actionID in (10, 92)):
			global bail
			bail = True
			self.close()

	def save_search(self,ss):
		try:
			self.prevs.remove(ss)
		except:
			pass
		new = [ss] + self.prevs
		new = [x.rstrip('\n') for x in new]
		with open(searchfile, 'w+') as f:
			for i, s in enumerate(new):
				if i<10:
					f.write(s + '\n')


class contextwindow(xbmcgui.WindowXMLDialog):
	
	def onInit(self):
		self.started = True
		self.contextoption = ''	

		self.getControl(110).setLabel(lang(32081))
		self.getControl(220).setLabel(lang(32082))


		self.setFocus(self.getControl(110))

	def onClick(self, controlID):
		self.contextoption = controlID
		self.close()


if __name__ == "__main__":
	log('started')

	myMenu = lfmenu("lfmenu.xml", scriptPath, 'Default')
	myMenu.doModal()

	del myMenu

	if not bail:

		if search:
			mySearch = searchwindow('searchmenu.xml', scriptPath, 'Default')
			mySearch.doModal()
			del mySearch

		if not bail:

			# progress dialog
			progress.create('Loose Files',lang(32061))
			
			# get all the files from the library
			log('search type= ' + str(search))

			if search == 'All':
				lp = []
			else:
				lp = scan_library()

			# clean searchstring and break into individual words
			pattern = r'(\w*)'
			sw = re.findall(pattern,searchstring)
			searchwords = [s for s in sw if s]

			log('searchwords = ' +str(searchwords))

			# get all the files from sources that meet criteria
			if rescan:
				log('rescanning')
				f = scan_files(lp, extensions)
				log(f)
			else:
				f = filter_list()
				log('not rescanning')
				log(f)
				if not f:
					log('list empty, rescanning')
					f = scan_files(lp, extensions)

			# send the output
			if not search:
				send_output(address, f)

			# close the progress dialog
			progress.close()


			# build the file display window
			dialog.ok('Loose Files',lang(32065),lang(32066) % len(f))
			myWindow = yGUI("DialogSelect.xml", scriptPath, 'Default', data=f)
			myWindow.show()

			# create player to identify when file is playing
			wait_for_player = False
			myPlayer = xbmc.Player()

			# loop to catch actions of file display window
			while myWindow.running:
				xbmc.sleep(100)

				# if the file is playing then close the file display window
				if myWindow.playing == True:
					myWindow.close()
					myWindow.playing = False
					wait_for_player = True
					log('waiting for player')

				# if the file is playing then wait for it to stop then show the window again
				if wait_for_player:
					log('now waiting')
					if not myPlayer.isPlaying():
						myWindow.show()
						wait_for_player = False
						log('player stopped')

				# closes and reopens the window 
				if myWindow.refresh == True:
					log('refreshing')
					myWindow.refresh = False
					myWindow.close()
					xbmc.sleep(5)
					myWindow.show()


			# upon close, and if there are changes, ask the user if they want to refresh the db
			if myWindow.change:
				log('changes: update library')
				update_lib = dialog.yesno('Loose Files',lang(32078))
				if update_lib:
					xbmc.executebuiltin('UpdateLibrary(video)')

			del myWindow
			del myPlayer

	log('Exited') #'''
