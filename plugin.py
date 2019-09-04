# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Help Plugin"""

# Standard library imports
import os.path as osp
import sys
import numpy
import cv2
import os 
import time
import ast

# Third party imports
from qtpy.QtCore import QUrl, Signal, Slot
from qtpy.QtWidgets import (QActionGroup, QComboBox, QHBoxLayout,
                            QLabel, QLineEdit, QMenu, QMessageBox, QDialog,
                            QToolButton, QVBoxLayout, QApplication, QGraphicsScene)
from PyQt5.QtWidgets import QPushButton
from qtpy.QtWebEngineWidgets import QWebEnginePage, WEBENGINE

from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon, QImage
from PyQt5 import QtCore, QtGui, QtWidgets, uic

# Local imports
from spyder import dependencies
from spyder.config.base import _, get_conf_path, get_module_source_path
from spyder.config.fonts import DEFAULT_SMALL_DELTA
from spyder.api.plugins import SpyderPluginWidget
from spyder.py3compat import get_meth_class_inst, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils import programs
from spyder.plugins.help.utils.sphinxify import (CSS_PATH,
                                                 generate_context,
                                                 usage, warning)
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout,
                                    MENU_SEPARATOR)
from spyder.plugins.help.confpage import HelpConfigPage
from spyder.plugins.help.utils.sphinxthread import SphinxThread
from spyder.plugins.help.widgets import PlainText, RichText, ObjectComboBox
# import spyder.plugins.editor.widgets.editor.Editor
from spyder.plugins.editor.widgets.editor import (EditorMainWindow, Printer,
                                                  EditorSplitter, EditorStack,)


from spyder.plugins.ipythonconsole.widgets import (ShellWidget)

from spyder.plugins.help.opencv_funcs import (do_threshold, image_resize, do_color_conversion, do_blob_detection)

# import pandas
import inspect

# Sphinx dependency
dependencies.add("sphinx", _("Show help for objects in the Editor and "
                             "Consoles in a dedicated pane"),
                 required_version='>=0.6.6')


class BlobDetectionWindow(QtWidgets.QDialog):

    def getResult(self, source_code):
        final_output = ''
        var_name = self.ui.imageSelectionBox.currentText()
        final_var_name = var_name + '_final'
        contour_var_name = var_name + '_contours'
        
        fn_already_present = False
        root = ast.parse(source_code)
        for node in ast.walk(root):
            if isinstance(node, ast.FunctionDef) and node.name == 'do_blob_detection':
                fn_already_present = True
        
        if not fn_already_present:
            final_output += '\n' + inspect.getsource(do_blob_detection)
        final_output += '\n ' + contour_var_name + ', ' + final_var_name + ' = do_blob_detection(' + var_name +  ')'
        return final_output

    def __init__(self, var_info, shell):
        super(BlobDetectionWindow, self).__init__()
        currentDirectory = os.getcwd()
        dir = os.path.dirname(__file__)
        ui = uic.loadUi(dir + '/ui/blob_detection.ui', self)
        self.ui = ui
        self.var_info = var_info
        self.shell = shell
        self.imagePath = ''
        
        # Fill up imageSelectionBox:
        names = []
        ui.imageSelectionBox.clear()
        for var_name in self.var_info:
            if (self.var_info[var_name]['type'] == 'uint8') and len(self.shell.get_value(var_name).shape) < 3:
                names.append(var_name)
        
        index = 0
        for name in names:
            if index == 0:
                imgTmp = self.shell.get_value(name)
                self.loadImage(imgTmp)
            
            # Add to ui.imageSelector
            ui.imageSelectionBox.addItem(name)
            index += 1
        
        # Assign onChange Event:
        ui.imageSelectionBox.currentIndexChanged.connect(self.selectionChanged)
        

    def loadImage(self, imgTmp):
        scene = QtWidgets.QGraphicsScene()

        contours, imgTmp = do_blob_detection(imgTmp)
        cvImg = image_resize(imgTmp, height = self.ui.graphicsView.height() - 20)
        
        # image is now converted to grayscale format:
        height, width = cvImg.shape
        bytesPerLine = width
        qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_Grayscale8)
        pic = QtGui.QPixmap.fromImage(qImg)
        scene.addItem(QtWidgets.QGraphicsPixmapItem(pic))
        self.ui.graphicsView.setScene(scene)
        self.ui.graphicsView.show()
		
    
    def selectionChanged(self, index=None):
        imgTmp = self.shell.get_value(self.ui.imageSelectionBox.currentText())
        self.loadImage(imgTmp)


