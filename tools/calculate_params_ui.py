import sys
from typing import List, Dict, Any

from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtGui import (
    QAction,
    QColor,
    QFont,
    QPalette,
    QRegularExpressionValidator,
)
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
)


HELP_HTML = """
<h2 style="margin:0;">Motor & ESC Glossary and Calculation Notes</h2>
<hr/>
<h3>KV (RPM per Volt)</h3>
<p><b>KV</b> is a motor constant indicating the no-load speed increase per volt applied.</p>
<ul>
  <li><b>Units:</b> RPM/V.</li>
  <li><b>Meaning:</b> Ideal, no-load. Real RPM under load is lower due to torque demand and losses.</li>
  <li><b>Trade-off:</b> Higher KV -> higher speed potential, typically lower torque per amp; lower KV -> lower speed, higher torque per amp for a given current.</li>
</ul>

<h3>Battery Voltage (V)</h3>
<p>Electrical potential of the pack.</p>
<ul>
  <li><b>Nominal vs. full-charge:</b> A "4S LiPo 14.8V" is nominal; full can be ~16.8V. Under load voltage sags.</li>
  <li><b>Effect:</b> Higher voltage raises potential RPM and power at the same current.</li>
</ul>

<h3>RPM (Revolutions per Minute)</h3>
<p>Rotational speed.</p>
<ul>
  <li><b>Model used here:</b> <code>RPM = KV * Voltage</code> (no-load estimate).</li>
  <li><b>Reality:</b> Under load: <code>RPM_load = RPM_no_load - k * torque</code>. Expect lower RPM in practice.</li>
</ul>

<h3>Torque</h3>
<p>Twisting force at the shaft.</p>
<ul>
  <li><b>Heuristic in UI:</b> Categorized from KV as High/Medium/Low to convey the common inverse trend (lower KV often implies higher torque per amp).</li>
  <li><b>Exact torque:</b> Depends on motor constants (Kt), current, winding, magnetics, and system load.</li>
</ul>

<h3>Current Draw (A)</h3>
<p>Electrical current the motor pulls at a given operating point.</p>
<ul>
  <li><b>Input format:</b> Pairs <code>KV:Current</code>, e.g., <code>2300:30</code>.</li>
  <li><b>Note:</b> Current depends on prop/load, throttle, and drivetrain; values provided here are user-supplied estimates or test data.</li>
</ul>

<h3>Power (W)</h3>
<p>Electrical input power estimate.</p>
<ul>
  <li><b>Formula:</b> <code>Power = Voltage * Current</code>.</li>
  <li><b>Meaning:</b> Electrical input; mechanical output is lower by efficiency (losses in copper, iron, and ESC).</li>
</ul>

<h3>ESC Recommendation (A)</h3>
<p>Suggested ESC continuous current rating.</p>
<ul>
  <li><b>Formula in app:</b> <code>ESC_Rec = round(Current * 1.20)</code> (adds ~20% buffer).</li>
  <li><b>Guidance:</b> Consider ambient temperature, airflow, duty cycle, ESC quality, burst specs, and telemetry. Increase margin for harsh conditions.</li>
</ul>

<h3>Assumptions and Limits</h3>
<ul>
  <li><b>No-load RPM model:</b> Simplified; load reduces RPM.</li>
  <li><b>Single-point current:</b> One current value per KV is used for all voltages; in reality current varies with voltage/prop/load.</li>
  <li><b>Safety margin:</b> The 20% buffer is a rule of thumb, not a guarantee. See your ESC datasheet for continuous/burst ratings and cooling needs.</li>
  <li><b>Units:</b> Voltage in volts, current in amperes, power in watts, speed in RPM.</li>
</ul>

<h3>Example</h3>
<pre style="white-space: pre-wrap; font-family: monospace;">
KV = 1200 RPM/V, Voltage = 14.8 V
RPM_no_load = 1200 * 14.8 = 17,760 RPM
If Current = 40 A: Power = 14.8 * 40 = 592 W
ESC_Rec ~ round(40 * 1.20) = 48 A -> choose the next standard size above this value.
</pre>

<h3>Best Practices</h3>
<ul>
  <li>Verify current with a wattmeter/telemetry using your actual prop/load and airflow.</li>
  <li>Leave thermal headroom for summer heat and long-duration operation.</li>
  <li>Account for LiPo voltage sag at high current and low state-of-charge.</li>
</ul>

<p style="color:#aaaaaa; font-size: 90%;">This helper explains the UI terms and the simplified math used by the calculator.</p>
"""


