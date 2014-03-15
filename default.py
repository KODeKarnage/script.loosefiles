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
#  This script uses significant elements from service.skin.widgets
#  by Martijn & phil65

import xbmc
import json
import xbmcaddon
import xbmcgui
import os
import sys
import smtplib
from email.mime.text import MIMEText

__addon__   = xbmcaddon.Addon()
__addonid__ = __addon__.getAddonInfo('id')
__setting__ = __addon__.getSetting
lang        = __addon__.getLocalizedString
progress    = xbmcgui.DialogProgress()
dialog = xbmcgui.Dialog()

progress.create('Loose Files',lang(32061))

extensions    = []


def log(message):
    xbmc.log(msg = 'LooseFiles -=- ' + str(message))

def correct_bool(boolean):
    return True if boolean == 'true' else False

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
    result = xbmc.executeJSONRPC(xbmc_request)
    return json.loads(result)['result']


def filter_file(full_file, extensions):

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
    return filenom,fileExtension,fileName,full_file


def get_all_paths(library_paths, extensions):
    # get all the video source directories
    # traverse them, get all the file names

    files = []
    dirs = []

    q = {"jsonrpc": "2.0","id": 1, "method": "Files.GetSources","params": {"media": "video"}}
    res = jq(q)
    if 'sources' in res and res['sources']:
        for s in res['sources']:
            dirs.append(s['file'])
    count = 0
    while dirs:
        w = os.walk(dirs[0])
        del dirs[0]
        for r,d,f in w:
            for folder in d:
                new_dir = os.path.join(r,folder)
                if new_dir not in dirs:
                    dirs.append(new_dir)
            for fyle in f:
                full_file = os.path.join(r,fyle)

                count += 1
                if count % 50 == 0:
                    progress.update(0,lang(32062),r)

                if full_file in library_paths:
                    continue

                file_tup = filter_file(full_file, extensions)
                if not file_tup:
                    continue
                files.append(file_tup)

    for x in files:
        log(str(x[3]) + '\n')

    return files

def get_library_paths():
    library_paths = []
    res = jq(eps_query)
    progress.update(0,lang(32063))
    if 'episodes' in res and res['episodes']:
        for ep in res['episodes']:
            if 'file' in ep and ep['file']:
                library_paths.append(ep['file'])
    return library_paths

def send_output(recipient, files):
    paths = [x[3] for x in files]
    paths = list(set(paths))
    paths.sort(key = lambda y : y.lower())

    progress.close()

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

    return len(paths)

if __name__ == "__main__":
    lp = get_library_paths()
    f = get_all_paths(lp, extensions)
    orphans = send_output(address, f)
    dialog.ok('Loose Files',lang(32065),lang(32066) % orphans)
