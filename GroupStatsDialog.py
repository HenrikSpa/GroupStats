# -*- coding: utf-8 -*-

import csv
import os
import pickle
import sys
import traceback
import math
import webbrowser
from math import *

from qgis.PyQt import uic
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox, QTableView, QWidget, QMenu, QAction

from qgis.core import *
from qgis.gui import *


FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'ui_groupstats.ui'))

class GroupStatsDialog(QMainWindow):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.ui = FORM_CLASS()
        self.ui.setupUi(self)

        self.ui.result = WindowResults(self.ui.centralwidget)

        self.ui.horizontalLayout.addWidget(self.ui.result)

        self.calculations = Calculations(self)

        self.ui.listHalf.setAcceptDrops(True)
        self.ui.listHalf.setModelColumn(2)

        self.ui.rows.setAcceptDrops(True)
        self.ui.columns.setAcceptDrops(True)
        self.ui.values.setAcceptDrops(True)

        self.ui.calculate.clicked.connect(self.showScore)
        self.ui.clear.clicked.connect(self.clearChoice)
        self.ui.filterButton.clicked.connect(self.setFilter)
        self.ui.layer.currentIndexChanged.connect(self.layerSelection)   # Layer selection signal

        dictionary =  {'attributeTxt':[('Rejon',1), ('Posterunek',2)],
                    'countAttributes':[('Moc stacji', 3)],
                    'geometry':[('Length', 1), ('Area', 2)],
                    'calculations':[('Count', 1), ('Sum', 2), ('Average', 3), ('Standard deviation', 4)]}

        self.tm1 = ModelListaPol(self)
        self.ui.listHalf.setModel(self.tm1)

        self.tm2 = ModelRowsColumns(self)
        #tm2.ustawInneModele(tm1)
        self.ui.rows.setModel(self.tm2)

        self.tm3 = ModelRowsColumns(self)
        #tm3.ustawInneModele(tm1)
        self.ui.columns.setModel(self.tm3)

        self.tm4 = ValueModel(self)
        self.ui.values.setModel(self.tm4)

        self.tm2.setOtherModels(self.tm3, self.tm4)
        self.tm3.setOtherModels(self.tm2, self.tm4)
        self.tm4.setOtherModels(self.tm2, self.tm3)

        self.tm2.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm3.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm4.rowsInserted.connect(self.blockCalculations)   # Layer selection signal
        self.tm2.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal
        self.tm3.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal
        self.tm4.rowsRemoved.connect(self.blockCalculations)   # Layer selection signal

        self.ui.actionCopy.triggered.connect(self.duplication)   # Layer selection signal
        self.ui.actionCopySelected.triggered.connect(self.copyMarked)   # Layer selection signal
        self.ui.actionSaveCSV.triggered.connect(self.exportToCSV)   # Layer selection signal
        self.ui.actionSaveCSVSelected.triggered.connect(self.exportMarkedToCSV)   # Layer selection signal
        self.ui.actionShowPanel.triggered.connect(self.showControlPanel)   # Layer selection signal
        self.ui.actionShowOnMap.triggered.connect(self.showOnMap)   # Layer selection signal
        self.ui.actionTutorial.triggered.connect(self.showTutorial)   # Layer selection signal

        self.ui.result.verticalHeader().sortIndicatorChanged.connect(self.sortRows)   # Layer selection signal


    def sortRows(self, row, mode):
            self.ui.result.model().sortRows(row, mode)


    def blockCalculations(self, x, y, z): #finished
        values = self.tm4._data
        columns = self.tm3._data
        rows = self.tm2._data
        # If the value field has numbers (attributes or geometry) and some calculate function has been selected
        if  ('geometry' in [a[0] for a in values] or 'countAttributes' in [a[0] for a in values]) and\
            'calculations' in [a[0] for a in values+rows+columns]:
            self.ui.calculate.setEnabled(True)
        # If the value field has a text attribute and you have selected exactly one function - the counter
        elif 'attributeTxt' in [a[0] for a in values] and len([a for a in values+rows+columns if a[0]=='calculations'])>0:
            if set([a[2] for a in values+rows+columns if a[0]=='calculations']).issubset(set(self.calculations.textList)): #[a for a in values+rows+columns if a[0]=='calculations'][0][2]==0:
                self.ui.calculate.setEnabled(True)
        else:
            self.ui.calculate.setEnabled(False)


    def showScore(self):               #finished
        "Performs calculations and sends them for display"
        chosenRows = tuple(self.tm2._data)                                               # Reading selected rows from the window
        chosenColumns = tuple(self.tm3._data)                                               # Reading selected columns from the window
        chosenValues = tuple(self.tm4._data)                                          # Reading from the window chosenj values ​​and calculations
        value = [x for x in chosenValues if x[0]!='calculations'][0]                 # reading the field that has been chosen for calculation (can only be one)
        if value[0]=='geometry':                                                         # Setting the calculate function depending on the chosen value type
            if value[2]==1:
                valueFunction = lambda _object: _object.geometry().length()                  # length
            elif value[2]==2:
                valueFunction = lambda _object: _object.geometry().area()                    # area
        elif value[0]=='attributeTxt':
            valueFunction = lambda _object: None if _object.attribute(value[1]) is None else _object.attribute(value[1])#.toString()    # text attribute
        elif value[0]=='countAttributes':
            valueFunction = lambda _object: value_attribute_func(value[1], _object)

        index = self.ui.layer.currentIndex()                                             # Download chosen layer
        layerId = self.ui.layer.itemData(index)
        layer = QgsProject.instance().mapLayer(layerId)#.toString())

        request = QgsFeatureRequest()
        _filter = self.ui._filter.toPlainText()
        if _filter:
            request.setFilterExpression(_filter)
        iterator = layer.getFeatures(request)

        if self.ui.onlySelected.isChecked():                                         # Retrieve the IDs of the selected _objects
            selectedObjects = layer.selectedFeatureIds()
            onlySelected = True
        else:
            selectedObjects = []
            onlySelected = False

        result = {}                                                                         # results translator {((row) (column)): [[values], [indexes]}
        f=QgsFeature()                                                                      # Searching for calculation data
        numberOfObjects = len([1 for f in layer.getFeatures(request)
                               if not onlySelected or f.id() in selectedObjects])
        counter = 0
        NULLcounter = 0
        while iterator.nextFeature(f):                                                      # for each object ...
            if onlySelected==False or (onlySelected and (f.id() in selectedObjects)):
                key_column = []                                                                  # key column (column1, column2...)
                key_row = []                                                                  # key row (rows1, rows2...)
                key = ()
                for k in chosenColumns:                                                        # for each chosen column we check the column type
                    if k[0]=='geometry':                                                       # and create the key column
                        if k[2]==1:
                            key_column.append(f.geometry().length())
                        elif k[2]==2:
                            key_column.append(f.geometry().area())
                    elif k[0]=='attributeTxt' or k[0]=='countAttributes':
                        if f.attribute(k[1]) == None:
                            newKeyColumns = ''
                        else:
                            newKeyColumns = f.attribute(k[1])

                        key_column.append(newKeyColumns)#.toString())
                for k in chosenRows:                                                        # for each chosen rows we check the rows type
                    if k[0]=='geometry':                                                       # and create key rows
                        if k[2]==1:
                            key_row.append(f.geometry().length())
                        elif k[2]==2:
                            key_row.append(f.geometry().area())
                    elif k[0]=='attributeTxt' or k[0]=='countAttributes':
                        if f.attribute(k[1]) == None:
                            newRowKey = ''
                        else:
                            newRowKey = f.attribute(k[1])

                        key_row.append(newRowKey)

                key = ( tuple(key_row) , tuple(key_column) )                                 # key to identify object groups
                valueToCalculate = valueFunction(f)
                if valueToCalculate!=None or self.ui.useNULL.isChecked():
                    if valueToCalculate==None:
                        NULLcounter += 1
                        if value[0]=='countAttributes':
                            valueToCalculate=0

                    if key in result:
                        result[key][0].append(valueToCalculate)                                     # if key exists, a new value is added to the list
                    else:
                        result[key] = [[valueToCalculate],[]]                                         # if key does not exist then a new list is created

                    result[key][1].append(f.id())
                else:
                    NULLcounter += 1

                counter += 1
                self.statusBar().showMessage(QCoreApplication.translate('GroupStats','Calculate... ') + '%.0f%%' % ((float(counter)/float(numberOfObjects))*100))         # Displaying progress

        self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','generate view...'))

        keys = result.keys()                                                              # Finding unique row and column keys (separately)
        topmost = set([])
        kolu = set([])
        for z in keys:                                                                    # adding keys to collections to reject repetition
            topmost.add(z[0])
            kolu.add(z[1])
        rows = list(topmost)                                                                # list of unique row keys
        columns = list(kolu)                                                                # list of unique column keys

        rowDictionary={}                                                                      # Creating dictionaries for rows and columns (faster search)
        for nr, row in enumerate(rows):
            rowDictionary[row]=nr
        columnDictionary={}
        for nr, col in enumerate(columns):
            columnDictionary[col]=nr

        calculations = [[x[2] for x in chosenValues if x[0]=='calculations'],         # list of selected calculations in values, rows and columns
                       [x[2] for x in chosenRows      if x[0]=='calculations'],
                       [x[2] for x in chosenColumns      if x[0]=='calculations']]

        if len(calculations[0])!=0:                                                           # Take to calculations only the non-empty part of the list above
            calculation = calculations[0]
        elif len(calculations[1])!=0:
            calculation = calculations[1]
        else:
            calculation = calculations[2]

        data = []                                                                           # Creating an empty array for the date (l.row x l.column)
        for x in range( max( len(rows) , len(rows)*len(calculations[1]))):
            data.append(max(len(columns),len(columns)*len(calculations[2]))*[('',())])

        for x in keys:                                                                    # Calculation of values ​​for all keys
            nrw = rowDictionary[x[0]]                                                         # rows no in the data table for the chosen key
            nrk = columnDictionary[x[1]]                                                          # column number in the data table for the chosen key
            for n,y in enumerate(calculation):                                                       # making all calculates for all keys
                if len(calculations[1])>0:
                    data[nrw*len(calculations[1])+n][nrk] = [self.calculations.list[y][1](result[x][0]), result[x][1]]    # insert result if calculations with row
                elif len(calculations[2])>0:
                    data[nrw][nrk*len(calculations[2])+n] = [self.calculations.list[y][1](result[x][0]), result[x][1]]    # insert result if calculations from columns
                else:
                    data[nrw][nrk] = [self.calculations.list[y][1](result[x][0]), result[x][1]]                         # insert result if calculations with values

        atr = {}                                                                            # Attributes as dict.
        for i in range(layer.fields().count()):
            atr[i] = layer.fields().at(i)
        rowNames=[]                                                                     # List with names of rows
        for x in chosenRows:
            if x[0]=='geometry':
                rowNames.append(x[1])
            elif x[0]!='calculations':
                rowNames.append(atr[x[2]].name())
        colNames=[]                                                                      # List with column names
        for x in chosenColumns:
            if x[0]=='geometry':
                colNames.append(x[1])
            elif x[0]!='calculations':
                colNames.append(atr[x[2]].name())
        nameColumnsCalculations=()                                                            # Insert row and column names with calculations
        nameRowsCalculation=()
        if len(calculations[1])>0:
            obl = [self.calculations.list[x][0] for x in calculations[1]]
            rows1 = [w+(o,) for w in rows for o in obl]
            columns1 = columns
            nameRowsCalculation=(QCoreApplication.translate('GroupStats','Function'),)
        elif len(calculations[2])>0:
            obl = [self.calculations.list[x][0] for x in calculations[2]]
            columns1 = [w+(o,) for w in columns for o in obl]
            rows1 = rows
            nameColumnsCalculations=(QCoreApplication.translate('GroupStats','Function'),)
        else:
            columns1 = columns
            rows1 = rows

        if len(rows1)>0 and len(rows1[0])>0:
            rows1.insert(0,tuple(rowNames)+nameRowsCalculation)
        if len(columns1)>0 and len(columns1[0])>0:
            columns1.insert(0,tuple(colNames)+nameColumnsCalculations)

        if len(rows1)>0 and len(columns1)>0:
            self.ui.result.setUpdatesEnabled(False)
            self.tm5 = ResultModel(data, rows1, columns1, layer)
            self.ui.result.setModel(self.tm5)
            for i in range(len(columns1[0]),0,-1):
                self.ui.result.verticalHeader().setSortIndicator( i-1, Qt.SortOrder.AscendingOrder )
            for i in range(len(rows1[0]),0,-1):
                self.ui.result.horizontalHeader().setSortIndicator( i-1, Qt.SortOrder.AscendingOrder )
            statement = self.statusBar().currentMessage()
            percent = 100.00 / self.tm5.columnCount()
            counter = 0
            for i in range(self.tm5.columnCount()):
                self.ui.result.resizeColumnToContents(i)
                counter = counter + percent
                self.statusBar().showMessage(statement + '%.0f%%' % (counter))

            self.ui.result.setUpdatesEnabled(True)

            if NULLcounter==1:
                rekordy='record'
            else:
                rekordy='records'

            if self.ui.useNULL.isChecked() and NULLcounter>0:
                textNULL = QCoreApplication.translate('GroupStats','  (used %s %s with null value in "%s" field)' % (NULLcounter, rekordy, value[1]))
            elif self.ui.useNULL.isChecked()==False and NULLcounter>0:
                textNULL = QCoreApplication.translate('GroupStats','  (not used %s %s with null value in "%s" field)' % (NULLcounter, rekordy, value[1]))
            else:
                textNULL = ''

            self.statusBar().showMessage(self.statusBar().currentMessage() + ' |  ' + QCoreApplication.translate('GroupStats','done.')+textNULL, 20000)

        else:
            try:
                del(self.tm5)
            except AttributeError:
                pass

            self.ui.result.setModel(None)
            self.statusBar().showMessage(QCoreApplication.translate('GroupStats','No data found.'), 10000)


    def setLayers (self, layer):   #finished
        "Adds available layers to the selection list in the window"

        index = self.ui.layer.currentIndex()
        if index !=-1:
            layerId = self.ui.layer.itemData(index)                        # id of the previously selected layer

        self.ui.layer.blockSignals(True)
        self.ui.layer.clear()                                            # fill the comboBox with a new list of layers
        layer.sort(key=lambda x: x[0].lower())
        for i in layer:
            self.ui.layer.addItem(i[0], i[1])

        if index !=-1:
            index2 = self.ui.layer.findData(layerId)                       # if the previously selected layer is a list then select it
            if index2 !=-1:
                self.ui.layer.setCurrentIndex(index2)
            else:
                self.layerSelection(0)                                            # if it doesn't have the first one
        else:
            self.layerSelection(0)
        self.ui.layer.blockSignals(False)


    def layerSelection(self, index):     #finished
        "Runs after selecting layer from the list. Sets a new list of fields to choose from and deletes windows with already selected fields"

        idW = self.ui.layer.itemData(index)                          # Get the ID of the selected layer
        layer = QgsProject.instance().mapLayer(idW)#.toString())
        fields = layer.fields()

        dictionary = {}
        if layer.geometryType() in (QgsWkbTypes.PointGeometry, QgsWkbTypes.NullGeometry):
            dictionary['geometry'] =  []
        elif layer.geometryType() == QgsWkbTypes.LineGeometry:                             # line
            dictionary['geometry'] = [(QCoreApplication.translate('GroupStats','Length'), 1)]
        elif layer.geometryType() == QgsWkbTypes.PolygonGeometry:                             # polygon
            dictionary['geometry'] = [(QCoreApplication.translate('GroupStats','Perimeter'), 1), (QCoreApplication.translate('GroupStats','Area'), 2)]

        dictionary['countAttributes'] = []
        dictionary['attributeTxt'] = []

        for i in range(fields.count()):
            field = fields.at(i)
            if field.isNumeric():
                dictionary['countAttributes'].append((field.name(), i))
            else:
                dictionary['attributeTxt'].append((field.name(), i))

        dictionary['calculations']=[]
        obl = self.calculations.list
        for c,b in obl.items():
            dictionary['calculations'].append((b[0],c))

        del(self.tm1)
        self.tm1 = ModelListaPol()
        self.ui.listHalf.setModel(self.tm1)
        keys = ['calculations', 'geometry']
        for i in keys:
            j = dictionary[i]
            j.sort(key=lambda x: x[0].lower())
            rows=[]
            for k, l in j:
                rows.append((i,k,l))
            self.tm1.insertRows( 0, len(rows), QModelIndex(), rows)

        keys = ['countAttributes', 'attributeTxt']
        rows=[]
        for i in keys:
            j = dictionary[i]
            for k, l in j:
                rows.append((i,k,l))

        rows.sort(key=lambda x: x[1].lower())
        self.tm1.insertRows( 0, len(rows), QModelIndex(), rows)

        self.clearChoice()


    def clearChoice(self):             # finished
        " Clears windows with selected rows, columns and values"
        self.tm2.removeRows(0, self.tm2.rowCount() ,QModelIndex())
        self.tm3.removeRows(0, self.tm3.rowCount() ,QModelIndex())
        self.tm4.removeRows(0, self.tm4.rowCount() ,QModelIndex())
        self.ui._filter.setPlainText('')


    def showControlPanel(self):     # finished
        ""

        self.ui.controlPanel.setVisible(True)

    def showTutorial(self):
        url = "http://underdark.wordpress.com/2013/02/02/group-stats-tutorial/"
        webbrowser.open (url, 2)

    def setFilter(self):               # finished 2
        index = self.ui.layer.currentIndex()                                             # Download selected layer
        layerId = self.ui.layer.itemData(index)
        layer = QgsProject.instance().mapLayer(str(layerId))

        text = self.ui._filter.toPlainText()                                                 # Retrieve the text from the window and display the query window
        q = QgsSearchQueryBuilder(layer)
        q.setSearchString(text)
        q.exec()

        self.ui._filter.setPlainText(q.searchString ())                                       # Insert a query into the window

    # ------------------------ COPYING DATA TO THE CLIPBOARD AND CSV SAVE ----------------------------START

    def duplication (self):
        "Copy all data to the clipboard"
        text, test = self.downloadDataFromTheTable(True, True)
        if test==True:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

    def copyMarked (self):
        "Copy selected data to the clipboard"
        text, test = self.downloadDataFromTheTable(False, True)
        if test==True:
            clipboard = QApplication.clipboard()
            clipboard.setText(text)

    def exportToCSV (self):
        "Saves all data to CSV file"
        data, test = self.downloadDataFromTheTable(True, False)
        if test==True:
            self.saveFileData(data)

    def exportMarkedToCSV (self):
        "Saves selected data to a CSV file"
        data, test = self.downloadDataFromTheTable(False, False)
        if test==True:
            self.saveFileData(data)

    def saveFileData (self, data):
        "Support for writing data to a file"
        fileWindow = QFileDialog()                                              # Select file to write
        fileWindow.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
        fileWindow.setDefaultSuffix("csv")
        fileWindow.setNameFilters(["CSV files (*.csv)", "All files (*)"])
        if fileWindow.exec() == 0:                                             # No file selected - output
            return
        fileName = fileWindow.selectedFiles()[0]
        _file = open(fileName, 'w')                                            # Open file for writing
        csvfile = csv.writer( _file, delimiter=';' )
        for i in data:                                                          # Copying data from the table
            #csvfile.writerow([bytes(x, 'utf-8') for x in i])
            csvfile.writerow(i)
        _file.close()

    def downloadDataFromTheTable(self, allData=True, controlCharacters=False):
        if self.ui.result.model()==None:
            QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                QCoreApplication.translate('GroupStats','No data to save/copy'))
            return None, False

        text=''
        data = []
        numberOfColumns = self.tm5.columnCount()
        numberOfRows = self.tm5.rowCount()
        rows = []
        columns = []

        if allData == False:                                                               # If the option 'only checked' get indexes of selected fields
            indexList = self.ui.result.selectedIndexes()
            if len(indexList)==0:
                QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'), \
                    QCoreApplication.translate('GroupStatsD','No data selected'))
                return None, False
            for i in indexList:
                rows.append(i.row())
                columns.append(i.column())

        for i in range(numberOfRows):                                                          # Copying data from the table
            if allData or (i in rows) or (i < self.tm5.offsetY):
                row = []
                for j in range(numberOfColumns):
                    if allData or (j in columns) or (j < self.tm5.offsetX):
                        row.append(str(self.tm5.createIndex(i,j).data()))
                data.append(row)

        if controlCharacters == True:
            for m, i in enumerate(data):                                                # Copying data from the table
                if m>0:
                    text = text + chr(13)
                for n, j in enumerate(i):
                    if n>0:
                        text = text + chr(9)
                    text = text + j
            return text, True
        else:
            return data, True

    def copyCellContent(self, selectedCell):
        "Copy cell value to clipboard"
        clipboard = QApplication.clipboard()
        clipboard.setText(selectedCell)

    # ------------------------ COPYING DATA TO THE CLIPBOARD AND SAVING CSV ------------------ ---------- END



    def showOnMap(self):             # change not to duplicate indexes from cells
        indexList = self.ui.result.selectedIndexes()                                    # Retrieve the indexes of the selected fields
        idList = []
        for i in indexList:                                                             # Get object indexes to show
            lista = i.data(Qt.ItemDataRole.UserRole)#.toList()
            if lista == None:                                                               # Reject lines with headers
                lista = ()
            for j in lista:
                idList.append(j)    #w 1 było idList.append(j.toInt()[0])

        try:
            self.tm5.layer.selectByIds(idList)                                          #   selecting them on the map
        except AttributeError:
            QMessageBox.information(None,QCoreApplication.translate('GroupStats','Information'),QCoreApplication.translate('GroupStats','No data selected'))
        else:                                                  
            self.iface.mapCanvas().zoomToSelected(self.tm5.layer)                         #   zoom to selected objects
            if len(idList)==1 and self.tm5.layer.geometryType()==0:                      #      if the layer is point and there is only one object in the group ..
                self.iface.mapCanvas().zoomScale(1000)                                      #      set the scale to 1: 1000


