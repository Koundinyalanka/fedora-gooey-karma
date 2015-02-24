# -*- coding:  utf-8 -*-

#    Fedora Gooey Karma prototype
#    based on the https://github.com/mkrizek/fedora-gooey-karma
#
#    Copyright (C) 2013
#
#    This program is free software: you can redistribute it and/or modify
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#    Author: Branislav Blaskovic <branislav@blaskovic.sk>

import threading

from fedora.client import AuthError
from fedora.client import ServerError
from fedora.client.bodhi import BodhiClient

from idlequeue import *

class SendKarma(threading.Thread):
    def __init__(self, package, username, password, message, karma, main_thread, parent=None):
        #super(SendKarma, self).__init__(parent)
        threading.Thread.__init__(self)
        self.package = package
        self.username = username
        self.password = password
        self.message = message
        self.karma = karma
        self.main_thread = main_thread

    def run(self):
        bc = BodhiClient()
        bc.username = self.username
        bc.password = self.password

        # Try send it 3 times if ServerError occours
        for retry in range(3):
            try:
                # Send comment to bodhi
                bc.comment(self.package["title"], self.message, karma=self.karma)
                message = "Comment submitted successfully."
                message2 = ("Reloading bodhi update for "
                           + str(self.package['itemlist_name']) + "...")
                main_thread_call(self.main_thread.add_status_item, message)
                main_thread_call(self.main_thread.add_status_item, message2)

                # Reload bodhi update
                main_thread_call(self.main_thread.bodhi_workers_queue.put,
                         ['package_update', self.package['dnf_package']])
                # Clean up after sending
                main_thread_call(self.main_thread.sending_done, self.username, self.password)
                return
            except AuthError:
                message = "Invalid username or password. Please try again."
                main_thread_call(self.main_thread.add_status_item,
                         message)
                break
            except ServerError, e:
                message = "Server error %s" % str(e)
                main_thread_call(self.main_thread.add_status_item,
                         message)

        # In case of errors, return button and others back
        main_thread_call(self.main_thread.sending_done, self.username, self.password)

# vim: set expandtab ts=4 sts=4 sw=4 :