class ThresholdWindow(QtWidgets.QDialog):

    def getResult(self, source_code):
        final_output = ''
        var_name = self.ui.imageSelectionBox.currentText()
        final_var_name = var_name + '_final'
        
        t1 = self.ui.lowerThreshold.value()
        t2 = self.ui.upperThreshold.value()
        do_invert = self.ui.doInvert.isChecked()        

        fn_already_present = False
        root = ast.parse(source_code)
        for node in ast.walk(root):
            if isinstance(node, ast.FunctionDef) and node.name == 'do_threshold':
                fn_already_present = True
        
        if not fn_already_present:
            final_output += '\n' + inspect.getsource(do_threshold)
        final_output += '\n' + final_var_name + ' = do_threshold(' + var_name + ',' + str(t1) + ',' + str(t2) + ',' + str(do_invert) + ')'
        return final_output

    def __init__(self, var_info, shell):
        super(ThresholdWindow, self).__init__()
        currentDirectory = os.getcwd()
        dir = os.path.dirname(__file__)
        ui = uic.loadUi(dir + '/ui/threshold.ui', self)
        self.ui = ui
        self.var_info = var_info
        self.shell = shell
        self.imagePath = ''
        
        # Fill up imageSelectionBox:
        names = []
        ui.imageSelectionBox.clear()
        for var_name in self.var_info:
            if (self.var_info[var_name]['type'] == 'uint8') or (self.var_info[var_name]['type'] == 'str' and os.path.exists(self.shell.get_value(var_name))):
                names.append(var_name)
        
        index = 0
        for name in names:
            if index == 0:
                imgTmp = self.shell.get_value(name)
                self.loadImage(imgTmp)
            
            # Add to ui.imageSelector
            ui.imageSelectionBox.addItem(name)
            index += 1
        
        # Assign onChange Event:
        ui.imageSelectionBox.currentIndexChanged.connect(self.selectionChanged)
        ui.upperThreshold.valueChanged.connect(self.selectionChanged)
        ui.lowerThreshold.valueChanged.connect(self.selectionChanged)
        ui.doInvert.stateChanged.connect(self.selectionChanged)

    def loadImage(self, imgTmp):
        scene = QtWidgets.QGraphicsScene()

        t1 = self.ui.lowerThreshold.value()
        t2 = self.ui.upperThreshold.value()
        do_invert = self.ui.doInvert.isChecked()
        
        imgTmp = do_threshold(imgTmp, t1, t2, do_invert)
        cvImg = image_resize(imgTmp, height = self.ui.graphicsView.height() - 20)
        
        # image is now converted to grayscale format:
        height, width = cvImg.shape
        bytesPerLine = width
        qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_Grayscale8)
        #qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_Mono)
        pic = QtGui.QPixmap.fromImage(qImg)
        scene.addItem(QtWidgets.QGraphicsPixmapItem(pic))
        self.ui.graphicsView.setScene(scene)
        self.ui.graphicsView.show()
		
    
    def selectionChanged(self, index=None):
        imgTmp = self.shell.get_value(self.ui.imageSelectionBox.currentText())
        self.loadImage(imgTmp)