class ModelList(QAbstractListModel):
    """
    Model for windows with amodeut lists.
    Data stored on the list: [(amodeutu type, name, id), ...]
    """

    def __init__(self, mainWindow, parent=None):

        super(ModelList, self).__init__(parent)
        self._data = []
        self.mainWindow = mainWindow
        self.calculations = Calculations(self)


    def rowCount(self, parent=QModelIndex):
        return len(self._data)


    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return None#QVariant()

        row = index.row()
        if role == Qt.ItemDataRole.DisplayRole:
            return self._data[row][1]

        #elif rola == Qt.ForegroundRole:
        #    if self.data[row][0] == 'geometry':
        #        kolor = QColor(0,255,0)
        #    elif self.data[row][0] == 'calculations':
        #        kolor = QColor(255,0,0)
        #    elif self.data[row][0] == 'attributeTxt':
        #        kolor = QColor(150,150,150)
        #    else:
        #        kolor = QColor(0,0,0)   # 'countAttributes'
        #
        #    pedzel = QBrush(kolor)
        #    return pedzel

        elif role == Qt.ItemDataRole.DecorationRole:
            if self._data[row][0] == 'geometry':
                icon = QIcon(":/plugins/groupstats/icons/geom.png")
            elif self._data[row][0] == 'calculations':
                icon = QIcon(":/plugins/groupstats/icons/calc.png")
            elif self._data[row][0] == 'attributeTxt':
                icon = QIcon(":/plugins/groupstats/icons/alpha.png")
            else:
                icon = QIcon(":/plugins/groupstats/icons/digits.png")

            return icon

        return None#QVariant()


    def mimeTypes(self):
        return ['application/x-groupstats-polaL', 'application/x-groupstats-polaWK', 'application/x-groupstats-polaW']


    def supportedDragActions(self):
        return Qt.DropAction.MoveAction


    def supportedDropActions(self):
        return Qt.DropAction.MoveAction


    def insertRows(self, row, number, index, data):
        self.beginInsertRows(index, row, row + number - 1)
        for n in range(number):
            self._data.insert(row + n, data[n])
        self.endInsertRows()
        return True


    def removeRows(self, row, number, index):
        self.beginRemoveRows(index, row, row + number - 1)
        del self._data[row:row + number]
        self.endRemoveRows()
        return True


    def mimeData(self, indexy, typMime='application/x-groupstats-polaL'):
        dataMime = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.OpenModeFlag.WriteOnly)
        for index in indexy:
            row = index.row()
            stringg = pickle.dumps(self._data[row][2])
            #stream << self.data[rows][0][0] << self.data[row][1][0]    #----------------------------- ???????[0]correct
            # Datatypes below happen to be strings or already bytes! (b'geometry', b'calculations' or b'attributeTxt' - maybe reused?)

            stream.writeBytes(bytes(self._data[row][0], 'utf-8') if isinstance(self._data[row][0], str) else bytes(self._data[row][0]))
            stream.writeBytes(bytes(self._data[row][1], 'utf-8') if isinstance(self._data[row][1], str) else bytes(self._data[row][1]))
            stream.writeInt16(self._data[row][2])

        dataMime.setData(typMime, data)

        return dataMime


    def flags(self, index):
        flag = super(ModelList, self).flags(index)

        if index.isValid():
            return flag | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        else:
            return Qt.ItemFlag.ItemIsDropEnabled


