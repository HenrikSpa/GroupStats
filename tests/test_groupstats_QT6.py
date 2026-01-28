"""HenrikSpa: These tests should work with QT6."""
from qgis.core import QgsProject, QgsVectorLayer, QgsField, QgsFeature, QgsFields, QgsGeometry
from qgis.PyQt.QtCore import QMetaType, QModelIndex
from qgis.PyQt.QtWidgets import QApplication
import mock
from mock import call
from io import TextIOBase
from GroupStats.groupstats import GroupStats
from qgis.PyQt.QtCore import Qt

class TestGroupStats(object):
    """
    This fix was not needed anymore, but I'm leaving the instructions for future needs (HS 2022-07-05):

    The tests only works with nose by changing the rows in groupstats.py from:

    from . import resources_rc
    from .GroupStatsDialog import GroupStatsDialog

    to

    #from . import resources_rc   <-- Skip the import
    from GroupStatsDialog import GroupStatsDialog <-- Remove the .
    """

    def setUp(self):
        pass

    def tearDown(self):
        QgsProject.instance().clear()
        if hasattr(self, 'gs'):
            if self.gs is not None:
                self.gs.dlg.close()
            self.gs = None

    def create_vectorlayer(self, _fields, data, geometries=None, geomtype='Point'):
        self.vlayer = QgsVectorLayer("{}?crs=epsg:4326".format(geomtype), "test", "memory")
        provider = self.vlayer.dataProvider()

        fields = QgsFields()
        for _field in _fields:
            fields.append(_field)

        provider.addAttributes(_fields)
        self.vlayer.updateFields()
        feats = []
        for f_idx, features_attributes in enumerate(data):
            feature = QgsFeature(fields)
            for idx, attr in enumerate(features_attributes):
                feature[_fields[idx].name()] = attr
            if geometries:
                feature.setGeometry(geometries[f_idx])
            else:
                feature.setGeometry(None)
            #print("Feature valid: " + str(feature.isValid()))
            feats.append(feature)
        provider.addFeatures(feats)
        self.vlayer.updateExtents()

        features = [f for f in self.vlayer.getFeatures('True') if f.id() in self.vlayer.allFeatureIds()]
        feature_ids = [feature.id() for feature in features]

        QgsProject.instance().addMapLayer(self.vlayer)
        hide_print = True
        if not hide_print:
            print("1. Valid vlayer '{}'".format(self.vlayer.isValid()))
            print("2. feature_ids: " + str(feature_ids))
            print("5. QgsVectorLayer.getFeature(): " + str([self.vlayer.getFeature(x).id() for x in feature_ids]))
            print("6. QgsVectorLayer.getFeature() type: " + str([str(type(self.vlayer.getFeature(x))) for x in feature_ids]))
            print("7. QgsVectorLayer.getFeatures(): " + str([x.id() for x in self.vlayer.getFeatures(feature_ids)]))
            print("8. QgsVectorLayer.featureCount(): " + str(self.vlayer.featureCount()))

        root = QgsProject.instance().layerTreeRoot()
        root.addLayer(self.vlayer)

    def init_gs(self):
        mock_iface = mock.Mock
        self.gs = GroupStats(mock_iface)
        self.gs.run()

        self.all = self.gs.dlg.tm1
        self.rows_model = self.gs.dlg.tm2
        self.columns_model = self.gs.dlg.tm3
        self.values_model = self.gs.dlg.tm4
        self.showScore = 'showScore'
        self.actionSaveCSV = 'actionSaveCSV'
        self.actionSaveCSVSelected = 'actionSaveCSVSelected'
        self.data_var = 'data'
        self.result_table = self.gs.dlg.ui.result

    def test_all_unique(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row2', 'col1', 2.0], [3, 'row3', 'col1', 3.0], [4, 'row4', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        sum_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        sum_data = self.all.mimeData([sum_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(sum_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;1.0\r\n'),
                 call.write('row2;2.0\r\n'),
                 call.write('row3;3.0\r\n'),
                 call.write('row4;4.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sum(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;7.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_average(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(4, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;1.5\r\n'),
                 call.write('row2;3.5\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_min(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(8, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;1.0\r\n'),
                 call.write('row2;3.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_max(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(6, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;2.0\r\n'),
                 call.write('row2;4.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_count(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(5, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;2\r\n'),
                 call.write('row2;1\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_median(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0],
                [5, 'row2', 'col1', 8.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(7, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;1.5\r\n'),
                 call.write('row2;4.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_variance(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 6.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(12, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;0.25\r\n'),
                 call.write('row2;2.25\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_stdev(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 6.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(9, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;0.5\r\n'),
                 call.write('row2;1.5\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_geom_polygon_area_sum(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 6.0]]
        geometries = [QgsGeometry.fromWkt('POLYGON((1.0 1.0, 2.0 1.0, 2.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 3.0 1.0, 3.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 4.0 1.0, 4.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 6.0 1.0, 6.0 0.0, 1.0 0.0, 1.0 1.0))')]
        self.create_vectorlayer(_fields, data, geometries, 'Polygon')
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(4, 0)
        calc_index = self.all.createIndex(12, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;8.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_geom_perimeter_sum(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 6.0]]
        geometries = [QgsGeometry.fromWkt('POLYGON((1.0 1.0, 2.0 1.0, 2.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 3.0 1.0, 3.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 4.0 1.0, 4.0 0.0, 1.0 0.0, 1.0 1.0))'),
                      QgsGeometry.fromWkt('POLYGON((1.0 1.0, 6.0 1.0, 6.0 0.0, 1.0 0.0, 1.0 1.0))')]
        self.create_vectorlayer(_fields, data, geometries, 'Polygon')
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(5, 0)
        calc_index = self.all.createIndex(12, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;10.0\r\n'),
                 call.write('row2;20.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_geom_linestring_length_sum(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 6.0]]
        geometries = [QgsGeometry.fromWkt('LINESTRING(1.0 1.0, 2.0 1.0)'),
                      QgsGeometry.fromWkt('LINESTRING(1.0 1.0, 3.0 1.0)'),
                      QgsGeometry.fromWkt('LINESTRING(1.0 1.0, 4.0 1.0)'),
                      QgsGeometry.fromWkt('LINESTRING(1.0 1.0, 6.0 1.0)')]
        self.create_vectorlayer(_fields, data, geometries, 'Linestring')
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(4, 0)
        calc_index = self.all.createIndex(11, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;8.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_save_selected_unique(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row2', 'col1', 2.0], [3, 'row3', 'col1', 3.0], [4, 'row4', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        sum_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        sum_data = self.all.mimeData([sum_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(sum_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            self.result_table.selectRow(3)
            #self.result_table.selectRow(1)
            #self.result_table.selectRow(2)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSVSelected).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row2;2.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_dont_sortrow_one_columns(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.verticalHeader()
            qheaderview.setSortIndicator(3, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;7.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sortrow_two_columns(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0],
                [5, 'row1', 'col2', 5.0], [6, 'row1', 'col2', 6.0], [7, 'row2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.verticalHeader()
            qheaderview.setSortIndicator(2, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)

        assert [call.write('cols;col2;col1\r\n'),
                 call.write('rows;;\r\n'),
                 call.write('row1;11.0;3.0\r\n'),
                 call.write('row2;15.0;7.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sum_sortrow_two_columns_one_int(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        #data = [[1, 'row1', 'col1', 1.0], [2, 1.0, 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 2.0, 'col1', 4.0],
        #        [5, '1', 'col2', 5.0], [6, 1, 'col2', 6.0], [7, '2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        data = [[1, 'row1', 'col1', 1.0], [2, '1.0', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, '2.0', 'col1', 4.0],
                [5, '1', 'col2', 5.0], [6, '1', 'col2', 6.0], [7, '2', 'col2', 7.0], [8, 'row2', 'col2', 8.0],
                [9, '1', 'col1', 20.0], [10, '1', 'col1', 10.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.verticalHeader()
            qheaderview.setSortIndicator(2, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1;col2\r\n'),
                 call.write('rows;;\r\n'),
                 call.write('1;30.0;11.0\r\n'),
                 call.write('1.0;2.0;\r\n'),
                 call.write('2;;7.0\r\n'),
                 call.write('2.0;4.0;\r\n'),
                 call.write('row1;1.0;\r\n'),
                 call.write('row2;3.0;8.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sortrow_no_columns(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0],
                [5, 'row1', 'col2', 5.0], [6, 'row1', 'col2', 6.0], [7, 'row2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.verticalHeader()
            qheaderview.setSortIndicator(2, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('rows;None\r\n'),
             call.write('row1;14.0\r\n'),
             call.write('row2;22.0\r\n'),
             call.close()] in mock_file.mock_calls

    def test_sum_one_row(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sum_no_row(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        #rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        #rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        #self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('cols;col1\r\n'),
                 call.write('None;3.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_show_panel(self):
        """
        Test that show panel runs without exception
        :return:
        """
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()
        self.gs.dlg.ui.actionShowPanel.trigger()

    def test_duplicate_no_data(self):
        """
        Test that show panel runs without exception
        :return:
        """
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()


        @mock.patch('qgis.PyQt.QtWidgets.QMessageBox.information')
        def __test(self, mock_messagebox):
            self.gs.dlg.ui.actionCopy.trigger()
            return mock_messagebox

        mock_messagebox = __test(self)

        assert call(None, 'Information', 'No data to save/copy') in mock_messagebox.mock_calls

    def test_duplicate(self):
        """
        Test that show panel runs without exception
        :return:
        """
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch('qgis.PyQt.QtWidgets.QMessageBox.information')
        def __test(self, mock_messagebox):
            getattr(self.gs.dlg, self.showScore)()
            self.gs.dlg.ui.actionCopy.trigger()
            return mock_messagebox

        mock_messagebox = __test(self)

        assert not mock_messagebox.mock_calls

        test = QApplication.clipboard().text()

        #a = ''.join([str(a.encode()) for a in test])
        #print(str(a))
        assert test == '''cols\tcol1\rrows\t\rrow1\t3.0\rrow2\t7.0'''

    def test_sortrow_second_header_row(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0],
                [5, 'row1', 'col2', 5.0], [6, 'row1', 'col2', 6.0], [7, 'row2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.verticalHeader()
            qheaderview.setSortIndicator(1, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        assert [call.write('cols;col1;col2\r\n'),
                 call.write('rows;;\r\n'),
                 call.write('row1;3.0;11.0\r\n'),
                 call.write('row2;7.0;15.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def __test_sortrow_one_row(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0],
                [5, 'row1', 'col2', 5.0], [6, 'row1', 'col2', 6.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.horisontalHeader()
            #qheaderview.setSortIndicator(2, Qt.SortOrder.DescendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))

        assert [call.write('rows;None\r\n'),
             call.write('row1;14.0\r\n'),
             call.write('row2;22.0\r\n'),
             call.close()] in mock_file.mock_calls

    def test_sum_xsd_int_type(self):
        """Test that WFS data type xsd:int can be used for calculation"""
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Int, 'xsd:int')]
        data = [[1, 'row1', 'col1', 1.0], [2, 'row1', 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 'row2', 'col1', 4.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        #print(str(mock_file.mock_calls))
        assert [call.write('cols;col1\r\n'),
                 call.write('rows;\r\n'),
                 call.write('row1;3.0\r\n'),
                 call.write('row2;7.0\r\n'),
                 call.close()] in mock_file.mock_calls

    def test_sortcol_floats(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        #data = [[1, 'row1', 'col1', 1.0], [2, 1.0, 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 2.0, 'col1', 4.0],
        #        [5, '1', 'col2', 5.0], [6, 1, 'col2', 6.0], [7, '2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        data = [[1, 'row1', 'col1', 1.0],
                [2, '1.0', 'col1', 2.0],
                [3, 'row2', 'col1', 3.0],
                [4, '2.0', 'col1', 4.0],
                [5, '1', 'col2', 5.0],
                [6, '1', 'col2', 6.0],
                [7, '2', 'col2', 7.0],
                [8, 'row2', 'col2', 8.0],
                [9, '1', 'col1', 20.0],
                [10, '1', 'col1', 10.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.horizontalHeader()
            qheaderview.setSortIndicator(2, Qt.SortOrder.AscendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        print(str(mock_file.mock_calls))

        assert [call.write('cols;col1;col2\r\n'),
                 call.write('rows;;\r\n'),
                 call.write('2;;7.0\r\n'),
                 call.write('row2;3.0;8.0\r\n'),
                 call.write('1;30.0;11.0\r\n'),
                 call.write('1.0;2.0;\r\n'),
                 call.write('2.0;4.0;\r\n'),
                 call.write('row1;1.0;\r\n'),
                 call.close()] in mock_file.mock_calls


    def test_sortcol_contains_None(self):
        _fields = [QgsField('id', QMetaType.Type.Int, QMetaType.Type.Int.name),
                   QgsField('rows', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('cols', QMetaType.Type.QString, QMetaType.Type.QString.name),
                   QgsField('values', QMetaType.Type.Double, QMetaType.Type.Double.name)]
        #data = [[1, 'row1', 'col1', 1.0], [2, 1.0, 'col1', 2.0], [3, 'row2', 'col1', 3.0], [4, 2.0, 'col1', 4.0],
        #        [5, '1', 'col2', 5.0], [6, 1, 'col2', 6.0], [7, '2', 'col2', 7.0], [8, 'row2', 'col2', 8.0]]
        data = [[1, 'row1', 'col1', 1.0],
                [2, '1.0', 'col1', 2.0],
                [3, 'row2', 'col1', 3.0],
                [4, '2.0', 'col1', 4.0],
                [5, '1', 'col2', 5.0],
                [6, '1', 'col2', 6.0],
                [7, '2', 'col2', 7.0],
                [8, 'row2', 'col2', None],
                [9, '1', 'col1', 20.0],
                [10, '1', 'col1', 10.0]]
        self.create_vectorlayer(_fields, data)
        self.init_gs()

        #for idx, value in enumerate(getattr(self.gs.dlg.tm1, self.data_var)):
        #    print("{} {}".format(str(idx), str(value)))

        cols_index = self.all.createIndex(0, 0)
        rows_index = self.all.createIndex(2, 0)
        values_index = self.all.createIndex(3, 0)
        calc_index = self.all.createIndex(10, 0)

        cols_data = self.all.mimeData([cols_index])
        rows_data = self.all.mimeData([rows_index])
        values_data = self.all.mimeData([values_index])
        calc_data = self.all.mimeData([calc_index])

        self.columns_model.dropMimeData(cols_data, None, 0, 0, QModelIndex())
        self.rows_model.dropMimeData(rows_data, None, 0, 0, QModelIndex())
        self.values_model.dropMimeData(calc_data, None, 0, 0, self.values_model.index(0))
        self.values_model.dropMimeData(values_data, None, 0, 0, self.values_model.index(0))

        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.selectedFiles")
        @mock.patch('qgis.PyQt.QtWidgets.QMainWindow.statusBar')
        @mock.patch("qgis.PyQt.QtWidgets.QMessageBox.information")
        @mock.patch("qgis.PyQt.QtWidgets.QFileDialog.exec")
        @mock.patch("builtins.open")
        def savefile(dlg, mock_open, mock_exec, mock_messagebox, mock_statusbar, mock_selectedfile):
            mock_selectedfile.return_value = ['noname']
            mock_exec.return_value = 1
            getattr(self.gs.dlg, self.showScore)()
            qheaderview = self.gs.dlg.ui.result.horizontalHeader()
            qheaderview.setSortIndicator(2, Qt.SortOrder.AscendingOrder)
            #self.gs.dlg.sortRows(self, row, mode)

            mock_file = mock.MagicMock(spec=TextIOBase)
            mock_open.return_value = mock_file
            getattr(dlg.ui, self.actionSaveCSV).trigger()
            return mock_file

        mock_file = savefile(self.gs.dlg)
        print(str(mock_file.mock_calls))

        assert [call.write('cols;col1;col2\r\n'),
                 call.write('rows;;\r\n'),
                 call.write('2;;7.0\r\n'),
                 call.write('1;30.0;11.0\r\n'),
                 call.write('1.0;2.0;\r\n'),
                 call.write('2.0;4.0;\r\n'),
                 call.write('row1;1.0;\r\n'),
                 call.write('row2;3.0;\r\n'),
                 call.close()] in mock_file.mock_calls