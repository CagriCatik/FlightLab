import sys
import math
from typing import Dict, Any, List

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import QAction, QColor, QFont, QPalette, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QSplitter,
    QLabel,
    QDialog,
    QDialogButtonBox,
    QTextBrowser,
    QComboBox,
)

# ----------------------------
# Domain logic (unchanged math)
# ----------------------------

def recommend_power(weight_kg: float, flight_type: str = "trainer") -> float:
    if flight_type == "glider":
        return weight_kg * 65
    elif flight_type == "aerobatic":
        return weight_kg * 200
    else:
        return weight_kg * 120

def motor_efficiency_output(input_power: float, efficiency_percent: float) -> float:
    return input_power * (efficiency_percent / 100.0)

def motor_weight_from_power(power_watt: float, efficiency: float = 70.0) -> float:
    factor = 3 if efficiency <= 70 else 5
    return power_watt / factor  # grams

def battery_voltage_from_wingspan_cm(cm: float) -> float:
    if cm < 100:
        return 11.1  # 3s
    elif cm < 140:
        return 14.8  # 4s
    elif cm < 175:
        return 22.2  # 6s
    elif cm < 215:
        return 29.6  # 8s
    elif cm < 245:
        return 37.0  # 10s
    else:
        return 44.4  # 12s

def prop_pitch_speed(pitch_cm: float, rpm: float) -> float:
    return (pitch_cm * rpm) / 60000.0  # m/s

def thrust_check(thrust_g: float, plane_weight_g: float) -> Dict[str, bool]:
    return {
        "hover": thrust_g >= plane_weight_g,
        "takeoff": thrust_g >= 0.5 * plane_weight_g,
        "climb": thrust_g >= 0.33 * plane_weight_g,
    }

def esc_rating(max_current: float) -> float:
    return max_current * 1.2

def battery_discharge_check(capacity_mah: float, c_rating: float, load_current: float) -> bool:
    max_safe_continuous = (capacity_mah * c_rating * 0.6) / 1000.0  # A
    return load_current <= max_safe_continuous

# ----------------------------
# Help content
# ----------------------------

HELP_HTML = """
<h2 style="margin:0;">RC Plane Power System Estimator (Metric)</h2>
<hr/>
<h3>Inputs</h3>
<ul>
  <li><b>Weight (kg)</b>: All-up mass of the airplane ready to fly.</li>
  <li><b>Wingspan (cm)</b>: Used to suggest a nominal battery voltage (cell count) by size class.</li>
  <li><b>Flight Type</b>: Affects recommended input power per kg:
    <ul>
      <li>Glider: ~65 W/kg (sustained cruise, gentle climbs).</li>
      <li>Trainer: ~120 W/kg (general sport/training).</li>
      <li>Aerobatic: ~200 W/kg (strong vertical, 3D basics).</li>
    </ul>
  </li>
  <li><b>Motor Efficiency (%)</b>: Electrical-in to shaft-out estimate.</li>
  <li><b>Prop Pitch (cm)</b> and <b>RPM</b>: Used to compute static pitch speed.</li>
  <li><b>Static Thrust (g)</b>: Estimated thrust at full power for comparison to weight.</li>
  <li><b>Max Current (A)</b>: Expected worst-case continuous draw.</li>
  <li><b>Battery Capacity (mAh)</b> and <b>C-rate</b>: For discharge safety check.</li>
</ul>

<h3>Outputs</h3>
<ul>
  <li><b>Required Input Power (W)</b>: Weight * guideline by flight type.</li>
  <li><b>Expected Shaft Output Power (W)</b>: Input * Efficiency.</li>
  <li><b>Estimated Motor Weight (g)</b>: Heuristic from power and efficiency.</li>
  <li><b>Recommended Battery Voltage (V)</b>: Based on wingspan bands.</li>
  <li><b>Static Pitch Speed (m/s)</b>: Pitch(cm) * RPM / 60000 (no slip).</li>
  <li><b>Thrust Checks</b>:
    <ul>
      <li>Hover: thrust >= weight (true hover potential).</li>
      <li>Takeoff: thrust >= 0.5 * weight (short ROG takeoff typical).</li>
      <li>Climb: thrust >= 0.33 * weight (reasonable climb-out).</li>
    </ul>
  </li>
  <li><b>ESC Recommendation (A)</b>: 20% margin above max current.</li>
  <li><b>Battery Safe</b>: Checks continuous discharge using 60% of C rating.</li>
</ul>

<h3>Assumptions and Limits</h3>
<ul>
  <li>Rules-of-thumb; tune for your airframe, prop, and environment.</li>
  <li>Voltage suggestion is nominal; under load voltage sags.</li>
  <li>Pitch speed is an idealized static estimate; in flight, slip reduces speed.</li>
  <li>Battery discharge safety uses a conservative 60% of rated C for continuous load.</li>
  <li>ESC margin is a heuristic. For poor cooling or hot climate, increase headroom.</li>
</ul>
<p style="color:#aaaaaa; font-size: 90%;">Source guideline basis: rcplanes.online setup guidance (summary). This app does not guarantee suitability. Verify with ground tests and telemetry.</p>
"""

