#!/usr/bin/python2 -tt
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


import sys
import webbrowser
import yum
import multiprocessing
import Queue
import rpm
from fedora.client import AuthError
from fedora.client import ServerError
from fedora.client.bodhi import BodhiClient
from yum.misc import getCacheDir
from yum import Errors
from PySide import QtCore
from PySide import QtGui

from mainwindow_gui import Ui_MainWindow
from packagesworker import PackagesWorker 
from bodhiworker import BodhiWorker

class MainWindow(QtGui.QMainWindow):

    __BUGZILLA_REDHAT_URL = "http://bugzilla.redhat.com/show_bug.cgi?id="
    __FEDORAPEOPLE_TESTCASE_URL = "https://fedoraproject.org/wiki/QA:Testcase_"
    __FEDORA_RELEASES = [ 'Fedora 19', 'Fedora 18', 'Fedora 17' ]
    __BODHI_WORKERS_COUNT = 15

    def __init__(self, parent=None):
        # GUI
        super(MainWindow, self).__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Prepare Queues
        self.bodhi_workers_queue = Queue.Queue()
        self.pkg_worker_queue = Queue.Queue()

        # Prepare ui
        self.rpmTS = rpm.TransactionSet()
        self.__show_karma_widget_comment()
        self.__hide_karma_name_filter()
        self.__load_and_set_fedora_releases()

        # YumBase and cache
        self.yb = yum.YumBase()
        cachedir = getCacheDir()
        self.yb.repos.setCacheDir(cachedir)

        self.pkg_available = {}
        self.pkg_installed = {}

        # Holders of data
        self.__installed_packages = {}
        self.__bodhi_updates = {}


        # Connects
        self.ui.actionQuit.triggered.connect(QtCore.QCoreApplication.instance().quit)
        self.ui.pkgList.currentItemChanged.connect(self.__show_package_detail)
        self.ui.searchEdit.textChanged.connect(self.__search_pkg)
        self.ui.karmaUsernameEdit.textChanged.connect(self.__filter_already_submitted)
        self.ui.installedBtn.clicked.connect(self.__show_installed)
        self.ui.availableBtn.clicked.connect(self.__show_available)
        self.ui.sendBtn.clicked.connect(self.__show_karma_widget_auth)
        self.ui.okBtn.clicked.connect(self.__send_comment)
        self.ui.cancelBtn.clicked.connect(self.__show_karma_widget_comment)
        self.ui.loadPackagesBtn.clicked.connect(self.__start_pkg_worker)
        self.ui.releaseComboBox.currentIndexChanged.connect(self.__refresh_package_list)
        self.ui.treeWidget_bugs.itemClicked.connect(self.__show_bug_in_browser)
        self.ui.treeWidget_test_cases.itemClicked.connect(self.__show_testcase_in_browser)
        self.ui.karmaCheckBox.stateChanged.connect(self.__filter_already_submitted)

        # Prepare threads
        self.bodhi_workers = []
        for i in range(self.__BODHI_WORKERS_COUNT):
            b = BodhiWorker(self.bodhi_workers_queue)
            b.bodhi_query_done.connect(self.__bodhi_add_update)
            b.start()
            self.bodhi_workers.append(b)

        self.pkg_worker = PackagesWorker(self.pkg_worker_queue, self.bodhi_workers_queue)
        self.pkg_worker.set_installed_packages.connect(self.__set_installed_packages)
        self.pkg_worker.start()

        # Pkg worker threads
        self.pkg_worker.load_available_packages_done.connect(self.__save_available_pkg_list)
        self.pkg_worker.load_available_packages_start.connect(self.__available_pkg_list_loading_info)
        self.pkg_worker.load_installed_packages_done.connect(self.__save_installed_pkg_list)
        self.pkg_worker.load_installed_packages_start.connect(self.__installed_pkg_list_loading_info)

    def __bodhi_add_update(self, bodhi_update):
        self.__bodhi_updates[bodhi_update['itemlist_name']] = bodhi_update
        self.ui.pkgList.addItem(bodhi_update['itemlist_name'])

    def __set_installed_packages(self, packages):
        print str(len(packages)) + " installed packages on system."
        self.__installed_packages = packages

    def __load_and_set_fedora_releases(self):
        # Load fedora-release version
        packages = self.rpmTS.dbMatch('name', 'fedora-release')
        for package in packages:
            break

        # Fill in current release as first
        self.ui.releaseComboBox.addItem('Fedora ' + str(package['version']))

        # Fill combo box
        for release in self.__FEDORA_RELEASES:
            # Skip current release 
            if package['version'] == release.split()[-1]:
                continue

            self.ui.releaseComboBox.addItem(release)

    def __start_pkg_worker(self):
        # Get release and put it to queue
        # Package worker will get info about it
        releasever = self.ui.releaseComboBox.currentText().split()[-1]
        self.pkg_worker_queue.put(releasever)

    def __available_pkg_list_loading_info(self):
        release = self.ui.releaseComboBox.currentText()
        message = "Please wait... Loading all available packages. [%s]" % release
        self.ui.statusBar.showMessage(message)

    def __installed_pkg_list_loading_info(self):
        release = self.ui.releaseComboBox.currentText()
        message = "Please wait... Loading all installed packages. [%s]" % release
        self.ui.statusBar.showMessage(message)

    def __show_bug_in_browser(self):
        bug_id = self.ui.treeWidget_bugs.currentItem().text(0)
        webbrowser.open_new_tab("%s%s" % (self.__BUGZILLA_REDHAT_URL, bug_id))

    def __show_testcase_in_browser(self):
        testcase_name = self.ui.treeWidget_test_cases.currentItem().text(0).replace(' ', '_')
        webbrowser.open_new_tab("%s%s" % (self.__FEDORAPEOPLE_TESTCASE_URL, testcase_name))

    def __refresh_package_list(self):
        if self.ui.installedBtn.isChecked():
            self.__show_installed()
        elif self.ui.availableBtn.isChecked():
            self.__show_available()
        elif not self.ui.installedBtn.isChecked() and not self.ui.availableBtn.isChecked():
            self.ui.installedBtn.setChecked(True)
            self.__show_installed()

    def __search_pkg(self):
        # used for searchEdit searching
        if not self.ui.installedBtn.isChecked() and not self.ui.availableBtn.isChecked():
            return
        if self.__get_current_set() is None:
            return

        phrase = str(self.ui.searchEdit.text())
        if not phrase:
            if self.ui.karmaCheckBox.isChecked() and self.ui.karmaUsernameEdit.text() and self.ui.installedBtn.isChecked():
                self.__filter_already_submitted()
            else:
                self.__populate_pkgList()
            return

        self.ui.pkgList.clear()
        for build in self.__get_current_set().builds:
            if build['nvr'].startswith(phrase):
                if self.ui.installedBtn.isChecked():
                    if 'installed' in build:
                        self.ui.pkgList.addItem(build['nvr'])
                elif self.ui.availableBtn.isChecked():
                    self.ui.pkgList.addItem(build['nvr'])

    def __save_available_pkg_list(self, pkg_object):
        self.pkg_available[pkg_object[0]] = pkg_object[1]
        releasever = self.ui.releaseComboBox.currentText().split()[-1]
        if releasever == pkg_object[0]:
            self.ui.availableBtn.setChecked(True)
            self.__show_available()
        self.ui.statusBar.clearMessage()
        message = "All available packages has been loaded. [Fedora %s]" % pkg_object[0]
        self.ui.statusBar.showMessage(message)
        self.ui.searchEdit.setEnabled(True)

    def __save_installed_pkg_list(self, pkg_object):
        message = "All installed packages has been loaded. [Fedora %s]" % pkg_object
        self.ui.statusBar.showMessage(message)
        self.ui.searchEdit.setEnabled(True)

    def __decode_dict(self, dictionary, decoding='utf-8', data_type=str):
        for key in dictionary:
            if isinstance(dictionary[key], data_type):
                dictionary[key] = dictionary[key].decode(decoding)

    def __show_karma_widget_auth(self):
        self.ui.usernameEdit.show()
        self.ui.usernameEdit.setFocus()
        self.ui.passwordEdit.show()
        self.ui.okBtn.show()
        self.ui.cancelBtn.show()
        self.ui.commentEdit.hide()
        self.ui.karmaBox.hide()
        self.ui.sendBtn.hide()
        message = "Please enter FAS username and passowrd."
        self.ui.statusBar.showMessage(message)

    def __show_karma_widget_comment(self):
        self.ui.usernameEdit.hide()
        self.ui.passwordEdit.hide()
        self.ui.okBtn.hide()
        self.ui.cancelBtn.hide()
        self.ui.commentEdit.show()
        self.ui.karmaBox.show()
        self.ui.sendBtn.show()
        self.ui.statusBar.clearMessage()

    def __send_comment(self):
        comment = self.ui.commentEdit.text()
        karma = self.ui.karmaBox.currentText()
        update = None
        pkg_title = None

        if comment:
            pkg_title = self.__activated_pkgList_item_text()
            if pkg_title is not None:
                for key in self.__get_current_set().testing_builds:
                    if key == pkg_title:
                        update = self.__get_current_set().testing_builds[pkg_title]

        if update is None:
            message = "Comment not submitted: Could not get update from testing builds"
            self.ui.statusBar.showMessage(message)
            return
        if not self.ui.usernameEdit.text():
            message = "Please enter FAS username."
            self.ui.statusBar.showMessage(message)
            return
        if not self.ui.passwordEdit.text():
            message = "Please enter FAS password."
            self.ui.statusBar.showMessage(message)
            return

        bc = BodhiClient()
        bc.username = self.ui.usernameEdit.text()
        bc.password = self.ui.passwordEdit.text()

        message = "Processing... Wait please..."
        self.ui.statusBar.showMessage(message)

        for retry in range(3):
            try:
                result = bc.comment(update["title"], comment, karma=karma)
                message = "Comment submitted successfully."
                self.ui.statusBar.showMessage(message)
                # save comment and end
                self.__get_current_set().testing_builds[pkg_title] = result['update']
                return
            except AuthError:
                message = "Invalid username or password. Please try again."
                self.ui.statusBar.showMessage(message)
            except ServerError, e:
                message = "Server error %s" % str(e)
                self.ui.statusBar.showMessage(message)

    def __show_karma_name_filter(self):
        self.ui.karmaCheckBox.show()
        self.ui.karmaUsernameEdit.show()

    def __hide_karma_name_filter(self):
        self.ui.karmaCheckBox.hide()
        self.ui.karmaUsernameEdit.hide()

    def __filter_already_submitted(self):
        """ Add only those installed packages to the pkgList for which user did not
        submitted karma. (uses username from the karmaUsernameEdit)
        """
        if not self.ui.karmaCheckBox.isChecked() or not self.ui.karmaUsernameEdit.text():
            self.__populate_pkgList()
            return
        self.ui.pkgList.clear()

        for build in self.__get_current_set().builds:
            data = self.__get_current_set().testing_builds[build['nvr']]
            comments = self.__get_current_set().get_comments(data)
            already_submitted = False
            for comment in comments:
                if comment[1] == self.ui.karmaUsernameEdit.text():
                    already_submitted = True
                    break
            if not already_submitted:
                self.ui.pkgList.addItem(build['nvr'])

    def __populate_pkgList(self):
        self.ui.pkgList.clear()
        current_set = self.__get_current_set()
        if current_set is None:
            return
        for build in current_set.builds:
            if self.ui.installedBtn.isChecked() and 'installed' in build:
                self.ui.pkgList.addItem(build['nvr'])
            elif self.ui.availableBtn.isChecked():
                self.ui.pkgList.addItem(build['nvr'])

    def __show_installed(self):
        if self.ui.installedBtn.isChecked():
            self.__show_karma_name_filter()
        else:
            self.__hide_karma_name_filter()
        self.ui.availableBtn.setChecked(False)
        if self.ui.installedBtn.isChecked():
            try:
                self.__populate_pkgList()
                self.__search_pkg()
            except Exception, err:
                print "Packages are not ready yet. Please wait!"
                print err
        elif not self.ui.installedBtn.isChecked():
            self.ui.pkgList.clear()

    def __show_available(self):
        self.__hide_karma_name_filter()
        self.ui.installedBtn.setChecked(False)
        if self.ui.availableBtn.isChecked():
            try:
                self.__populate_pkgList()
                self.__search_pkg()
            except Exception, err:
                print "Packages are not ready yet. Please wait!"
                print err
        elif not self.ui.availableBtn.isChecked():
            self.ui.pkgList.clear()

    def __show_package_detail(self, pkg_item):
        """Shows package detail in the MainWindow.

        Updates all info in every widget when user click on the item in the pkgList.

        Args:
            pkg_item: A currently selected pkgList item widget.

        Returns:
            Returns when pkg_item is None.
        """
        if pkg_item is None:
            return

        text_browser_string = ""
        bodhi_update = self.__bodhi_updates[pkg_item.text()]

        ## title
        #self.ui.pkgNameLabel.setText(data['builds'][0]['nvr'])
        self.ui.pkgNameLabel.setText(bodhi_update['itemlist_name'])

        ## yum info
        yum_values = {}
        yum_format_string = (
            "\n        Yum Info\n"
            "        ========\n\n"
            "           Name: %(name)s\n"
            "           Arch: %(arch)s\n"
            "        Version: %(version)s\n"
            "        Release: %(release)s\n"
            "           Size: %(size)s\n"
            "           Repo: %(repo)s\n"
            "      From repo: %(from_repo)s\n"
            "        Summary: %(summary)s\n"
            "            URL: %(url)s\n"
            "        License: %(license)s\n\n"
            "    Description:\n"
            "    ------------\n\n"
            "%(description)s\n\n"
        )

        # Search for package in list of installed packages
        yum_pkg = None
        yum_pkg_deplist = None

        for yum_pkg in self.__installed_packages:
            if yum_pkg.nvr == pkg_item.text():
                break

        if yum_pkg is not None:
            # if we got yum package
            # fetch info from yum_pkg
            yum_values['name'] = yum_pkg.name
            yum_values['arch'] = yum_pkg.arch
            yum_values['version'] = yum_pkg.version
            yum_values['release'] = yum_pkg.release
            yum_values['size'] = yum_pkg.packagesize
            yum_values['repo'] = yum_pkg.repo
            yum_values['from_repo'] = yum_pkg.ui_from_repo
            yum_values['summary'] = yum_pkg.summary
            yum_values['url'] = yum_pkg.url
            yum_values['license'] = yum_pkg.license
            yum_values['description'] = yum_pkg.description
            # decode all strings found in yum_values to utf-8
            self.__decode_dict(yum_values)
            # map fetched yum info on the yum_format_string
            # add to the final browser string
            text_browser_string += yum_format_string % yum_values

            ## related packages
            self.ui.treeWidget_related_packages.clear()
            deplist = []

            try:
                deplist = self.yb.findDeps(yum_pkg_deplist)
            except Exception, e:
                print "_show_package_detail() error: %s" % e

            for key in deplist:
                for packages in deplist[key]:
                    pkg_name = deplist[key][packages][0]
                    pkg = QtGui.QTreeWidgetItem()
                    pkg.setText(0, str(pkg_name))
                    self.ui.treeWidget_related_packages.insertTopLevelItem(0, pkg)

        else:
            print "Not in installed packages"

        ## bodhi info
        bodhi_values = {}
        bodhi_format_string = (
            "\n      Bodhi Info\n"
            "      ==========\n\n"
            "         Status: %(status)s\n"
            "        Release: %(release)s\n"
            "      Update ID: %(updateid)s\n"
            "         Builds: %(builds)s"
            "      Requested: %(request)s\n"
            "         Pushed: %(pushed)s\n"
            " Date Submitted: %(date_submitted)s\n"
            "  Date Released: %(date_released)s\n"
            "      Submitted: %(submitter)s\n"
            "          Karma: %(karma)s\n"
            "   Stable Karma: %(stable_karma)s\n"
            " Unstable Karma: %(unstable_karma)s\n\n"
            "            URL: %(bodhi_url)s\n\n"
            "        Details:\n"
            "        --------\n\n"
            "%(notes)s\n"
        )

        bodhi_values['status'] = bodhi_update['status']
        bodhi_values['release'] = bodhi_update['release']['long_name']
        bodhi_values['updateid'] = bodhi_update['updateid']
        builds_list = bodhi_update['builds']
        if len(builds_list):
            build_num = 0
            builds_string = ""
            for build_item in builds_list:
                if not build_num:
                    # first build name
                    builds_string += "%s\n" % build_item['nvr']
                else:
                    # second and next builds
                    builds_string += "%s%s\n" % (17 * " ", build_item['nvr'])
                build_num += 1
            bodhi_values['builds'] = builds_string
        else:
            bodhi_values['builds'] = "None"
        bodhi_values['request'] = bodhi_update['request']
        bodhi_values['pushed'] = "True" if bodhi_update['date_pushed'] else "False"
        bodhi_values['date_submitted'] = bodhi_update['date_submitted']
        bodhi_values['date_released'] = bodhi_update['date_pushed']
        bodhi_values['submitter'] = bodhi_update['submitter']
        bodhi_values['karma'] = bodhi_update['karma']
        bodhi_values['stable_karma'] = bodhi_update['stable_karma']
        bodhi_values['unstable_karma'] = bodhi_update['unstable_karma']
        bodhi_values['notes'] = bodhi_update['notes']
        bodhi_values['bodhi_url'] = bodhi_update['bodhi_url']
        # decode all strings found in bodhi_values to utf-8
        self.__decode_dict(bodhi_values)
        # map fetched bodhi info on the bodhi_format_string
        # add to the final browser string
        text_browser_string += bodhi_format_string % bodhi_values
        # set final browser string text
        self.ui.textBrowser.setText(text_browser_string)

        ## bugs
        self.ui.treeWidget_bugs.clear()
        if bodhi_update['bugs_by_id']:
            for key in bodhi_update['bugs_by_id']:
                bug = QtGui.QTreeWidgetItem()
                bug.setText(0, str(key))
                bug.setText(1, str(bodhi_update['bugs_by_id'][key]))
                self.ui.treeWidget_bugs.insertTopLevelItem(0, bug)

        ## test cases
        self.ui.treeWidget_test_cases.clear()
        test_cases_list = bodhi_update['test_cases']
        if len(test_cases_list):
            for test_case_item in reversed(test_cases_list):
                tc = QtGui.QTreeWidgetItem()
                tc.setText(0, str(test_case_item))
                self.ui.treeWidget_test_cases.insertTopLevelItem(0, tc)

        ## feedback
        self.ui.treeWidget_feedback.clear()
        comments = bodhi_update['formatted_comments']
        if comments:
            for i in comments:
                comment = QtGui.QTreeWidgetItem()
                comment.setText(0, str(i[2]))
                comment.setText(1, i[1])
                comment.setText(2, i[0])
                self.ui.treeWidget_feedback.insertTopLevelItem(0, comment)

    def __activated_pkgList_item_text(self):
        """Finds currently activated item in the pkgList.

        Returns:
            item.text(), currently activated item text.
        """
        index = 0
        # check current activated item in pkgList
        for i in range(self.ui.pkgList.count()):
            item = self.ui.pkgList.item(index)
            if item.isSelected():
                return item.text()
            index += 1

    def exit_threads(self):
        if not self.pkg_worker.isRunning():
            self.pkg_worker.exit()

        for i in range(self.__BODHI_WORKERS_COUNT):
            if not self.bodhi_workers[i].isRunning():
                self.bodhi_workers[i].exit()

def main():
    app = QtGui.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    ret = app.exec_()
    win.exit_threads()
    sys.exit()

if __name__ == "__main__":
    main()

# vim: set expandtab ts=4 sts=4 sw=4 :