def calculate_motor_esc_params(
    kv_ratings: List[int],
    battery_voltages: List[float],
    current_draws: Dict[int, float],
) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for kv in kv_ratings:
        for voltage in battery_voltages:
            rpm = kv * voltage
            if kv >= 2000:
                torque = "Low"
            elif 1000 <= kv < 2000:
                torque = "Medium"
            else:
                torque = "High"

            current = current_draws.get(kv, 0.0)
            power = voltage * current
            esc_rating = round(current * 1.2)

            results.append(
                {
                    "KV": kv,
                    "Voltage (V)": voltage,
                    "RPM": rpm,
                    "Torque": torque,
                    "Power (W)": power,
                    "ESC Recommendation (A)": esc_rating,
                }
            )
    return results


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Glossary and Calculation Notes")
        self.resize(680, 560)

        layout = QVBoxLayout(self)
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setHtml(HELP_HTML)
        layout.addWidget(self.viewer)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class MotorEscCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Motor & ESC Parameter Calculator")
        self.resize(760, 480)

        self._apply_dark_theme()
        self._build_menu()
        self._build_ui()

    # ---- UI ----
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

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Inputs
        inputs_group = QGroupBox("Inputs")
        form = QFormLayout(inputs_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        inputs_group.setContentsMargins(8, 8, 8, 8)

        self.kv_edit = QLineEdit("2300,1200,900")
        self.kv_edit.setPlaceholderText("e.g. 2300,1200,900")
        self.kv_edit.setValidator(self._validator_csv_ints())
        self.kv_edit.setToolTip("KV list. Integers, comma-separated. Example: 2300,1200,900")

        self.voltage_edit = QLineEdit("14.8,11.1")
        self.voltage_edit.setPlaceholderText("e.g. 14.8,11.1")
        self.voltage_edit.setValidator(self._validator_csv_floats())
        self.voltage_edit.setToolTip("Battery voltages in volts. Numbers, comma-separated. Example: 14.8,11.1")

        self.current_edit = QLineEdit("2300:30,1200:40,900:50")
        self.current_edit.setPlaceholderText("KV:Current, e.g. 2300:30,1200:40")
        self.current_edit.setValidator(self._validator_kv_current_pairs())
        self.current_edit.setToolTip("Pairs KV:Current(A). Example: 2300:30,1200:40")

        form.addRow("KV Ratings:", self.kv_edit)
        form.addRow("Battery Voltages (V):", self.voltage_edit)
        form.addRow("Current Draws (A):", self.current_edit)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self._on_calculate)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._on_clear)
        self.sample_btn = QPushButton("Load Sample")
        self.sample_btn.clicked.connect(self._load_sample)
        self.help_btn = QPushButton("Glossary")
        self.help_btn.clicked.connect(self._open_help)

        btn_row.addWidget(self.calc_btn)
        btn_row.addWidget(self.clear_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.sample_btn)
        btn_row.addWidget(self.help_btn)

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        left_layout.addWidget(inputs_group)
        left_layout.addLayout(btn_row)

        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)

        # Right: Results
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        header = QLabel("Results")
        small_bold = QFont("Arial", 10, QFont.Weight.DemiBold)
        header.setFont(small_bold)
        right_layout.addWidget(header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["KV", "Voltage (V)", "RPM", "Torque", "Power (W)", "ESC Rec. (A)"]
        )
        self._apply_header_tooltips()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(22)
        right_layout.addWidget(self.table, stretch=1)

        splitter.addWidget(right_panel)
        splitter.setSizes([320, 440])

        root_layout.addWidget(splitter)

        tips = QLabel("KV is RPM/Volt (no-load). ESC Rec. adds a 20% current buffer.")
        tips.setObjectName("tips")
        right_layout.addWidget(tips)

    # ---- Validators ----
    def _validator_csv_ints(self):
        rx = QRegularExpression(r"^\s*\d+\s*(,\s*\d+\s*)*$")
        return QRegularExpressionValidator(rx, self)

    def _validator_csv_floats(self):
        rx = QRegularExpression(r"^\s*-?\d+(\.\d+)?\s*(,\s*-?\d+(\.\d+)?\s*)*$")
        return QRegularExpressionValidator(rx, self)

    def _validator_kv_current_pairs(self):
        rx = QRegularExpression(r"^\s*\d+\s*:\s*-?\d+(\.\d+)?\s*(,\s*\d+\s*:\s*-?\d+(\.\d+)?\s*)*$")
        return QRegularExpressionValidator(rx, self)

    # ---- Actions ----
    def _on_calculate(self):
        try:
            kv_list = self._parse_csv_ints(self.kv_edit.text(), "KV Ratings")
            volt_list = self._parse_csv_floats(self.voltage_edit.text(), "Battery Voltages")
            kv_curr = self._parse_kv_current_pairs(self.current_edit.text(), "Current Draws")

            results = calculate_motor_esc_params(kv_list, volt_list, kv_curr)
            self._populate_table(results)
            self.statusBar().showMessage(f"Calculated {len(results)} combinations.", 2500)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_clear(self):
        self.table.setRowCount(0)
        self.statusBar().clearMessage()

    def _load_sample(self):
        self.kv_edit.setText("2300,1200,900")
        self.voltage_edit.setText("14.8,11.1")
        self.current_edit.setText("2300:30,1200:40,900:50")

    def _export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "results.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            lines = [",".join(headers)]
            for r in range(self.table.rowCount()):
                row = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row.append("" if item is None else item.text())
                lines.append(",".join(row))
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.statusBar().showMessage(f"Exported to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    def _open_help(self):
        dlg = HelpDialog(self)
        dlg.exec()

    # ---- Parsing helpers ----
    def _parse_csv_ints(self, text: str, label: str) -> List[int]:
        if not text.strip():
            raise ValueError(f"{label} cannot be empty.")
        try:
            return [int(x.strip()) for x in text.split(",") if x.strip()]
        except Exception:
            raise ValueError(f"Invalid {label}. Use comma-separated integers.")

    def _parse_csv_floats(self, text: str, label: str) -> List[float]:
        if not text.strip():
            raise ValueError(f"{label} cannot be empty.")
        try:
            return [float(x.strip()) for x in text.split(",") if x.strip()]
        except Exception:
            raise ValueError(f"Invalid {label}. Use comma-separated numbers.")

    def _parse_kv_current_pairs(self, text: str, label: str) -> Dict[int, float]:
        if not text.strip():
            raise ValueError(f"{label} cannot be empty.")
        try:
            pairs = {}
            for part in text.split(","):
                if not part.strip():
                    continue
                kv_s, cur_s = part.split(":")
                kv = int(float(kv_s.strip()))
                cur = float(cur_s.strip())
                pairs[kv] = cur
            if not pairs:
                raise ValueError
            return pairs
        except Exception:
            raise ValueError(
                f"Invalid {label}. Use 'KV:Current' pairs separated by commas (e.g. 2300:30,1200:40)."
            )

    # ---- Table ----
    def _populate_table(self, results: List[Dict[str, Any]]):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.table.setRowCount(len(results))

        for row, res in enumerate(results):
            self._set_item(row, 0, f"{res['KV']}")
            self._set_item(row, 1, f"{res['Voltage (V)']:.2f}")
            self._set_item(row, 2, f"{res['RPM']:.2f}")
            self._set_item(row, 3, f"{res['Torque']}")
            self._set_item(row, 4, f"{res['Power (W)']:.2f}")
            self._set_item(row, 5, f"{res['ESC Recommendation (A)']}")

        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        self.table.resizeRowsToContents()

    def _set_item(self, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        if col in (0, 1, 2, 4, 5):
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.table.setItem(row, col, item)

    def _apply_header_tooltips(self):
        tooltips = [
            "KV: RPM per Volt (no-load speed constant).",
            "Voltage (V): Battery voltage used for the estimate.",
            "RPM: Estimated no-load speed = KV * Voltage.",
            "Torque: Heuristic category from KV (inverse trend).",
            "Power (W): Electrical input power = V * I.",
            "ESC Rec. (A): Suggested ESC rating with 20% margin.",
        ]
        for i in range(self.table.columnCount()):
            item = QTableWidgetItem(self.table.horizontalHeaderItem(i).text())
            item.setToolTip(tooltips[i])
            self.table.setHorizontalHeaderItem(i, item)

    # ---- Theme ----
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
        palette.setColor(QPalette.BrightText, QColor("#ff6666"))
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


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Motor & ESC Parameter Calculator")
    window = MotorEscCalculator()
    window.show()
    sys.exit(app.exec())
