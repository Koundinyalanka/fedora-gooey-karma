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
#    Author: Dominika Regeciova <regeciovad@gmail.com>


import os
import re
import sys
import urllib
import time
from PySide import QtCore
from PySide import QtGui
from browser import WebBrowser
from mainwindow_gui import Ui_MainWindow

class DialogWindow(QtGui.QMainWindow):
	
    __KOJI_PACKAGES_URL = "http://kojipkgs.fedoraproject.org//packages/"
    
    def __init__(self,main):
        QtGui.QMainWindow.__init__(self,main)
        self.label = QtGui.QLabel(self) 
        self.main = main

        update = self.main.get_bodhi_update()
        name = update['itemlist_name']       
        path = "%s" % (os.environ.get("XDG_DOWNLOAD_DIR", os.path.expanduser("~")))
        self.nameBox = QtGui.QGroupBox(self)  
        self.nameBox.setCheckable(False)
        self.nameBox.setObjectName("nameBox")
        self.nameBox.setTitle("Name")
        self.nameBox.move(30,20)
        self.nameLayout = QtGui.QHBoxLayout()
        self.nameLayout.setObjectName("nameLayout")
        self.nameEdit = QtGui.QLineEdit(self)
        font = QtGui.QFont()
        font.setItalic(True)
        self.nameEdit.setFont(font) 
        self.nameEdit.setInputMask("") 
        self.nameEdit.setText(name)  
        self.nameEdit.setObjectName("nameEdit")  
        self.nameEdit.setFixedWidth(360)   
        self.nameEdit.move(100,20)
        
        self.pathBox = QtGui.QGroupBox(self)  
        self.pathBox.setCheckable(False)
        self.pathBox.setObjectName("pathBox")
        self.pathBox.setTitle("Path")
        self.pathBox.move(30,90)
        self.pathLayout = QtGui.QHBoxLayout()
        self.pathLayout.setObjectName("pathLayout")
        self.pathEdit = QtGui.QLineEdit(self)
        font = QtGui.QFont()
        font.setItalic(True)
        self.pathEdit.setFont(font) 
        self.pathEdit.setInputMask("") 
        self.pathEdit.setText(path)  
        self.pathEdit.setObjectName("pathEdit")  
        self.pathEdit.setFixedWidth(300)   
        self.pathEdit.move(100,90)

        pathBtn = QtGui.QPushButton("...",self)
        pathBtn.setFixedWidth(50) 
        pathBtn.move(410,90)
        pathBtn.clicked.connect(self.openDirectoryDialog, QtCore.Qt.QueuedConnection)

        cancelBtn = QtGui.QPushButton("Cancel",self)
        cancelBtn.move(100,150)
        cancelBtn.clicked.connect(self.Cancel)
        saveBtn = QtGui.QPushButton("Save",self)
        saveBtn.move(300,150)
        saveBtn.clicked.connect(self.Accept)
      
        layout = QtGui.QVBoxLayout()
        layout.addWidget(self.label)
        layout.addLayout(self.nameLayout)
        layout.addWidget(self.nameEdit)
        layout.addWidget(self.nameBox)
        layout.addLayout(self.pathLayout)
        layout.addWidget(self.pathEdit)
        layout.addWidget(self.pathBox) 
        layout.addWidget(pathBtn)
        layout.addWidget(cancelBtn)
        layout.addWidget(saveBtn)
        self.setLayout(layout)
        
        qr = self.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
        self.ProgressDialog = QtGui.QProgressDialog(self)
        self.ProgressDialog.setWindowTitle(self.tr("Downloading..."))
        self.ProgressDialog.setCancelButtonText(self.tr("Cancel"))
        self.setWindowTitle("Download source RPM")
        
    def dlProgress(self,count, blockSize, totalSize):
        # Progress bar of downloading packages
        self.ProgressDialog.setRange(0, totalSize)
        self.ProgressDialog.setValue(count*blockSize) 
        if count*blockSize >= totalSize:
            self.ProgressDialog.setValue(totalSize)
            return
        if self.ProgressDialog.wasCanceled():
            self.ProgressDialog.close()		      

    def download_source_rpm(self):
        # Download a package to the directory
        update = self.main.get_bodhi_update()
        if not update:
            return

        name = update['parsed_nvr']['name']
        version = update['parsed_nvr']['version']
        release = update['parsed_nvr']['release']

        # Set-up url
        url = self.__KOJI_PACKAGES_URL + "%s/%s/%s/src/%s.src.rpm" % (name, version, release, update['itemlist_name'])          
        urllib.urlretrieve("%s" % (url),"%s/%s" % (self.pathEdit.text(), self.nameEdit.text()), reporthook=self.dlProgress)
        
    def Cancel(self):
        # Download dialog was closed
        self.close()
		
    def Accept(self):
        # Download dialog was confirmed
        self.download_source_rpm()
        self.ProgressDialog.hide()
        self.close()		
		
    def openDirectoryDialog(self):
        # Directory dialog for a change of path for downloading 
        flags = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        directory = QtGui.QFileDialog.getExistingDirectory(self,"Choose Directory",os.getcwd(),flags)
        self.pathEdit.setText(directory)
        