class ModelRowsColumns(ModelList):
    """
    Model for windows with field lists for rows and columns
    """

    def __init__(self, parent):

        super(ModelRowsColumns, self).__init__(parent)
        self._data = []


    def setData(self, index, value):
        self._data.insert(index, value)
        return True


    def setOtherModels(self, modelWiK, valueModel):
        self.modelWiK = modelWiK._data
        self.valueModel = valueModel._data


    def mimeData(self, indexy):
        return super(ModelRowsColumns, self).mimeData(indexy, 'application/x-groupstats-polaWK')

    def dropMimeData(self, dataMime, share, row, column, index):
        if dataMime.hasFormat('application/x-groupstats-polaL'):
            dataType = 'application/x-groupstats-polaL'
        elif dataMime.hasFormat('application/x-groupstats-polaWK'):
            dataType = 'application/x-groupstats-polaWK'
        elif dataMime.hasFormat('application/x-groupstats-polaW'):
            dataType = 'application/x-groupstats-polaW'
        else:
            return False

        data = dataMime.data(dataType)

        stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
        outData = []
        while not stream.atEnd():
            #typ = ''#QString() --------------------------------???????????????????????????????????????
            #name = ''#QString()   -------------------------------------??????????????????????????????????????????????
            #stream >> typ >> name
            typ = stream.readBytes().decode('utf-8')
            name = stream.readBytes().decode('utf-8')
            id = stream.readInt16()
            field = (typ, name, id)
            dataWKiW = self.modelWiK+self.valueModel

            if typ=='calculations' and typ in [x[0] for x in dataWKiW] and dataType == 'application/x-groupstats-polaL':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be dropped in only one area'),15000)
                return False
            elif (field in self.modelWiK or field in self._data) and dataType in ['application/x-groupstats-polaL', 'application/x-groupstats-polaW']:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','This field has already been droped'),15000)
                return False
            #elif (typ != 'calculations' and 'calculations' in [x[0] for x in self.data]) or (typ=='calculations' and len([x for x in self.data if (x[0] != 'calculations')])>0):
            #    pprint 'calculated fields cannot be together with other fields'
            #    return False
            elif typ=='calculations' and id not in self.calculations.textList and 'attributeTxt' in [x[0] for x in self.valueModel]:  #name != self.calculations.lista[0][0]
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False

            outData.append(field)

        self.insertRows(row, len(outData), index, outData)

        return True


