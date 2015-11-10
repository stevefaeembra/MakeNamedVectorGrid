# -*- coding: utf-8 -*-
"""
/***************************************************************************
 createnamedgrid
                                 A QGIS plugin
 creates a regular grid for indexing
                              -------------------
        begin                : 2015-04-17
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Steven Kay
        email                : stevendkay@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.gui import *
from qgis.core import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from createnamedgrid_dialog import createnamedgridDialog
import os.path
import time
import math


class createnamedgrid:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'createnamedgrid_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = createnamedgridDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Create Indexed Grid')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'createnamedgrid')
        self.toolbar.setObjectName(u'createnamedgrid')

        # wire up events
        self.dlg.pbMapCanvasExtent.clicked.connect(self.canvasextent)
        self.dlg.pbLayerExtent.clicked.connect(self.layerextent)
        
        self.dlg.rbShowCellSize.clicked.connect(self.updateinfobox)
        self.dlg.rbShowGridSize.clicked.connect(self.updateinfobox)
        
        self.dlg.sbColumns.valueChanged.connect(self.updategrid)
        self.dlg.sbRows.valueChanged.connect(self.updategrid)
        self.dlg.cbAspect.currentIndexChanged.connect(self.updateaspect)
        self.dlg.pbCreate.clicked.connect(self.makegrid)
        
        self.ycells = 1
        self.xcells = 1
        
        # default to canvas extent
        self.canvasextent()

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('createnamedgrid', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToVectorMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/createnamedgrid/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Create named vector grid'),
            callback=self.run,
            parent=self.iface.mainWindow())
#         self.add_action(
#             icon_path,
#             text=self.tr(u'Do something else'),
#             callback=self.run,
#             parent=self.iface.mainWindow())


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginVectorMenu(
                self.tr(u'&create grid for indexing'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def layerextent(self):
        self.using = "layer"
        bounds = self.iface.mapCanvas().fullExtent()
        self.xmin = bounds.xMinimum()
        self.xmax = bounds.xMaximum()
        self.ymin = bounds.yMinimum()
        self.ymax = bounds.yMaximum()
        self.xrange = self.xmax - self.xmin
        self.yrange = self.ymax - self.ymin
        print "Lower left (%2.4f,%2.4f) " % (self.xmin, self.ymin)
        print "Upper right (%2.4f,%2.4f) " % (self.xmax, self.ymax)
        self.updategridsize()
        self.updateinfobox()
        
    def canvasextent(self):
        self.using = "canvas"
        bounds = self.iface.mapCanvas().extent()
        self.xmin = bounds.xMinimum()
        self.xmax = bounds.xMaximum()
        self.ymin = bounds.yMinimum()
        self.ymax = bounds.yMaximum()
        self.xrange = self.xmax - self.xmin
        self.yrange = self.ymax - self.ymin
        print "Lower left (%2.4f,%2.4f) " % (self.xmin, self.ymin)
        print "Upper right (%2.4f,%2.4f) " % (self.xmax, self.ymax)
        self.updategridsize()
        self.updateinfobox()

    def updateinfobox(self):
        '''
        update text label
        '''
        s =[]
        s.append("Using %s extent" % self.using)
        if self.ysize == 0:
            return
        s2 = "\n".join(s)
        
        # two modes - show cell size, or show grid size
        
        mode =  self.dlg.rbShowCellSize.isChecked()
        
        if mode:
            self.dlg.labHeight.setText("%2.2f" % self.ysize)
            self.dlg.labWidth.setText("%2.2f" % self.xsize)
        else:
            self.dlg.labHeight.setText("%d" % self.ycells)
            self.dlg.labWidth.setText("%d" % self.xcells)
        
        ratio = self.xsize/self.ysize
        self.dlg.pbAspect.setText("1 : %1.2f" % ratio)
        self.dlg.labInfo.setText(s2)

    def updategrid(self):
        self.updategridsize()
        self.updateinfobox()


    def guessbestaspectratio(self,xx,yy):
        '''
        given extent xx by yy, find the row/column count (between 0 and 99) which gives
        the closest aspect ratio to 1:1
        '''
        if self.xrange == 0 or self.yrange == 0 :
            return
        print "Yrange %2.4f" % self.yrange
        print "Xrange %2.4f" % self.xrange
        minratio = 10000.0
        minrow = 0
        micol = 0
        for rows in range(1,100):
            for cols in range(1,100):
                xx = self.xrange / cols
                yy = self.yrange / rows
                ratio = xx/yy
                offsquare =  abs(ratio-1.0)
                if offsquare < minratio:
                    minratio = offsquare
                    minrow = rows
                    mincol = cols
                    print "New best ratio is (%2.2f x %2.2f), ratio of 1:%2.4f" % (mincol, minrow, minratio) 
        return (minrow, mincol) 

    def updateaspect(self):
        if self.dlg.cbAspect.currentIndex()==0:
            # rectangular mode, freely choose rows AND columns
            self.dlg.sbRows.setEnabled(True)
            self.dlg.sbColumns.setEnabled(True)
        if self.dlg.cbAspect.currentIndex()==1:
            # square mode, freely choose rows only
            self.dlg.sbRows.setEnabled(True)
            self.dlg.sbColumns.setEnabled(False)
        if self.dlg.cbAspect.currentIndex()==2:
            # squarer mode, freely choose columns only
            self.dlg.sbRows.setEnabled(False)
            self.dlg.sbColumns.setEnabled(True)
        if self.dlg.cbAspect.currentIndex()==3:
            # square mode, get best fit
            self.dlg.sbRows.setEnabled(False)
            self.dlg.sbColumns.setEnabled(True)
            self.guessbestaspectratio(self.xrange, self.yrange)
            
        self.updategrid()  
        
            
    def updategridsize(self):
        self.ycells = self.dlg.sbRows.value()
        self.xcells = self.dlg.sbColumns.value()
        
        if self.dlg.cbAspect.currentIndex()==1:
            print "Force to squares vertically"
            try:
                self.ysize = self.yrange/self.ycells
                self.xcells = int(self.xrange/self.ysize)+1
                self.xsize = self.ysize
                
            except:
                self.iface.messageBar().pushMessage("Error", "You need to have a layer selected!", level=QgsMessageBar.CRITICAL)
            #self.dlg.sbRows.setValue(self.ysize)
            
        if self.dlg.cbAspect.currentIndex()==2:
            print "Force to squares horizontally"
            try:
                self.xsize = self.xrange/self.xcells
                self.ycells = int(self.yrange/self.xsize)+1
                self.ysize = self.xsize
            except:
                self.iface.messageBar().pushMessage("Error", "You need to have a layer selected!", level=QgsMessageBar.CRITICAL)
            #self.dlg.sbColumns.setValue(self.xsize)

        if self.dlg.cbAspect.currentIndex()==0:
            print "Normal size mode"
            self.xcells = self.dlg.sbColumns.value()
            self.xsize = self.xrange/self.xcells
            self.ysize = self.yrange/self.ycells
            
            
        if self.dlg.cbAspect.currentIndex()==3:
            print "Square auto fit mode"
            minrow, mincol = self.guessbestaspectratio(self.xrange, self.yrange)
            self.xcells = mincol
            self.ycells = minrow
            self.dlg.sbColumns.setValue(mincol)
            self.dlg.sbRows.setValue(minrow)
            self.xsize = self.xrange/self.xcells
            self.ysize = self.yrange/self.ycells
            
        
        #self.dlg.sbRows.setValue(self.ycells)
        #self.dlg.sbColumns.setValue(self.xcells)

    def getspreadsheetalphabetic(self,idx):
        if idx < 1:
            raise ValueError("Index is too small")
        result = ""
        while True:
            if idx > 26:
                idx, r = divmod(idx - 1, 26)
                result = chr(r + ord('A')) + result
            else:
                return chr(idx + ord('A') - 1) + result
            
    def getnumeric(self,idx):
        return "%d" % idx

    def gridcellgenerator(self):
        ''' 
        generates a grid cell at a time, row-by-row, left to right 
        '''
        mode = self.dlg.cbDirection.currentIndex()
        rowlabelmode = self.dlg.cbRowNumbering.currentIndex()
        collabelmode = self.dlg.cbColumnNumbering.currentIndex()
        for row in range(0,self.ycells):
            if rowlabelmode==0:
                rowname = self.getnumeric(row+1)
            elif rowlabelmode == 1:
                rowname = self.getspreadsheetalphabetic(row+1)
            else:
                rowname = ""    
            if mode==1:
                ytop = self.ymax - (row*self.ysize)
                ybottom = ytop - self.ysize
            else:
                ytop = self.ymin + ((row+1)*self.ysize)
                ybottom = ytop - self.ysize
            for col in range(0,self.xcells):
                if collabelmode==0:
                    colname = self.getnumeric(col+1)
                elif collabelmode == 1:
                    colname = self.getspreadsheetalphabetic(col+1)
                else:
                    colname = ""
                name = "%s%s" % (colname,rowname)
                xleft = self.xmin + (col * self.xsize)
                xright = xleft + self.xsize
                # yield (name, POLYGON)
                yield (name, 'N', row, col, QgsGeometry.fromPolygon([[QgsPoint(xleft,ytop), QgsPoint(xright,ytop), QgsPoint(xright,ybottom), QgsPoint(xleft,ybottom), QgsPoint(xleft,ytop)]]))
        # add a legend cell, half grid height, above the grid
        calcsize=0.0
        if self.dlg.chShowLabels.isChecked():
            for col in range(0,self.xcells):
                # starting from bottom left
                if collabelmode==0:
                    colname = self.getnumeric(col+1)
                else:
                    colname = self.getspreadsheetalphabetic(col+1)
                ybottom = self.ymin + ((row+1)*self.ysize)
                calcsize = (self.ysize/2)
                ytop = ybottom + calcsize
                xleft = self.xmin + (col * self.xsize)
                xright = xleft + self.xsize
                name = "%s" % colname
                yield (name, 'Y', None, colname, QgsGeometry.fromPolygon([[QgsPoint(xleft,ytop), QgsPoint(xright,ytop), QgsPoint(xright,ybottom), QgsPoint(xleft,ybottom), QgsPoint(xleft,ytop)]]))
            # add a legend cell, half grid height, above the grid
            for row in range(0,self.ycells):
                # starting from bottom left
                if rowlabelmode==0:
                    rowname = self.getnumeric(row+1)
                else:
                    rowname = self.getspreadsheetalphabetic(row+1)   
                if mode==1:
                    ytop = self.ymax - (row*self.ysize)
                else:
                     ytop = self.ymin + ((row+1)*self.ysize)
                ybottom = ytop - self.ysize
                xleft = self.xmin - calcsize
                xright = self.xmin
                name = "%s" % rowname
                yield (name, 'Y', rowname, None, QgsGeometry.fromPolygon([[QgsPoint(xleft,ytop), QgsPoint(xright,ytop), QgsPoint(xright,ybottom), QgsPoint(xleft,ybottom), QgsPoint(xleft,ytop)]]))

    def makegrid(self):
        """ build in-memory layer, optionally save as shapefile """
        layername = "index_grid_%s" % time.strftime("%H%M",time.gmtime(time.time()))
        layer = QgsVectorLayer("Polygon", layername, "memory")
        provider = layer.dataProvider()
        layer.startEditing()
        provider.addAttributes( [ QgsField("name", QVariant.String), QgsField("isLabel", QVariant.String), QgsField("col", QVariant.String), QgsField("row", QVariant.String) ] )
        layer.commitChanges()
        # top-left version
        fields=layer.pendingFields()
        for (name, isLabel, row, col, poly) in self.gridcellgenerator():
            feat = QgsFeature(fields)
            feat.setGeometry(poly)
            feat['name'] = name
            feat['isLabel'] = isLabel
            feat['row'] = row
            feat['col'] = col
            provider.addFeatures( [ feat ] )
        layer.commitChanges()
        QgsMapLayerRegistry.instance().addMapLayer(layer)  
        #writer = QgsVectorFileWriter( "/tmp/xxx.shp", provider.encoding(), provider.fields(), QGis.WKBPolygon, provider.crs() )

    def run(self):
        """Run method that performs all the real work"""
        
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass
