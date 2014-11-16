#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2014 KenV99
#
# This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import stat
import time
from cPickle import dump, load

if 'win' in sys.platform:
    isKodi = 'xbmc' in sys.executable.lower() or 'kodi' in sys.executable.lower()
else:
    isKodi = True
if isKodi:
    import xbmcaddon

    path_to_required_modules = os.path.join(xbmcaddon.Addon('script.module.ipc').getAddonInfo('path'), 'lib')
    if path_to_required_modules not in sys.path:
        sys.path.insert(0, path_to_required_modules)

import pyro4

IPCERROR_UKNOWN = 0
IPCERROR_NO_VALUE_FOUND = 1
IPCERROR_USE_CACHED_COPY = 2
IPCERROR_SERVER_TIMEOUT = 3
IPCERROR_CONNECTION_CLOSED = 4
IPCERROR_NONSERIALIZABLE = 5


class DataObjectBase(object):
    def __init__(self):
        self.ts = None
        self.value = None


class DataObject(DataObjectBase):
    def __init__(self, dox):
        super(DataObject, self).__init__()
        self.ts = dox.ts
        self.value = dox.value


class DataObjectX(DataObjectBase):
    def __init__(self, value):
        super(DataObjectX, self).__init__()
        self.ts = time.time()
        self.value = value
        self.requestors = {}


class DataObjects(object):
    def __init__(self):
        self.__odict = {}

    @pyro4.oneway
    def set(self, name, value, author):
        dox = DataObjectX(value)
        idx = (str(author), str(name))
        self.__odict[idx] = dox

    def get(self, requestor, name, author, force=False):
        idx = (str(author), str(name))
        if idx in self.__odict:
            dox = self.__odict[idx]
            do = DataObject(dox)
            if requestor in dox.requestors and force is False:
                if dox.requestors[requestor] == dox.ts:
                    return chr(IPCERROR_USE_CACHED_COPY)
                else:
                    dox.requestors[requestor] = dox.ts
                    return do
            else:
                dox.requestors[requestor] = dox.ts
                return do
        else:
            return chr(IPCERROR_NO_VALUE_FOUND)

    def delete(self, name, author):
        idx = (str(author), str(name))
        if idx in self.__odict:
            dox = self.__odict.pop(idx)
            do = DataObject(dox)
            return do
        else:
            return chr(IPCERROR_NO_VALUE_FOUND)

    def get_data_list(self, author=None):
        dl = {}
        for key in self.__odict.keys():
            if key[0] == author or author is None:
                if key[0] in dl:
                    dl[key[0]].append(key[1])
                else:
                    dl[key[0]] = [key[1]]
        return dl

    @pyro4.oneway
    def clearall(self):
        self.__odict = {}

    def savedata(self, author, fn):
        default_dir_mod = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        default_file_mod = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
        save = {}
        for key in self.__odict:
            if key[0] == author:
                tmp = self.__odict[key]
                tmp.requestors = {}
                save[key] = tmp
        try:
            path = os.path.dirname(fn)
            os.chmod(path, default_dir_mod)
            output = open(fn, 'wb')
            dump(save, output, -1)
            output.close()
            os.chmod(fn, default_file_mod)
            return True
        except:
            return False

    def restoredata(self, author, fn):
        default_dir_mod = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH
        default_file_mod = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH
        try:
            path = os.path.dirname(fn)
            os.chmod(path, default_dir_mod)
            os.chmod(fn, default_file_mod)
            inputf = open(fn, 'rb')
            restore = load(inputf)
            inputf.close()
        except Exception:
            return False
        else:
            for key in restore:
                if key[0] == author:
                    self.__odict[key] = restore[key]
            return True

    @pyro4.oneway
    def clearcache(self, requestor):
        for key in self.__odict:
            if requestor in self.__odict[key].requestors:
                del self.__odict[key].requestors[requestor]