class ValueModel(ModelList):
    """
    Model for a window with values ​​for calculations
    """

    def __init__(self, parent=None):

        super(ValueModel, self).__init__(parent)
        self._data = []

    def mimeData(self, indexy):
        return super(ValueModel, self).mimeData(indexy, 'application/x-groupstats-polaW')

    def dropMimeData(self, dataMime, share, row, column, index):
        if dataMime.hasFormat('application/x-groupstats-polaL'):
            dataType = 'application/x-groupstats-polaL'
        elif dataMime.hasFormat('application/x-groupstats-polaWK'):
            dataType = 'application/x-groupstats-polaWK'
        elif dataMime.hasFormat('application/x-groupstats-polaW'):
            dataType = 'application/x-groupstats-polaW'
        else:
            return False

        data = dataMime.data(dataType)
        stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
        outData = []
        while not stream.atEnd():
            #typ = '2'#QString()-------------------------------------????????????????????????????
            #name = '2'#QString()-------------------------------------?????????????????????
            #stream >> typ >> name
            typ = stream.readBytes().decode('utf-8')
            name = stream.readBytes().decode('utf-8')
            id = stream.readInt16()
            field = (typ, name, id)
            allData = self.modelRows+self.modelColumns+self._data
            dataWiK = self.modelRows+self.modelColumns
            if len(self._data)>=2:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats',"Area 'Value' may contain a maximum of two entries"),15000)
                return False
            elif typ=='calculations' and typ in [x[0] for x in allData] and dataType == 'application/x-groupstats-polaL':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','Function can be droped in only one area'),15000)
                return False
            elif len(self._data)==1 and typ != 'calculations' and self._data[0][0] != 'calculations':
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats',"In the area 'Value' one of the items must be a function"),15000)
                return False
            elif len(self._data)==1 and ((typ == 'attributeTxt' and self._data[0][2] not in self.calculations.textList) or (id not in self.calculations.textList and self._data[0][0] == 'attributeTxt')):
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False
            elif typ=='attributeTxt' and len([x for x in dataWiK if (x[0]=='calculations' and x[2] not in self.calculations.textList)])>0:
                self.mainWindow.statusBar().showMessage(QCoreApplication.translate('GroupStats','For the text value function can only be one of (%s)' % self.calculations.textNames), 15000)
                return False

            outData.append(field)

        self.insertRows(row, len(outData), index, outData)

        # check: what if when deleting only the calculated field or the value field is left
        return True

    def setOtherModels(self, modelRows, modelColumns):
        self.modelRows = modelRows._data
        self.modelColumns = modelColumns._data


