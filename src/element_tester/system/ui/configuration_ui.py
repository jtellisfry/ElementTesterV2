from __future__ import annotations
from typing import Tuple
from PyQt6 import QtWidgets, QtCore, QtGui


class ClickableZone(QtWidgets.QFrame):
    """A clickable zone that triggers an action when clicked anywhere."""
    clicked = QtCore.pyqtSignal()
    
    def __init__(self, text: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.setMinimumSize(140, 100)
        self.setMaximumWidth(190)
        self.setStyleSheet("""
            QFrame {
                background-color: #9C27B0;
                border: 3px solid #7B1FA2;
                border-radius: 12px;
            }
            QFrame:hover {
                background-color: #AB47BC;
                border: 3px solid #8E24AA;
            }
        """)
        
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        label = QtWidgets.QLabel(text)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setFont(self._big_font(32))
        label.setStyleSheet("color: white; border: none; background: transparent;")
        layout.addWidget(label)
    
    def _big_font(self, pts: int) -> QtGui.QFont:
        f = QtGui.QFont()
        f.setPointSize(pts)
        f.setBold(True)
        return f
    
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class TouchSelector(QtWidgets.QWidget):
    """A touch-friendly selector: large left/right clickable zones and a central value display.

    Keeps a hidden QComboBox as the data store so callers can use `currentData()`.
    """

    def __init__(self, items: Tuple[int, ...], parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self._items = list(items)
        self._combo = QtWidgets.QComboBox()
        for it in self._items:
            self._combo.addItem(str(it), it)
        self._combo.setCurrentIndex(0)
        
        # Add border and background
        self.setStyleSheet("""
            TouchSelector {
                background-color: #E1BEE7;
                border: 4px solid #9C27B0;
                border-radius: 16px;
            }
        """)

        h = QtWidgets.QHBoxLayout(self)
        h.setContentsMargins(12, 12, 12, 12)
        h.setSpacing(12)

        # Left clickable zone
        self.zone_prev = ClickableZone("❮")
        self.zone_prev.setMinimumSize(140, 100)
        
        # Center value display
        self.value_label = QtWidgets.QLabel(str(self._items[0]))
        self.value_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumWidth(260)
        self.value_label.setMinimumHeight(100)
        self.value_label.setFont(self._big_font(28))
        self.value_label.setStyleSheet("""
            QLabel {
                color: #2E0B46;
                background-color: white;
                border: 3px solid #9C27B0;
                border-radius: 12px;
                padding: 10px;
            }
        """)
        
        # Right clickable zone
        self.zone_next = ClickableZone("❯")
        self.zone_next.setMinimumSize(140, 100)

        h.addWidget(self.zone_prev)
        h.addWidget(self.value_label, stretch=1)
        h.addWidget(self.zone_next)

        self.zone_prev.clicked.connect(self._decrement)
        self.zone_next.clicked.connect(self._increment)
        
        # Store references for backward compatibility
        self.btn_prev = self.zone_prev
        self.btn_next = self.zone_next

        # keep hidden combo for API compatibility
        self._combo.hide()

    def _big_font(self, pts: int) -> QtGui.QFont:
        f = QtGui.QFont()
        f.setPointSize(pts)
        f.setBold(True)
        return f

    def _increment(self):
        idx = self._combo.currentIndex()
        idx = (idx + 1) % len(self._items)
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

    def _decrement(self):
        idx = self._combo.currentIndex()
        idx = (idx - 1) % len(self._items)
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

    # API compatibility methods
    def currentData(self):
        return self._combo.currentData()

    def currentIndex(self):
        return self._combo.currentIndex()

    def setCurrentIndex(self, idx: int):
        self._combo.setCurrentIndex(idx)
        self.value_label.setText(str(self._items[idx]))

class ConfigurationWindow(QtWidgets.QDialog):
    """Configuration form shown after scanning WO/PN.

    - Choose element voltage and wattage from predefined tuples
    - Emits `configConfirmed(voltage, wattage)` when Continue pressed
    """

    configConfirmed = QtCore.pyqtSignal(int, int)

    VOLTAGE_OPTIONS: Tuple[int, ...] = (208,220,230,240,440,480)
    WATTAGE_OPTIONS: Tuple[int, ...] = (7000,7500,8000,8500,9000,11000,12800,14000)

    # Manual mapping: keys are (voltage, wattage) tuples, values are (r_min_ohm, r_max_ohm).
    # Populate this mapping with the exact ranges you want for each combo.
    RESISTANCE_RANGE: dict[tuple[int, int], tuple[float, float]] = {
        (208, 7000): (18.2/2, 19.6/2),
        (230, 7000): (22.0/2, 23.5/2),
        (240, 7000): (23.9/2, 24.6/2),
        (480, 7000): (90.2/2, 91.2/2),
        (208, 8500): (15.0/2, 16.6/2),
        (230, 8500): (18.0/2, 19.6/2),
        (240, 8500): (19.5/2, 21.5/2),
        (480, 8500): (79.8/2, 82.5/2),
    }

    def __init__(self, work_order: str, part_number: str, parent: QtWidgets.QWidget | None = None):
        super().__init__(parent)
        self.work_order = work_order
        self.part_number = part_number
        self.setWindowTitle("Configuration")
        self.resize(1100, 700)
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(50, 35, 50, 35)
        root.setSpacing(20)

        # Header
        header = QtWidgets.QLabel("Configuration")
        f = header.font()
        f.setPointSize(40)
        f.setBold(True)
        header.setFont(f)
        header.setText(header.text().upper())
        header.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        header.setMinimumHeight(80)
        header.setStyleSheet(
            "background-color: #6A1B9A; color: white; padding: 10px; border-radius: 8px;"
        )
        root.addWidget(header)
        # Create visually prominent, rounded bars for the two fields.
        # Each bar contains a centered label and the combo box (combo is visually embedded).
        def _make_field(title: str, items: Tuple[int, ...]) -> tuple[QtWidgets.QWidget, TouchSelector]:
            container = QtWidgets.QWidget()
            container.setMinimumHeight(185)
            container.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Fixed)
            container.setStyleSheet(
                "background-color: #D6B3FF; border-radius: 12px;"
            )
            lay = QtWidgets.QVBoxLayout(container)
            lay.setContentsMargins(20, 15, 20, 15)

            label = QtWidgets.QLabel(title)
            lf = label.font()
            lf.setPointSize(20)
            lf.setBold(True)
            label.setFont(lf)
            label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #2E0B46;")

            selector = TouchSelector(items)

            lay.addWidget(label)
            lay.addWidget(selector, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
            return container, selector

        v_widget, self.voltage_combo = _make_field("Element Voltage(V)", self.VOLTAGE_OPTIONS)
        w_widget, self.wattage_combo = _make_field("Element Wattage(W)", self.WATTAGE_OPTIONS)

        # Add a bit of spacing between the bars
        root.addWidget(v_widget)
        root.addSpacing(15)
        root.addWidget(w_widget)
        
        # Resistance range label (touch-friendly large text)
        self.range_label = QtWidgets.QLabel("")
        rf = self.range_label.font()
        rf.setPointSize(18)
        rf.setBold(True)
        self.range_label.setFont(rf)
        self.range_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.range_label.setStyleSheet("color: #FFFFFF;")
        root.addSpacing(12)
        root.addWidget(self.range_label)

        # Wire selector zones to update the computed resistance label
        try:
            self.voltage_combo.zone_prev.clicked.connect(self._update_resistance_label)
            self.voltage_combo.zone_next.clicked.connect(self._update_resistance_label)
            self.wattage_combo.zone_prev.clicked.connect(self._update_resistance_label)
            self.wattage_combo.zone_next.clicked.connect(self._update_resistance_label)
        except Exception:
            # If selectors are not TouchSelector (fallback), ignore
            pass

        # Initialize the label text
        self._update_resistance_label()

        # Spacer
        root.addStretch(1)

        # Buttons
        btn_row = QtWidgets.QHBoxLayout()
        btn_row.addStretch(1)

        self.btn_continue = QtWidgets.QPushButton("CONTINUE")
        self.btn_exit = QtWidgets.QPushButton("EXIT")
        self._style_main_button(self.btn_continue, bg="#4CAF50")
        self._style_main_button(self.btn_exit, bg="#C62828")

        btn_row.addWidget(self.btn_continue)
        btn_row.addSpacing(30)
        btn_row.addWidget(self.btn_exit)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

        # Signals
        self.btn_continue.clicked.connect(self._on_continue)
        self.btn_exit.clicked.connect(self.reject)

    def _style_main_button(self, btn: QtWidgets.QPushButton, bg: str = "#4CAF50"):
        btn.setMinimumWidth(180)
        btn.setMinimumHeight(70)
        f = btn.font()
        f.setPointSize(18)
        f.setBold(True)
        btn.setFont(f)
        btn.setStyleSheet(
            f"QPushButton {{ background-color: {bg}; color: white; border-radius: 10px; padding: 10px 20px; }}"
        )

    def _on_continue(self):
        v = int(self.voltage_combo.currentData())
        w = int(self.wattage_combo.currentData())
        # Emit configuration and close dialog with Accepted
        self.configConfirmed.emit(v, w)
        self.accept()

    def _compute_resistance_range(self, voltage: int, wattage: int) -> tuple[float, float]:
        """Return (r_min, r_max) in ohms for the given voltage and wattage.
        Uses `RESISTANCE_OVERRIDES` if present. If no mapping exists, returns (0.0, 0.0).
        """
        key = (int(voltage), int(wattage))
        return self.RESISTANCE_RANGE.get(key, (0.0, 0.0))

    def _update_resistance_label(self):
        try:
            v = int(self.voltage_combo.currentData())
            w = int(self.wattage_combo.currentData())
        except Exception:
            # fallback to first options
            v = int(self.VOLTAGE_OPTIONS[0])
            w = int(self.WATTAGE_OPTIONS[0])
        rmin, rmax = self._compute_resistance_range(v, w)
        if rmin == 0.0 and rmax == 0.0:
            self.range_label.setText(f"Resistance range: not configured for {v} V / {w} W")
        else:
            self.range_label.setText(f"Expected resistance: {rmin:.1f} - {rmax:.1f} Ω")

    @classmethod
    def get_configuration(cls, parent: QtWidgets.QWidget | None, wo: str, pn: str) -> tuple[int, int] | None:
        dlg = cls(wo, pn, parent)
        res = dlg.exec()
        if res == QtWidgets.QDialog.DialogCode.Accepted:
            v = int(dlg.voltage_combo.currentData())
            w = int(dlg.wattage_combo.currentData())
            rmin, rmax = dlg._compute_resistance_range(v, w)
            return int(v), int(w), (float(rmin), float(rmax))
        return None


if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    def _on_configured(v: int, w: int):
        print(f"Selected configuration: {v} V, {w} W")

    # Show dialog for manual inspection
    dlg = ConfigurationWindow("DEMO_WO", "DEMO_PN")
    dlg.configConfirmed.connect(_on_configured)
    dlg.show()

    sys.exit(app.exec())