# ----------------------------
# UI
# ----------------------------

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Glossary and Notes")
        self.resize(680, 560)
        v = QVBoxLayout(self)
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml(HELP_HTML)
        v.addWidget(tb)
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        v.addWidget(btns)

class PlanePowerCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RC Plane Power System Estimator")
        self.resize(780, 520)
        self._apply_dark_theme()
        self._build_menu()
        self._build_ui()

    # Menu
    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Results to CSV...", self)
        export_action.triggered.connect(self._export_csv)
        file_menu.addAction(export_action)
        file_menu.addSeparator()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        help_menu = menubar.addMenu("Help")
        glossary_action = QAction("Open Glossary and Notes", self)
        glossary_action.triggered.connect(self._open_help)
        help_menu.addAction(glossary_action)

    # Main UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: inputs
        inputs_group = QGroupBox("Inputs")
        form = QFormLayout(inputs_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        inputs_group.setContentsMargins(8, 8, 8, 8)

        self.weight_kg = QLineEdit()
        self.weight_kg.setPlaceholderText("e.g. 1.2")
        self.weight_kg.setValidator(self._val_float_nonneg())
        self.weight_kg.setToolTip("Plane all-up weight in kg.")

        self.wingspan_cm = QLineEdit()
        self.wingspan_cm.setPlaceholderText("e.g. 120")
        self.wingspan_cm.setValidator(self._val_float_nonneg())
        self.wingspan_cm.setToolTip("Wingspan in cm. Used to suggest nominal voltage.")

        self.flight_type = QComboBox()
        self.flight_type.addItems(["trainer", "glider", "aerobatic"])
        self.flight_type.setToolTip("Guideline power class.")

        self.efficiency_pct = QLineEdit()
        self.efficiency_pct.setPlaceholderText("e.g. 70")
        self.efficiency_pct.setValidator(self._val_float_range(1, 99.9))
        self.efficiency_pct.setToolTip("Motor/drive efficiency in percent.")

        self.pitch_cm = QLineEdit()
        self.pitch_cm.setPlaceholderText("e.g. 15")
        self.pitch_cm.setValidator(self._val_float_nonneg())
        self.pitch_cm.setToolTip("Prop pitch in cm (static estimate).")

        self.rpm = QLineEdit()
        self.rpm.setPlaceholderText("e.g. 9000")
        self.rpm.setValidator(self._val_float_nonneg())
        self.rpm.setToolTip("Estimated RPM at full power.")

        self.thrust_g = QLineEdit()
        self.thrust_g.setPlaceholderText("e.g. 1200")
        self.thrust_g.setValidator(self._val_float_nonneg())
        self.thrust_g.setToolTip("Estimated static thrust in grams.")

        self.max_current_a = QLineEdit()
        self.max_current_a.setPlaceholderText("e.g. 45")
        self.max_current_a.setValidator(self._val_float_nonneg())
        self.max_current_a.setToolTip("Worst-case continuous current draw in A.")

        self.batt_capacity_mah = QLineEdit()
        self.batt_capacity_mah.setPlaceholderText("e.g. 3000")
        self.batt_capacity_mah.setValidator(self._val_float_nonneg())
        self.batt_capacity_mah.setToolTip("Battery capacity in mAh.")

        self.c_rate = QLineEdit()
        self.c_rate.setPlaceholderText("e.g. 35")
        self.c_rate.setValidator(self._val_float_nonneg())
        self.c_rate.setToolTip("Battery C rating.")

        form.addRow("Weight (kg):", self.weight_kg)
        form.addRow("Wingspan (cm):", self.wingspan_cm)
        form.addRow("Flight type:", self.flight_type)
        form.addRow("Efficiency (%):", self.efficiency_pct)
        form.addRow("Prop pitch (cm):", self.pitch_cm)
        form.addRow("RPM:", self.rpm)
        form.addRow("Static thrust (g):", self.thrust_g)
        form.addRow("Max current (A):", self.max_current_a)
        form.addRow("Capacity (mAh):", self.batt_capacity_mah)
        form.addRow("C-rate:", self.c_rate)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self._on_calculate)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        self.help_btn = QPushButton("Glossary")
        self.help_btn.clicked.connect(self._open_help)
        btn_row.addWidget(self.calc_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.help_btn)

        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(6)
        left_box.addWidget(inputs_group)
        left_box.addLayout(btn_row)
        leftw = QWidget()
        leftw.setLayout(left_box)
        splitter.addWidget(leftw)

        # Right: results
        rightw = QWidget()
        right = QVBoxLayout(rightw)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)

        header = QLabel("Results")
        small_bold = QFont("Arial", 10, QFont.Weight.DemiBold)
        header.setFont(small_bold)
        right.addWidget(header)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        right.addWidget(self.table, stretch=1)

        tips = QLabel("ESC rating adds 20% margin. Battery check uses 60% of rated C for continuous load.")
        tips.setObjectName("tips")
        right.addWidget(tips)

        splitter.addWidget(rightw)
        splitter.setSizes([360, 420])

        root.addWidget(splitter)

    # Validators
    def _val_float_nonneg(self):
        return QRegularExpressionValidator(QRegularExpression(r"^\s*(\d+(\.\d+)?)\s*$"), self)

    def _val_float_range(self, low: float, high: float):
        # Accept numeric, range-checked later
        return QRegularExpressionValidator(QRegularExpression(r"^\s*(\d+(\.\d+)?)\s*$"), self)

    # Actions
    def _on_clear(self):
        self.table.setRowCount(0)
        for w in [
            self.weight_kg, self.wingspan_cm, self.efficiency_pct, self.pitch_cm,
            self.rpm, self.thrust_g, self.max_current_a, self.batt_capacity_mah, self.c_rate
        ]:
            w.clear()
        self.flight_type.setCurrentIndex(0)
        self.statusBar().clearMessage()

    def _on_calculate(self):
        try:
            weight = self._f(self.weight_kg, "Weight (kg)")
            wingspan = self._f(self.wingspan_cm, "Wingspan (cm)")
            eff = self._pct(self.efficiency_pct, "Efficiency (%)")
            pitch = self._f(self.pitch_cm, "Prop pitch (cm)")
            rpm = self._f(self.rpm, "RPM")
            thrust_g = self._f(self.thrust_g, "Static thrust (g)")
            max_i = self._f(self.max_current_a, "Max current (A)")
            cap = self._f(self.batt_capacity_mah, "Capacity (mAh)")
            c_rate = self._f(self.c_rate, "C-rate")
            ftype = self.flight_type.currentText()

            input_power = recommend_power(weight, ftype)
            output_power = motor_efficiency_output(input_power, eff)
            est_motor_weight = motor_weight_from_power(input_power, eff)
            rec_voltage = battery_voltage_from_wingspan_cm(wingspan)
            p_speed = prop_pitch_speed(pitch, rpm)
            t_eval = thrust_check(thrust_g, weight * 1000.0)
            esc_rec = esc_rating(max_i)
            batt_ok = battery_discharge_check(cap, c_rate, max_i)

            results = [
                ("Required input power (W)", f"{input_power:.1f}"),
                ("Expected shaft output power (W)", f"{output_power:.1f}"),
                ("Estimated motor weight (g)", f"{est_motor_weight:.1f}"),
                ("Recommended battery voltage (V)", f"{rec_voltage:.1f}"),
                ("Static pitch speed (m/s)", f"{p_speed:.2f}"),
                ("Thrust: hover", "OK" if t_eval["hover"] else "No"),
                ("Thrust: takeoff", "OK" if t_eval["takeoff"] else "No"),
                ("Thrust: climb", "OK" if t_eval["climb"] else "No"),
                ("ESC recommendation (A)", f"{esc_rec:.1f}"),
                ("Battery safe (continuous)", "OK" if batt_ok else "No"),
            ]
            self._populate(results)
            self.statusBar().showMessage("Calculated.", 2500)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    # Parsing helpers
    def _f(self, widget: QLineEdit, label: str) -> float:
        txt = widget.text().strip()
        if not txt:
            raise ValueError(f"{label} is required.")
        try:
            val = float(txt)
        except Exception:
            raise ValueError(f"{label} must be a number.")
        if val < 0:
            raise ValueError(f"{label} must be non-negative.")
        return val

    def _pct(self, widget: QLineEdit, label: str) -> float:
        val = self._f(widget, label)
        if not (0 < val <= 100):
            raise ValueError(f"{label} must be in (0, 100].")
        return val

    # Results table
    def _populate(self, rows: List[tuple]):
        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            k_item = QTableWidgetItem(k)
            v_item = QTableWidgetItem(v)
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 0, k_item)
            self.table.setItem(r, 1, v_item)
        self.table.resizeRowsToContents()

    # Export
    def _export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "plane_power_results.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            lines = ["Metric,Value"]
            for r in range(self.table.rowCount()):
                k = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
                v = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                # Basic CSV escaping
                k = '"' + k.replace('"', '""') + '"'
                v = '"' + v.replace('"', '""') + '"'
                lines.append(f"{k},{v}")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.statusBar().showMessage(f"Exported to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    # Help
    def _open_help(self):
        HelpDialog(self).exec()

    # Theme
    def _apply_dark_theme(self):
        base_font = QFont("Arial", 10)
        QApplication.instance().setFont(base_font)

        palette = QPalette()
        palette.setColor(QPalette.Window, QColor("#121212"))
        palette.setColor(QPalette.WindowText, QColor("#dcdcdc"))
        palette.setColor(QPalette.Base, QColor("#1a1a1a"))
        palette.setColor(QPalette.AlternateBase, QColor("#171717"))
        palette.setColor(QPalette.ToolTipBase, QColor("#2a2a2a"))
        palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
        palette.setColor(QPalette.Text, QColor("#dcdcdc"))
        palette.setColor(QPalette.Button, QColor("#232323"))
        palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
        palette.setColor(QPalette.Highlight, QColor("#0a84ff"))
        palette.setColor(QPalette.HighlightedText, QColor("#000000"))
        self.setPalette(palette)

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #121212;
                color: #dcdcdc;
                font-family: Arial;
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #2b2b2b;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 2px;
                font-size: 10pt;
            }
            QLineEdit {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                padding: 4px 6px;
                font-size: 10pt;
            }
            QLineEdit:focus {
                border: 1px solid #0a84ff;
            }
            QComboBox {
                background-color: #1a1a1a;
                color: #ffffff;
                border: 1px solid #3a3a3a;
                border-radius: 5px;
                padding: 3px 6px;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #0a84ff;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 10pt;
                min-height: 26px;
            }
            QPushButton:hover { background-color: #2b95ff; }
            QPushButton:pressed { background-color: #086ed6; }
            QTableWidget {
                gridline-color: #2a2a2a;
                background-color: #161616;
                alternate-background-color: #141414;
                color: #dcdcdc;
                selection-background-color: #0a84ff;
                selection-color: #000000;
                border: 1px solid #2a2a2a;
                border-radius: 6px;
                font-size: 10pt;
            }
            QHeaderView::section {
                background-color: #1c1c1c;
                color: #dcdcdc;
                padding: 4px 6px;
                border: 0px;
                border-right: 1px solid #2a2a2a;
                font-size: 10pt;
            }
            QSplitter::handle { background: #1b1b1b; }
            QLabel#tips {
                color: #a0a0a0;
                padding: 4px 0;
                font-size: 9pt;
            }
            QTextBrowser {
                background-color: #1a1a1a;
                color: #e6e6e6;
                border: 1px solid #3a3a3a;
                border-radius: 6px;
                padding: 6px;
                font-size: 10pt;
            }
            """
        )

# ----------------------------
# Entrypoint
# ----------------------------

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("RC Plane Power System Estimator")
    win = PlanePowerCalculator()
    win.show()
    sys.exit(app.exec())