class ModelListaPol(ModelList):
    """
    Model for the window with a list of available fields
    """

    def __init__(self, parent=None):

        super(ModelListaPol, self).__init__(parent)
        #self.ustawDane(slownikPol)
        self._data = []

    def dropMimeData(self, dataMime, share, row, column, index):
        return True


    def removeRows(self, row, number, index):

        return True


class ResultModel(QAbstractTableModel):     # finished
    """
    Model for the window with calculation results
    """

    def __init__(self, data, rows, columns, layer, parent=None):
        super(ResultModel, self).__init__(parent)
        self._data = data
        self.rows = rows
        self.columns = columns
        self.layer = layer

        self.offsetX = max(1,len(rows[0]))                                           # Coordinate shift so that the data starts with 0.0
        self.offsetY = max(1, len(columns[0]))

        if len(rows[0]) != 0 and len(columns[0]) != 0:                               # One line offset (empty) to make room for the names of the lines
                self.offsetY += 1

    def columnCount(self,parent=QModelIndex()):
        if len(self.rows[0])>0 and len(self.columns[0])>0:
            l = len(self.columns) + len(self.rows[0]) - 1
        elif len(self.rows[0])>0 and len(self.columns[0])==0:
            l = len(self.rows[0])+1
        elif len(self.rows[0])==0 and len(self.columns[0])>0:
            l = len(self.columns)
        else:
            l = 2

        return l #max(len(self.rows[0])+1,len(self.column)+len(self.rows[0]))

    def rowCount(self, parent=QModelIndex()):
        return max(2, len(self.rows) + len(self.columns[0]))

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < self.rowCount():
            return None

        row = index.row() - self.offsetY
        column = index.column() - self.offsetX

        if role == Qt.ItemDataRole.DisplayRole:
            if row >=0 and column >=0:                                      # Data
                return self._data[row][column][0]
            elif column < 0 and row >= 0 and len(self.rows[0])>0:        # descriptions of rows
                return self.rows[row+1][column]
            elif row == -1 and column <0 and len(self.rows[0])>0:        # row names
                return self.rows[0][column]
            elif column >= -1 and row < 0 and len(self.columns[0])>0:       # descriptions and column names
                if len(self.rows[0])>0:
                    if row == -1:                                            # break line
                        return ''
                    else:
                        return self.columns[column + 1][row + 1]                # descriptions and column names if there is a break line
                else:
                    return self.columns[column + 1][row]                      # descriptions and column names if there is no gap line

        elif role == Qt.ItemDataRole.UserRole:
            if row >=0 and column >=0:                                      # Data
                return self._data[row][column][1]

        elif role == Qt.ItemDataRole.UserRole+1:
            #print "user role+1"
            if row <0 and column >=0:                                      # column, row or data
                return "column"
            elif row >=0 and column <0:
                return "row"
            elif row >=0 and column >=0:
                return "data"

        elif role == Qt.ItemDataRole.BackgroundRole:                                         # Cell filling
            if row<0 or column<0:                                           # gray for cells with descriptions and namesi
                colour = QColor(245,235,235)
                brush = QBrush(colour)
                return brush

        elif role == Qt.ItemDataRole.TextAlignmentRole:
            if column < 0 and row < -1 and len(self.rows[0]) != 0:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            elif column >= 0 and row < 0:
                return Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
            elif column >= 0 and row >= 0:
                return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter

        elif role == Qt.ItemDataRole.FontRole:
            if row<0 and column<0:
                font = QFont()
                font.setBold(True)
                #font.setItalic(True)
                return font

        return None#QVariant()

    def sort(self, column, mode):
        """
        Sorts the results table by the selected column
        column - column number
        mode - 1-descending, other-ascending
        """

        if len(self.rows) == 1:                                              # If there is only one line, there is nothing to sort
            return

        tmp = []                                                                # A temporary list for a sorted column

        if column >= self.offsetX:                                             # Selecting data to sort
            # n-line number before storting, d-data in line
            try:
                tmp.extend([(n, (float('nan') if not str(d[column - self.offsetX][0]).strip()
                                 else float(d[column - self.offsetX][0]))) for n, d in enumerate(self._data)])
            except (ValueError, TypeError):
                tmp.extend([(n, str(d[column - self.offsetX][0])) for n, d in enumerate(self._data)])
        else:                                                                   # or line names
            # Either convert all values or none to float for sorting
            # n-row number before storting, d-row description
            try:
                tmp.extend([(n, (float('nan') if not str(d[column]).strip()
                                 else float(d[column]))) for n, d in enumerate(self.rows[1:])])
            except (ValueError, TypeError):
                tmp.extend([(n, str(d[column])) for n, d in enumerate(self.rows[1:])])

        tmp = sort_values_nulls_last(tmp, mode)

        data2 = tuple(self._data)                                                # A temporary tuple with all the data
        self._data=[]
        rows2=tuple(self.rows)                                            # A temporary tuple with descriptions of the rows
        self.rows=[]
        self.rows.append(rows2[0])                                        # Adding row names (only names, no row descriptions)

        for i in tmp:                                                           # Arrange all data and row descriptions according to a temporary sort list
            self._data.append(data2[i[0]])
            self.rows.append(rows2[i[0]+1])

        topLeft = self.createIndex(0,0)                                         # Signal change data
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


    def sortRows(self, row, mode):
        """
        Sorts the results table according to the chosen rows
        rows - rows number
        mode - 1-descending, other-ascending
        """
        if len(self.columns) - self.offsetX <=1:                                              # If there is only one column, there is nothing to sort
            return                                                              # (self.columns are then the following list [(),])
        tmp = []                                                                # A temporary list for a sorted row

        if row >= self.offsetY:                                              # Selecting data to sort
            # Either convert all values or none to float for sorting
            try:
                tmp.extend([(n, (float('nan') if not str(d[0]).strip() else float(d[0]))) for n, d in enumerate(self._data[row - self.offsetY])])
            except (ValueError, TypeError):
                tmp.extend([(n, str(d[0])) for n, d in enumerate(self._data[row - self.offsetY])])    # n-column number before storting, d-data in the column
        else:                                                                   # or column names
            # Either convert all values or none to float for sorting
            try:
                tmp.extend([(n, (float('nan') if not str(d[row]).strip() else float(d[row]))) for n, d in enumerate(self.columns[1:])])
            except (ValueError, TypeError):
                tmp.extend([(n, str(d[row])) for n, d in enumerate(self.columns[1:])])
            except IndexError:
                # The table can't be sorted using this column. It's probably the row header columnn
                return

        tmp = sort_values_nulls_last(tmp, mode)

        data2 = tuple(self._data)                                                # A temporary tuple with all the data
        self._data=[]
        columns2=tuple(self.columns)                                            # A temporary tuple with column descriptions
        self.columns=[]
        self.columns.append(columns2[0])                                        # Adding column names (only names, no column descriptions)
        for j in data2:                                                         # Arranging all data according to a temporary sort list
            row = []
            for i in tmp:
                row.append(j[i[0]])
            self._data.append(tuple(row))

        for i in tmp:                                                           # Arrangement of column descriptions according to a temporary sort list
            self.columns.append(columns2[i[0] + 1])

        topLeft = self.createIndex(0,0)                                         # Signal change data
        bottomRight = self.createIndex(self.rowCount(), self.columnCount())
        self.dataChanged.emit(topLeft, bottomRight)