class ColorConversionWindow(QtWidgets.QDialog):

    def getResult(self, source_code):
        final_output = ''
        var_name = self.ui.imageSelector.currentText()
        final_var_name = var_name + '_final'

        do_grayscale = self.ui.isGrayScale.isChecked()
        slide_r_value = self.ui.slideR.value() / 100.0
        slide_g_value = self.ui.slideG.value() / 100.0
        slide_b_value = self.ui.slideB.value() / 100.0

        fn_already_present = False
        root = ast.parse(source_code)
        for node in ast.walk(root):
            if isinstance(node, ast.FunctionDef) and node.name == 'do_color_conversion':
                fn_already_present = True
        
        if not fn_already_present:
            final_output += '\n' + inspect.getsource(do_color_conversion)
        final_output += '\n' + final_var_name + ' = do_color_conversion(' + var_name + ',' + str(slide_r_value) + ',' + str(slide_g_value) + ',' + str(slide_b_value) + ',' + str(do_grayscale) + ')'
        return final_output

    def __init__(self, var_info, shell):
        super(ColorConversionWindow, self).__init__()
        currentDirectory = os.getcwd()
        dir = os.path.dirname(__file__)
        ui = uic.loadUi(dir + '/ui/color_space_converter.ui', self)
        self.ui = ui
        self.var_info = var_info
        self.shell = shell
        self.isGrayScale = self.ui.isGrayScale
        self.imagePath = ''
        
        names = []
        for var_name in self.var_info:
            if (self.var_info[var_name]['type'] == 'uint8') or (self.var_info[var_name]['type'] == 'str' and os.path.exists(self.shell.get_value(var_name))):
                names.append(var_name)
            # QMessageBox.critical(self, _('node result'), str(var))
        
        ui.imageSelector.clear()
        index = 0
        for name in names:
            if index == 0:
                imgTmp = self.shell.get_value(name)
                self.loadImage(imgTmp)
            
            # Add to ui.imageSelector
            ui.imageSelector.addItem(name)
            index += 1

        # Assign onChange Event:
        ui.imageSelector.currentIndexChanged.connect(self.selectionChanged)
        ui.isGrayScale.stateChanged.connect(self.selectionChanged)
        ui.slideR.valueChanged.connect(self.selectionChanged)
        ui.slideG.valueChanged.connect(self.selectionChanged)
        ui.slideB.valueChanged.connect(self.selectionChanged)

    def loadImage(self, imgTmp):
        scene = QtWidgets.QGraphicsScene()
        
        do_grayscale = self.ui.isGrayScale.isChecked()
        slide_r_value = self.ui.slideR.value() / 100.0
        slide_g_value = self.ui.slideG.value() / 100.0
        slide_b_value = self.ui.slideB.value() / 100.0
        
        imgTmp = do_color_conversion(imgTmp, slide_r_value, slide_g_value, slide_b_value, do_grayscale, True)
        cvImg = image_resize(imgTmp, height = self.ui.imageView.height() - 20)
        
        if do_grayscale == True or len(cvImg.shape) < 3:
            height, width = cvImg.shape
            bytesPerLine = width
            qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_Grayscale8)
            pic = QtGui.QPixmap.fromImage(qImg)
            scene.addItem(QtWidgets.QGraphicsPixmapItem(pic))
            self.ui.imageView.setScene(scene)
            self.ui.imageView.show()
        else:
            height, width, channel = cvImg.shape
            bytesPerLine = 3 * width
            qImg = QImage(cvImg.data, width, height, bytesPerLine, QImage.Format_RGB888)
            pic = QtGui.QPixmap.fromImage(qImg)
            scene.addItem(QtWidgets.QGraphicsPixmapItem(pic))
            self.ui.imageView.setScene(scene)
            self.ui.imageView.show()
			
    def selectionChanged(self, index=None):
        imgTmp = self.shell.get_value(self.ui.imageSelector.currentText())
        self.loadImage(imgTmp)
        

class SelectFileDialog(QWidget):
    def __init__(self):
        super().__init__()
        self.title = 'PyQt5 file dialogs'
        self.left = 10
        self.top = 10
        self.width = 640
        self.height = 480
        self.fName=""
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.openFileNameDialog()
        #self.show()
        
    def getFileName(self):
        return self.fName
    
    def openFileNameDialog(self):
        options = QFileDialog.Options()
        # options |= QFileDialog.DontUseNativeDialog
        fileName, _ = QFileDialog.getOpenFileName(self,"Select an Image File", "","Images (*.jpg *.jpeg *.png)", options=options)
        if fileName:
            self.fName = fileName


