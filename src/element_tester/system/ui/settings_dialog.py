"""
Settings Dialog
===============

UI dialog for configuring application settings.
Allows user to select relay driver (MCC_ERB or MCC_PDIS) and meter driver (FLUKE287 or UT61E).
"""

from __future__ import annotations
from typing import Optional
from pathlib import Path

from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton, QMessageBox, QLineEdit, QGridLayout

try:
    from element_tester.system.procedures.settings_manager import SettingsManager, AppSettings
except ImportError:
    SettingsManager = None
    AppSettings = None


class SettingsDialog(QDialog):
    """
    Dialog for configuring application settings.
    
    Settings saved to: system/core/instrument_configuration.json
    """
    
    def __init__(self, parent: Optional[QtWidgets.QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(500, 400)
        
        if SettingsManager is None:
            QMessageBox.critical(self, "Import Error", "Failed to import SettingsManager")
            self.reject()
            return
        
        self.settings_manager = SettingsManager()
        self.current_settings = self.settings_manager.load()
        
        self._build_ui()
        self._load_current_settings()
    
    def _build_ui(self):
        """Build the settings dialog UI."""
        # Set dark theme background
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
        pal.setColor(QtGui.QPalette.ColorRole.WindowText, QtGui.QColor(255, 255, 255))
        pal.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(35, 35, 35))
        pal.setColor(QtGui.QPalette.ColorRole.Text, QtGui.QColor(255, 255, 255))
        self.setPalette(pal)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Title
        title = QLabel("Application Settings")
        title_font = title.font()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                background-color: #2a82da;
                color: #FFFFFF;
                padding: 10px;
                border-radius: 5px;
            }
        """)
        main_layout.addWidget(title)
        
        # Relay Driver Selection
        relay_group = QtWidgets.QGroupBox("Relay Driver Configuration")
        relay_group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FFFFFF;
            }
        """)
        relay_layout = QVBoxLayout()
        
        # Dropdown label and combo
        dropdown_layout = QHBoxLayout()
        
        relay_label = QLabel("Select Relay Driver:")
        relay_label_font = relay_label.font()
        relay_label_font.setPointSize(11)
        relay_label.setFont(relay_label_font)
        relay_label.setStyleSheet("QLabel { color: #FFFFFF; }")
        dropdown_layout.addWidget(relay_label)
        
        self.relay_combo = QComboBox()
        self.relay_combo.addItems(["MCC_ERB", "MCC_PDIS"])
        self.relay_combo.setMinimumHeight(35)
        combo_font = self.relay_combo.font()
        combo_font.setPointSize(11)
        self.relay_combo.setFont(combo_font)
        self.relay_combo.setStyleSheet("""
            QComboBox {
                background-color: #353535;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 2px solid #2a82da;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #353535;
                color: #FFFFFF;
                selection-background-color: #2a82da;
                selection-color: #FFFFFF;
            }
        """)
        dropdown_layout.addWidget(self.relay_combo, 1)
        
        relay_layout.addLayout(dropdown_layout)
        
        # Driver descriptions
        desc_label = QLabel(
            "<b>MCC_ERB:</b> MCC USB-ERB08 (Board 0, Ports 12-13)<br>"
            "<b>MCC_PDIS:</b> MCC USB-PDIS08 (Board 1, Port 1)"
        )
        desc_label.setStyleSheet("QLabel { padding: 10px; background-color: #404040; color: #FFFFFF; border-radius: 3px; border: 1px solid #555555; }")
        relay_layout.addWidget(desc_label)
        
        relay_group.setLayout(relay_layout)
        main_layout.addWidget(relay_group)
        
        # Meter Driver Selection
        meter_group = QtWidgets.QGroupBox("Meter Driver Configuration")
        meter_group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #FFFFFF;
            }
        """)
        meter_layout = QVBoxLayout()
        
        # Dropdown label and combo
        meter_dropdown_layout = QHBoxLayout()
        
        meter_label = QLabel("Select Meter Driver:")
        meter_label_font = meter_label.font()
        meter_label_font.setPointSize(11)
        meter_label.setFont(meter_label_font)
        meter_label.setStyleSheet("QLabel { color: #FFFFFF; }")
        meter_dropdown_layout.addWidget(meter_label)
        
        self.meter_combo = QComboBox()
        self.meter_combo.addItems(["FLUKE287", "UT61E"])
        self.meter_combo.setMinimumHeight(35)
        meter_combo_font = self.meter_combo.font()
        meter_combo_font.setPointSize(11)
        self.meter_combo.setFont(meter_combo_font)
        self.meter_combo.setStyleSheet("""
            QComboBox {
                background-color: #353535;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QComboBox:focus {
                border: 2px solid #2a82da;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #353535;
                color: #FFFFFF;
                selection-background-color: #2a82da;
                selection-color: #FFFFFF;
            }
        """)
        meter_dropdown_layout.addWidget(self.meter_combo, 1)
        
        meter_layout.addLayout(meter_dropdown_layout)
        
        # Driver descriptions
        meter_desc_label = QLabel(
            "<b>FLUKE287:</b> Fluke 287 Datalogging Multimeter (Serial)<br>"
            "<b>UT61E:</b> UNI-T UT61E Multimeter (USB HID via UT61xP)"
        )
        meter_desc_label.setStyleSheet("QLabel { padding: 10px; background-color: #404040; color: #FFFFFF; border-radius: 3px; border: 1px solid #555555; }")
        meter_layout.addWidget(meter_desc_label)

        meter_ports = QGridLayout()
        meter_ports.setContentsMargins(4, 8, 4, 4)
        meter_ports.setHorizontalSpacing(12)
        meter_ports.setVerticalSpacing(8)

        fluke_label = QLabel("FLUKE287 COM Port:")
        fluke_label.setStyleSheet("QLabel { color: #FFFFFF; }")
        self.fluke_com_edit = QLineEdit()
        self.fluke_com_edit.setPlaceholderText("COM11")
        self.fluke_com_edit.setMinimumHeight(30)
        self.fluke_com_edit.setStyleSheet("""
            QLineEdit {
                background-color: #353535;
                color: #FFFFFF;
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 5px;
            }
            QLineEdit:focus {
                border: 2px solid #2a82da;
            }
        """)

        meter_ports.addWidget(fluke_label, 0, 0)
        meter_ports.addWidget(self.fluke_com_edit, 0, 1)

        meter_layout.addLayout(meter_ports)
        
        meter_group.setLayout(meter_layout)
        main_layout.addWidget(meter_group)
        
        main_layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("Apply")
        self.cancel_button = QPushButton("Cancel")
        
        for btn in [self.save_button, self.cancel_button]:
            btn.setMinimumWidth(100)
            btn.setMinimumHeight(35)
            btn_font = btn.font()
            btn_font.setPointSize(11)
            btn_font.setBold(True)
            btn.setFont(btn_font)
        
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border-radius: 5px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        button_layout.addWidget(self.save_button)
        button_layout.addSpacing(10)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()
        
        main_layout.addLayout(button_layout)
        
        # Connect signals
        self.save_button.clicked.connect(self._on_save)
        self.cancel_button.clicked.connect(self.reject)
    
    def _load_current_settings(self):
        """Load current settings into UI controls."""
        # Set relay driver combo
        index = self.relay_combo.findText(self.current_settings.relay_driver)
        if index >= 0:
            self.relay_combo.setCurrentIndex(index)
        
        # Set meter driver combo
        meter_index = self.meter_combo.findText(self.current_settings.meter_driver)
        if meter_index >= 0:
            self.meter_combo.setCurrentIndex(meter_index)

        self.fluke_com_edit.setText(self.current_settings.fluke_port)
    
    def _on_save(self):
        """Save settings and close dialog."""
        # Update settings from UI
        self.current_settings.relay_driver = self.relay_combo.currentText()
        self.current_settings.meter_driver = self.meter_combo.currentText()

        self.current_settings.fluke_port = self.fluke_com_edit.text().strip().upper() or "COM11"
        
        # Save to file
        success = self.settings_manager.save(self.current_settings)
        
        if success:
            QMessageBox.information(
                self,
                "Settings Applied",
                f"Instrument configuration updated.\n\n"
                f"Relay Driver: {self.current_settings.relay_driver}\n"
                f"Meter Driver: {self.current_settings.meter_driver}\n\n"
                f"These settings will be used on the next test run."
            )
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                "Failed to save settings. Check logs for details."
            )


# Standalone test
if __name__ == "__main__":
    import sys
    from PyQt6.QtGui import QPalette, QColor
    
    app = QtWidgets.QApplication(sys.argv)
    
    # Apply dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
    dark_palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(dark_palette)
    
    dlg = SettingsDialog()
    result = dlg.exec()
    print(f"Dialog result: {result}")
    sys.exit(0)