def sort_values_nulls_last(alist, rev):
    contains_values = [x for x in alist
                       if str(x[1]).strip()
                       and x[1] is not None
                       and (not isinstance(x[1], float) or not math.isnan(x[1]))]
    contains_values = list(sorted(contains_values, key=lambda x: x[1], reverse=True if rev == 1 else False))
    values_idx = [x[0] for x in contains_values]
    contains_values.extend([x for x in alist if x[0] not in values_idx])
    return contains_values


class WindowResults(QTableView, QMenu):
    """
    Window with calculation results
    """

    def __init__(self, parent=None):
        super(WindowResults, self).__init__(parent)
        self.setSortingEnabled(True)
        self.setObjectName("result")
        self.verticalHeader().setSortIndicatorShown(True)
        self.clicked.connect(self._selectAll)

    def contextMenuEvent(self, event):
        """
        Right click in the results table
        """
        self.menu = QMenu(self)
        copyCellContentAction = QAction('Copy cell content', self)
        selectionIndex = self.indexAt(event.pos())                                       # Get the index at the position of the right click event
        if selectionIndex.row() in [0, -1] or selectionIndex.column() in [0, -1]:             # Don't do anyting if row or column header is clicked
            return
        selectedCell = str(self.indexAt(event.pos()).data())                        # Get the content of the cell on right click
        copyCellContentAction.triggered.connect(lambda: GroupStatsDialog().copyCellContent(selectedCell))
        self.menu.addAction(copyCellContentAction)
        self.selectionModel().select(selectionIndex, QItemSelectionModel.ClearAndSelect)        # Clear any selection in the table and select the single cell that has been clicked
        self.menu.popup(QCursor.pos())

    def selectionCommand(self, index, event=None):
        """
        Implementation of the original method - adds selection of entire rows and columns when the table header is selected
        """
        flag = super(WindowResults, self).selectionCommand(index, event)        # calling the original method
        test = None        
        if self.model():
            test = self.model().data(index, Qt.ItemDataRole.UserRole+1)                         # checking the selected cell type
        if test == "row":
            return flag | QItemSelectionModel.SelectionFlag.Rows
        elif test == "column":
            return flag | QItemSelectionModel.SelectionFlag.Columns
        else:
            return flag


    def _selectAll(self, index):
        """
        Select or deselect all data when clicked in the corner of the table
        """
        test = self.model().data(index, Qt.ItemDataRole.UserRole+1)                      # checking the selected cell type
        if test not in ("data", "row", "column"):                           # checking if the corner
            if self.selectionModel().isSelected(index):                        # if the corner is selected, it also marks all dataa
                self.selectAll()
            else:
                self.clearSelection()                                          # deselects all data


