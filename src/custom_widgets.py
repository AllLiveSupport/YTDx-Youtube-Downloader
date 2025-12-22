"""
YTDx - Custom Widgets Module
Özelleştirilmiş PyQt6 widget'ları
"""

from PyQt6.QtWidgets import QLineEdit, QTextEdit, QMenu
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction
from src.language import _


class TranslatedLineEdit(QLineEdit):
    """Çevirisi yapılmış sağ tık menüsüne sahip QLineEdit."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Standart eylemler
        undo_action = QAction(_("undo"), self)
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self.isUndoAvailable())
        
        redo_action = QAction(_("redo"), self)
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self.isRedoAvailable())
        
        cut_action = QAction(_("cut"), self)
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(not self.isReadOnly() and self.hasSelectedText())
        
        copy_action = QAction(_("copy"), self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.hasSelectedText())
        
        paste_action = QAction(_("paste"), self)
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(not self.isReadOnly())
        
        delete_action = QAction(_("delete"), self)
        delete_action.triggered.connect(self.delete_selected)
        delete_action.setEnabled(not self.isReadOnly() and self.hasSelectedText())
        
        select_all_action = QAction(_("select_all"), self)
        select_all_action.triggered.connect(self.selectAll)
        select_all_action.setEnabled(not self.text() == "")
        
        # Menüye eylemleri ekle
        menu.addAction(undo_action)
        menu.addAction(redo_action)
        menu.addSeparator()
        menu.addAction(cut_action)
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(select_all_action)
        
        # Menüyü göster
        menu.exec(self.mapToGlobal(pos))
    
    def delete_selected(self):
        """Seçili metni siler."""
        self.insert("")


class TranslatedTextEdit(QTextEdit):
    """Çevirisi yapılmış sağ tık menüsüne sahip QTextEdit."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
    
    def show_context_menu(self, pos):
        menu = QMenu(self)
        
        # Standart eylemler
        undo_action = QAction(_("undo"), self)
        undo_action.triggered.connect(self.undo)
        undo_action.setEnabled(self.document().isUndoAvailable())
        
        redo_action = QAction(_("redo"), self)
        redo_action.triggered.connect(self.redo)
        redo_action.setEnabled(self.document().isRedoAvailable())
        
        cut_action = QAction(_("cut"), self)
        cut_action.triggered.connect(self.cut)
        cut_action.setEnabled(not self.isReadOnly() and self.textCursor().hasSelection())
        
        copy_action = QAction(_("copy"), self)
        copy_action.triggered.connect(self.copy)
        copy_action.setEnabled(self.textCursor().hasSelection())
        
        paste_action = QAction(_("paste"), self)
        paste_action.triggered.connect(self.paste)
        paste_action.setEnabled(not self.isReadOnly())
        
        delete_action = QAction(_("delete"), self)
        delete_action.triggered.connect(lambda: self.textCursor().removeSelectedText())
        delete_action.setEnabled(not self.isReadOnly() and self.textCursor().hasSelection())
        
        select_all_action = QAction(_("select_all"), self)
        select_all_action.triggered.connect(self.selectAll)
        select_all_action.setEnabled(not self.toPlainText() == "")
        
        # Menüye eylemleri ekle
        menu.addAction(undo_action)
        menu.addAction(redo_action)
        menu.addSeparator()
        menu.addAction(cut_action)
        menu.addAction(copy_action)
        menu.addAction(paste_action)
        menu.addAction(delete_action)
        menu.addSeparator()
        menu.addAction(select_all_action)
        
        # Menüyü göster
        menu.exec(self.mapToGlobal(pos))
