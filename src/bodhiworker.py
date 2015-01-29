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
#    Author: Tomas Meszaros <exo@tty.sk>

import os
import os.path
import re
import subprocess
from PySide import QtCore
from fedora.client import BodhiClient
from idlequeue import *
import itertools

class BodhiWorker(QtCore.QThread):

    bodhi_query_done = QtCore.Signal(object)

    def __init__(self, worker_name, queue, main_thread, parent=None):
        super(BodhiWorker, self).__init__(parent)
        self.queue = queue

        self.worker_name = worker_name
        self.main_thread = main_thread

        bodhi_url = 'https://admin.fedoraproject.org/updates/'
        self.bc = BodhiClient(bodhi_url, useragent="Fedora Gooey Karma", debug=None)
        self.installed_packages = []
        self.process_list = self.get_proc_list()

    def run(self):
        while True:
            action, data = self.queue.get()

            if action == 'package_update':
                package = data
                # Get info about this build
                variant, bodhi_update = self.__bodhi_query_pkg(package)
                if bodhi_update:
                    # If we get info from bodhi, prepare some info
                    # and send it to GUI
                    bodhi_update['bugs_by_id'] = self.__get_bugs_by_id(bodhi_update)
                    bodhi_update['bodhi_url'] = self.__get_url(bodhi_update)
                    bodhi_update['test_cases'] = self.__get_testcases(bodhi_update)
                    bodhi_update['formatted_comments'] = self.__get_comments(bodhi_update)
                    bodhi_update['relevant_packages'] = self.__get_relevant_packages(package.name)
                    bodhi_update['parsed_nvr'] = self.__parse_nvr(bodhi_update['itemlist_name'])
                    bodhi_update['currently_running'] = []

                    # Is something from this package running?
                    ## Find package in installed packages
                    pkg = self.installed_packages.filter(name=bodhi_update['parsed_nvr']['name'])
                    fname2pkg = {fname: pkg.filter(file=fname) for fname in self.process_list}                            
                    # Append binary to list 
                    for key in fname2pkg.iteritems():
                        bodhi_update['currently_running'].append(key[0]) 
                        break            

                    # Send it to main thread
                    main_thread_call(self.main_thread.bodhi_process_result,
                             [variant, bodhi_update])
                else:
                    # If there is no info from Bodhi, send info to main thread to adjust progress bar
                    main_thread_call(self.main_thread.bodhi_process_result,
                             ['progress_only', None])

            elif action == 'set_installed_packages':
                # Is this item for this worker?
                # data[0] worker_name, data[1] installed_packages
                if self.worker_name != data[0]:
                    self.queue.put([action, data])

                self.installed_packages = data[1]
            else:
                print "Bodhi worker: Unknown action"

            self.queue.task_done()

    def __parse_nvr(self, nvr):
        splitted = nvr.split('-')

        # We need at least 3 items
        if len(splitted) < 3:
            return

        # Get items from array
        name = '-'.join(splitted[0:(len(splitted)-2)])
        version = splitted[-2]
        release = splitted[-1]

        return {'name':name, 'version':version, 'release':release}

    def __get_relevant_packages(self, package):
        pkgs = {}
        pkgs['desktop'] = {}
        pkgs['others'] = {}

        # TODO: Should be rewritten to pure python code
        try:
            p = subprocess.Popen('repoquery -q --qf "%{name}" --whatrequires ' + str(package),
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT)

            for line in p.stdout.readlines():
                name = line.strip()
                installed_pkg = self.installed_packages.filter(name=name)
                # Which category is it?
                category = 'others'
                ## Search for desktop file
                desktop_pkg = [filename for filename in itertools.chain.from_iterable(installed_pkg)
                if re.search('^/usr/share/applications/(.*).desktop$', filename)]
                if desktop_pkg!=[]: 
                    category = 'desktop'
                    break
						
                pkgs[category][name] = installed_pkg
        except IOError, e:
            print "BodhiWorker.__get_relevant_packages: %s" % str(e)

        return pkgs

    def __bodhi_query_pkg(self, package):
        # Search by name
        rel = None
        for part in package.release.split('.'):
            if re.search("^fc[0-9]+$", part):
                rel = part.replace('fc','F')

        # Correct release not found
        if not rel:
            return [None, None]

        pkg_update = self.bc.query(release=rel, package=package.name, status='testing')['updates']

        if pkg_update:
            for update in pkg_update:
                for build in update['builds']:
                    # Does this build match with our current build?
                    package.nvr = package.name + '-' + package.version + '-' + package.release
                    if build['nvr'] == package.nvr:
                        update['itemlist_name'] = package.nvr
                        update['yum_package'] = package
                        update['variant'] = 'installed'
                        return ['installed', update]
                    # If not, there could be newer version
                    elif build.package.name == package.name:
                        update['itemlist_name'] = build['nvr']
                        update['yum_package'] = build.package
                        update['variant'] = 'available'
                        return ['available', update]

        return [None, None]

    def __get_bugs_by_id(self, data):
        # Prepare bugs for easier use
        bugs = {}
        if len(data['bugs']):
            for bug in data['bugs']:
                bugs[bug['bz_id']] = bug['title']

        return bugs

    def __get_url(self, data):
        return 'https://admin.fedoraproject.org/updates/' + str(data['updateid'])

    def __get_testcases(self, data):
        if data['nagged'] is not None:
            if 'test_cases' in data['nagged']:
                test_cases = data['nagged']['test_cases']
                for i in range(len(test_cases)):
                    test_cases[i] = test_cases[i].replace("QA:Testcase ", "")
                return test_cases
        # when package does not have test cases
        return []

    def __get_comments(self, data):
        # Get comments and rewrite it to better formatted dict
        comments = []
        i = 1
        if len(data['comments']):
            for comment in data['comments']:
                anonymous = ""
                if comment['anonymous']:
                    anonymous = " (unauthenticated)"
                comments.append({'ord':i,
                                 'text':comment['text'],
                                 'author':comment['author'] + anonymous,
                                 'karma':comment['karma']})
                i = i + 1

        return comments

    def which(filename):
        # Get full path to relative bin name
        locations = os.environ.get("PATH").split(os.pathsep)
        candidates = []
        for location in locations:
            candidate = os.path.join(location, filename)
            if os.path.isfile(candidate):
                candidates.append(candidate)
        return candidates

    def get_proc_list(self):
        p = subprocess.Popen(['/bin/ps', 'aux'], shell=False, stdout=subprocess.PIPE)
        p.stdout.readline()
        plist = []

        # Get processes, find their full path and so
        for line in p.stdout:
            try:
                process = re.split(' *', line.strip())[10]

                # Not a process what we are looking for
                if process[0] == '[':
                    continue
                # We need to get full path to process from PATH variable
                elif process[0] != '/':
                    process = self.which(process)[0]

                # Add it to list
                if process not in plist:
                    plist.append(process)

            except:
                continue

        return plist

# vim: set expandtab ts=4 sts=4 sw=4 :