class Help(SpyderPluginWidget):
    """
    Docstrings viewer widget
    """
    CONF_SECTION = 'help'
    CONFIGWIDGET_CLASS = HelpConfigPage
    LOG_PATH = get_conf_path(CONF_SECTION)
    FONT_SIZE_DELTA = DEFAULT_SMALL_DELTA

    # Signals
    focus_changed = Signal()

    editorstacks = []
    last_focus_editorstack = {}

    def getWidgetByClassName(self, name):
        widgets = QApplication.instance().topLevelWidgets()
        widgets = widgets + QApplication.instance().allWidgets()
        for x in widgets:
            if name in str(x.__class__).replace("<class '","").replace("'>",""):
                return x
    def getWidgetByObjectName(self, name):
        widgets = QApplication.instance().topLevelWidgets()
        widgets = widgets + QApplication.instance().allWidgets()
        for x in widgets:
            if str(x.objectName) == name:
                return x
    def getObjects(self, name, cls=True):
        import gc
        objects = []
        for obj in gc.get_objects():
            if (isinstance(obj, PythonQt.private.QObject) and
                ((cls and obj.inherits(name)) or
                (not cls and obj.objectName() == name))):
                objects.append(obj)
        return objects

    def get_current_editorstack(self, editorwindow=None):
        if self.editorstacks is not None:
            if len(self.editorstacks) == 1:
                editorstack = self.editorstacks[0]
            else:
                editorstack = self.__get_focus_editorstack()
                if editorstack is None or editorwindow is not None:
                    editorstack = self.get_last_focus_editorstack(editorwindow)
                    if editorstack is None:
                        editorstack = self.editorstacks[0]
            return editorstack
			
    def __get_focus_editorstack(self):
        fwidget = self.getWidgetByClassName('EditorStack')
        # fwidget = QApplication.focusWidget()
        if isinstance(fwidget, EditorStack):
            return fwidget
        else:
            for editorstack in self.editorstacks:
                if editorstack.isAncestorOf(fwidget):
                    return editorstack
					

    def get_last_focus_editorstack(self, editorwindow=None):
        return self.last_focus_editorstack[editorwindow]
        
    def selectImageFile(self):
        self.editorstack = self.get_current_editorstack()
        self.editor = self.editorstack.get_current_editor()
        ex = SelectFileDialog()        
        if ex.getFileName() != '':
            image_variable_name = 'img_' + str(int(time.time()))
            
            import_line = ''
            if self.editor.get_text_with_eol().find('import cv2') == -1:
                import_line = 'import cv2\n'
            self.editor.set_text(self.editor.get_text_with_eol() + import_line + '\n' + '# Load Image using OpenCV' + '\n' + image_variable_name + ' = cv2.imread(\'' + ex.getFileName() + '\', cv2.IMREAD_UNCHANGED)')
	
    def under_process(self):
        QMessageBox.critical(self, _('Under Progress'), "This step is under process.")
    
    def showdialog(self):
        global windowdlg
        windowdlg = ColorConversionWindow(self.var_info, self.shell)
        window_state = windowdlg.exec_()
        
        if window_state == 1:
            self.editorstack = self.get_current_editorstack()
            self.editor = self.editorstack.get_current_editor()
            self.editor.set_text(self.editor.get_text_with_eol() + '\n' + windowdlg.getResult(self.editor.get_text_with_eol()))
        
    def showdialog2(self):
        global windowdlg
        windowdlg = ThresholdWindow(self.var_info, self.shell)
        window_state = windowdlg.exec_()
        
        if window_state == 1:
            self.editorstack = self.get_current_editorstack()
            self.editor = self.editorstack.get_current_editor()
            self.editor.set_text(self.editor.get_text_with_eol() + '\n' + windowdlg.getResult(self.editor.get_text_with_eol()))
        
    def showdialog3(self):
        global windowdlg
        windowdlg = BlobDetectionWindow(self.var_info, self.shell)
        window_state = windowdlg.exec_()
        
        if window_state == 1:
            self.editorstack = self.get_current_editorstack()
            self.editor = self.editorstack.get_current_editor()
            self.editor.set_text(self.editor.get_text_with_eol() + '\n' + windowdlg.getResult(self.editor.get_text_with_eol()))
        
    def __init__(self, parent=None, css_path=CSS_PATH):
        SpyderPluginWidget.__init__(self, parent)

        self.shell = None
        self.var_info = []
        
        # Object name
        layout_edit = QHBoxLayout()
        layout_edit.setContentsMargins(0, 0, 0, 0)

        pybutton = QPushButton('Select a File', self)
        pybutton.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        pybutton.clicked.connect(self.selectImageFile)
        
        pybutton1 = QPushButton('Color Conversion', self)
        pybutton1.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        pybutton1.clicked.connect(self.showdialog)
        
        pybutton2 = QPushButton('Thresholding', self)
        pybutton2.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        pybutton2.clicked.connect(self.showdialog2)
        
        pybutton3 = QPushButton('Blob Detection', self)
        pybutton3.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        pybutton3.clicked.connect(self.showdialog3)
        
        welcomeTitle = QLabel()
        welcomeTitle.setText("Welcome to Image Processr!")

        layout_edit.addWidget(pybutton)
        #layout_edit.addStretch()
        layout_edit.addWidget(pybutton1)
        #layout_edit.addStretch()
        layout_edit.addWidget(pybutton2)
        #layout_edit.addStretch()
        layout_edit.addWidget(pybutton3)

        # Main layout
        layout = create_plugin_layout(QVBoxLayout())
        # we have two main widgets, but only one of them is shown at a time
        layout.addStretch()
        layout.addWidget(welcomeTitle)
        layout.addLayout(layout_edit)
        layout.addStretch()
        layout.addStretch()
        layout.addStretch()
        self.setLayout(layout)

        self._starting_up = True

    #------ SpyderPluginWidget API ---------------------------------------------
    def on_first_registration(self):
        """Action to be performed on first plugin registration"""
        self.tabify(self.main.variableexplorer)

    def get_plugin_title(self):
        """Return widget title"""
        return _('Quick Actions')

    def get_plugin_icon(self):
        """Return widget icon"""
        return ima.icon('help')

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        # return [self.rich_text_action, self.plain_text_action, self.show_source_action, MENU_SEPARATOR, self.auto_import_action]
        return []

    def register_plugin(self):
        """Register plugin in Spyder's main window"""
        self.focus_changed.connect(self.main.plugin_focus_changed)
        self.add_dockwidget()
        self.main.console.set_help(self)

        self.internal_shell = self.main.console.shell
        self.console = self.main.console

    def refresh_plugin(self):
        """Refresh widget"""
        if self._starting_up:
            self._starting_up = False
            # self.switch_to_rich_text()
            # self.show_intro_message()

    def update_font(self):
        """Update font from Preferences"""
        color_scheme = self.get_color_scheme()
        font = self.get_font()
        rich_font = self.get_font(rich_text=True)

        self.set_plain_text_font(font, color_scheme=color_scheme)
        self.set_rich_text_font(rich_font)

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        color_scheme_n = 'color_scheme_name'
        color_scheme_o = self.get_color_scheme()
        connect_n = 'connect_to_oi'
        wrap_n = 'wrap'
        wrap_o = self.get_option(wrap_n)
        self.wrap_action.setChecked(wrap_o)
        math_n = 'math'
        math_o = self.get_option(math_n)

        if color_scheme_n in options:
            self.set_plain_text_color_scheme(color_scheme_o)
        if wrap_n in options:
            self.toggle_wrap_mode(wrap_o)
        if math_n in options:
            self.toggle_math_mode(math_o)

        # To make auto-connection changes take place instantly
        self.main.editor.apply_plugin_settings(options=[connect_n])
        self.main.ipyconsole.apply_plugin_settings(options=[connect_n])

    #------ Public API (related to Help's source) -------------------------


    #------ Public API (related to rich/plain text widgets) --------------------
    @property
    def find_widget(self):
        if self.plain_text.isVisible():
            return self.plain_text.find_widget
        else:
            return self.rich_text.find_widget

    def set_rich_text_font(self, font):
        """Set rich text mode font"""
        self.rich_text.set_font(font, fixed_font=self.get_font())

    def set_plain_text_font(self, font, color_scheme=None):
        """Set plain text mode font"""
        self.plain_text.set_font(font, color_scheme=color_scheme)

    def set_plain_text_color_scheme(self, color_scheme):
        """Set plain text mode color scheme"""
        self.plain_text.set_color_scheme(color_scheme)

    @Slot(bool)
    def toggle_wrap_mode(self, checked):
        """Toggle wrap mode"""
        self.plain_text.editor.toggle_wrap_mode(checked)
        self.set_option('wrap', checked)

    def toggle_math_mode(self, checked):
        """Toggle math mode"""
        self.set_option('math', checked)

    def is_plain_text_mode(self):
        """Return True if plain text mode is active"""
        return self.plain_text.isVisible()

    def is_rich_text_mode(self):
        """Return True if rich text mode is active"""
        return self.rich_text.isVisible()

    def switch_to_plain_text(self):
        """Switch to plain text mode"""
        self.rich_help = False
        self.plain_text.show()
        self.rich_text.hide()
        self.plain_text_action.setChecked(True)

    def switch_to_rich_text(self):
        """Switch to rich text mode"""
        self.rich_help = True
        self.plain_text.hide()
        self.rich_text.show()
        self.rich_text_action.setChecked(True)
        self.show_source_action.setChecked(False)

    def set_plain_text(self, text, is_code):
        """Set plain text docs"""

        # text is coming from utils.dochelpers.getdoc
        if type(text) is dict:
            name = text['name']
            if name:
                rst_title = ''.join(['='*len(name), '\n', name, '\n',
                                    '='*len(name), '\n\n'])
            else:
                rst_title = ''

            if text['argspec']:
                definition = ''.join(['Definition: ', name, text['argspec'],
                                      '\n'])
            else:
                definition = ''

            if text['note']:
                note = ''.join(['Type: ', text['note'], '\n\n----\n\n'])
            else:
                note = ''

            full_text = ''.join([rst_title, definition, note,
                                 text['docstring']])
        else:
            full_text = text

        self.plain_text.set_text(full_text, is_code)
        self.save_text([self.plain_text.set_text, full_text, is_code])

    def set_rich_text_html(self, html_text, base_url):
        """Set rich text"""
        self.rich_text.set_html(html_text, base_url)
        self.save_text([self.rich_text.set_html, html_text, base_url])

    def show_intro_message(self):
        intro_message = _("Here you can get help of any object by pressing "
                          "%s in front of it, either on the Editor or the "
                          "Console.%s"
                          "Help can also be shown automatically after writing "
                          "a left parenthesis next to an object. You can "
                          "activate this behavior in %s.")
        prefs = _("Preferences > Help")
        if sys.platform == 'darwin':
            shortcut = "Cmd+I"
        else:
            shortcut = "Ctrl+I"

        if self.is_rich_text_mode():
            title = _("Usage")
            tutorial_message = _("New to Spyder? Read our")
            tutorial = _("tutorial")
            intro_message = intro_message % ("<b>"+shortcut+"</b>", "<br><br>",
                                             "<i>"+prefs+"</i>")
            self.set_rich_text_html(usage(title, intro_message,
                                          tutorial_message, tutorial,
                                          css_path=self.css_path),
                                    QUrl.fromLocalFile(self.css_path))
        else:
            install_sphinx = "\n\n%s" % _("Please consider installing Sphinx "
                                          "to get documentation rendered in "
                                          "rich text.")
            intro_message = intro_message % (shortcut, "\n\n", prefs)
            intro_message += install_sphinx
            self.set_plain_text(intro_message, is_code=False)

    def show_rich_text(self, text, collapse=False, img_path=''):
        """Show text in rich mode"""
        self.switch_to_plugin()
        self.switch_to_rich_text()
        context = generate_context(collapse=collapse, img_path=img_path,
                                   css_path=self.css_path)
        self.render_sphinx_doc(text, context)

    def show_plain_text(self, text):
        """Show text in plain mode"""
        self.switch_to_plugin()
        self.switch_to_plain_text()
        self.set_plain_text(text, is_code=False)

    @Slot()
    def show_tutorial(self):
        """Show the Spyder tutorial in the Help plugin, opening it if needed"""
        self.switch_to_plugin()
        tutorial_path = get_module_source_path('spyder.plugins.help.utils')
        tutorial = osp.join(tutorial_path, 'tutorial.rst')
        text = open(tutorial).read()
        self.show_rich_text(text, collapse=True)

    def handle_link_clicks(self, url):
        url = to_text_string(url.toString())
        if url == "spy://tutorial":
            self.show_tutorial()
        elif url.startswith('http'):
            programs.start_file(url)
        else:
            self.rich_text.webview.load(QUrl(url))

    # ------ Public API -------------------------------------------------------

    def set_var_data(self, data):
        self.var_info = data

    def set_shell(self, shell):
        """Bind to shell"""
        self.shell = shell
        self.shell.sig_namespace_view.connect(lambda data: self.set_var_data(data))

    def get_shell(self):
        """
        Return shell which is currently bound to Help,
        or another running shell if it has been terminated
        """
        if (not hasattr(self.shell, 'get_doc') or
                (hasattr(self.shell, 'is_running') and
                 not self.shell.is_running())):
            self.shell = None
            if self.main.ipyconsole is not None:
                shell = self.main.ipyconsole.get_current_shellwidget()
                if shell is not None and shell.kernel_client is not None:
                    self.shell = shell
            if self.shell is None:
                self.shell = self.internal_shell
        return self.shell

    def render_sphinx_doc(self, doc, context=None, css_path=CSS_PATH):
        """Transform doc string dictionary to HTML and show it"""
        # Math rendering option could have changed
        if self.main.editor is not None:
            fname = self.main.editor.get_current_filename()
            dname = osp.dirname(fname)
        else:
            dname = ''
        self._sphinx_thread.render(doc, context, self.get_option('math'),
                                   dname, css_path=self.css_path)

    def _on_sphinx_thread_html_ready(self, html_text):
        """Set our sphinx documentation based on thread result"""
        self._sphinx_thread.wait()
        self.set_rich_text_html(html_text, QUrl.fromLocalFile(self.css_path))

    def _on_sphinx_thread_error_msg(self, error_msg):
        """ Display error message on Sphinx rich text failure"""
        self._sphinx_thread.wait()
        self.plain_text_action.setChecked(True)
        sphinx_ver = programs.get_module_version('sphinx')
        QMessageBox.critical(self,
                    _('Help'),
                    _("The following error occured when calling "
                      "<b>Sphinx %s</b>. <br>Incompatible Sphinx "
                      "version or doc string decoding failed."
                      "<br><br>Error message:<br>%s"
                      ) % (sphinx_ver, error_msg))

    def show_help(self, obj_text, ignore_unknown=False):
        """Show help"""
        shell = self.get_shell()
        if shell is None:
            return
        obj_text = to_text_string(obj_text)

        if not shell.is_defined(obj_text):
            if self.get_option('automatic_import') and \
               self.internal_shell.is_defined(obj_text, force_import=True):
                shell = self.internal_shell
            else:
                shell = None
                doc = None
                source_text = None

        if shell is not None:
            doc = shell.get_doc(obj_text)
            source_text = shell.get_source(obj_text)

        is_code = False

        if self.rich_help:
            self.render_sphinx_doc(doc, css_path=self.css_path)
            return doc is not None
        elif self.docstring:
            hlp_text = doc
            if hlp_text is None:
                hlp_text = source_text
                if hlp_text is None:
                    hlp_text = self.no_doc_string
                    if ignore_unknown:
                        return False
        else:
            hlp_text = source_text
            if hlp_text is None:
                hlp_text = doc
                if hlp_text is None:
                    hlp_text = _("No source code available.")
                    if ignore_unknown:
                        return False
            else:
                is_code = True
        self.set_plain_text(hlp_text, is_code=is_code)
        return True