class Calculations(QObject):                   # finished
    """
    A class that suppresses functions that perform statistical calculations
    """

    def __init__(self, parent):                                                                     # List with ID, name and calculating function
        super(Calculations, self).__init__(parent)

                                                                                                    # Do not change the function ID! (used for conditions)
        self.list = {0:(QCoreApplication.translate('Calculations', 'count'), self.count),
                     1:(QCoreApplication.translate('Calculations','sum'), self.sum),
                     2:(QCoreApplication.translate('Calculations','average'), self.average),
                     3:(QCoreApplication.translate('Calculations','variance'), self.variance),
                     4:(QCoreApplication.translate('Calculations','stand.dev.'), self.stand_dev),
                     5:(QCoreApplication.translate('Calculations','median'), self.median),
                     6:(QCoreApplication.translate('Calculations','min'), self.minimum),
                     7:(QCoreApplication.translate('Calculations','max'), self.maximum),
                     8:(QCoreApplication.translate('Calculations','unique'), self.unique)}

        self.textList = (0, 6, 7, 8)                                                                        # Calculations also working on text

        self.textNames = ''
        for i in self.textList:
            self.textNames = self.textNames + self.list[i][0] + ', '

        self.textNames = self.textNames[:-2]

    def count(self, result):
        return len(result)

    def sum(self, result):
        return sum(result)

    def average(self, result):
        return self.sum(result)/self.count(result)

    def variance(self, result):
        _variance = 0
        for x in result:
            _variance = _variance + (x-self.average(result))**2
        return _variance/self.count(result)

    def stand_dev(self, result):
        return sqrt(self.variance(result))

    def median(self, result):
        result.sort()
        count = self.count(result)
        if count == 1:
            median = result[0]
        else:
            position = int(count / 2)
            if count%2 == 0:
                median = (result[position]+result[position-1])/2
            else:
                median = result[position]
        return median

    def minimum(self, result):
        return min(result)

    def maximum(self, result):
        return max(result)

    def unique(self, result):
        return len(set(result))


def value_attribute_func(value, _object):
    if _object.attribute(value) is None:
        return None
    try:
        return float(_object.attribute(value))
    except TypeError:
        # Fix for QT5 QVariant-problem.
        if isinstance(_object.attribute(value), QVariant) and _object.attribute(value).isNull():
            return None
        else:
            if isinstance(_object.attribute(value), QVariant):
                return float(_object.attribute(value).value())
            else:
                return float(_object.attribute(value))