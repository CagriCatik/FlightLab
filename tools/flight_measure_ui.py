import sys
import time
import random
from typing import List, Tuple

from PySide6.QtCore import Qt, QRegularExpression, QTimer
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
    QCheckBox,
)


HELP_HTML = """
<h2 style="margin:0;">Battery Monitor Simulator (Coulomb Counting)</h2>
<hr/>
<h3>Concepts</h3>
<ul>
  <li><b>Capacity (mAh)</b>: Battery charge capacity. 1500 mAh = 1.5 Ah.</li>
  <li><b>80% rule</b>: Use only 80% of nominal capacity to preserve battery health and avoid deep discharge.
    <ul><li>Effective capacity = capacity * 0.8 when enabled.</li></ul>
  </li>
  <li><b>Sampling interval (s)</b>: Period between telemetry updates.</li>
  <li><b>Current (A)</b>: Instantaneous draw. In simulation, a random value in [min, max].</li>
  <li><b>Coulomb counting</b>: Integrates current over time to estimate consumption.
    <ul>
      <li>Elapsed time (h) = dt_seconds / 3600</li>
      <li>Used Ah = I(A) * elapsed(h)</li>
      <li>Used mAh = Used Ah * 1000</li>
      <li>Consumed mAh = sum(Used mAh)</li>
      <li>Remaining mAh = effective_capacity_mAh - consumed_mAh</li>
    </ul>
  </li>
  <li><b>Estimated flight time (min)</b>: Remaining Ah / current * 60.
    <ul><li>If current <= 0.1 A, estimate is set to a large sentinel value.</li></ul>
  </li>
</ul>
<h3>Termination</h3>
<ul>
  <li>Stops when simulation duration is reached or effective capacity is depleted.</li>
</ul>
<h3>Notes</h3>
<ul>
  <li>Random current is a stand-in for real telemetry.</li>
  <li>Coulomb counting accumulates error without calibration; real systems often fuse voltage, current, and state models.</li>
</ul>
<p style="color:#aaaaaa; font-size:90%;">This tool is a simplified simulator for educational and sizing purposes.</p>
"""


def _val_float_nonneg() -> QRegularExpressionValidator:
    return QRegularExpressionValidator(QRegularExpression(r"^\s*(\d+(\.\d+)?)\s*$"))


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


class BatterySimWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Battery Monitor Simulator")
        self.resize(820, 540)

        self._apply_dark_theme()
        self._build_menu()
        self._build_ui()

        # Simulation state
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_tick)
        self.running = False
        self.start_time = 0.0
        self.last_time = 0.0
        self.total_elapsed_s = 0.0
        self.consumed_mAh = 0.0
        self.effective_capacity_mAh = 0.0
        self.records: List[Tuple[float, float, float, float, float]] = []  # (t, I, consumed, remaining, eta_min)

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

    # UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: controls
        inputs_group = QGroupBox("Configuration")
        form = QFormLayout(inputs_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        inputs_group.setContentsMargins(8, 8, 8, 8)

        self.capacity_mAh = QLineEdit()
        self.capacity_mAh.setPlaceholderText("e.g. 1500")
        self.capacity_mAh.setValidator(_val_float_nonneg())
        self.capacity_mAh.setToolTip("Battery capacity (mAh).")

        self.use_80 = QCheckBox("Use 80% rule")
        self.use_80.setChecked(True)
        self.use_80.setToolTip("Use only 80% of capacity for safety.")

        self.sampling_s = QLineEdit()
        self.sampling_s.setPlaceholderText("e.g. 0.1")
        self.sampling_s.setValidator(_val_float_nonneg())
        self.sampling_s.setToolTip("Sampling interval in seconds.")

        self.duration_s = QLineEdit()
        self.duration_s.setPlaceholderText("e.g. 120")
        self.duration_s.setValidator(_val_float_nonneg())
        self.duration_s.setToolTip("Total simulation time in seconds.")

        self.i_min_a = QLineEdit()
        self.i_min_a.setPlaceholderText("e.g. 2.0")
        self.i_min_a.setValidator(_val_float_nonneg())
        self.i_min_a.setToolTip("Minimum current draw (A).")

        self.i_max_a = QLineEdit()
        self.i_max_a.setPlaceholderText("e.g. 10.0")
        self.i_max_a.setValidator(_val_float_nonneg())
        self.i_max_a.setToolTip("Maximum current draw (A).")

        form.addRow("Capacity (mAh):", self.capacity_mAh)
        form.addRow("", self.use_80)
        form.addRow("Sampling (s):", self.sampling_s)
        form.addRow("Duration (s):", self.duration_s)
        form.addRow("Current min (A):", self.i_min_a)
        form.addRow("Current max (A):", self.i_max_a)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self.start_btn = QPushButton("Start")
        self.start_btn.clicked.connect(self._on_start)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self._on_reset)

        self.help_btn = QPushButton("Glossary")
        self.help_btn.clicked.connect(self._open_help)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.pause_btn)
        btn_row.addWidget(self.reset_btn)
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

        # Right: telemetry
        rightw = QWidget()
        right = QVBoxLayout(rightw)
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(6)

        header = QLabel("Telemetry")
        small_bold = QFont("Arial", 10, QFont.Weight.DemiBold)
        header.setFont(small_bold)
        right.addWidget(header)

        # Status row
        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self.status_time = QLabel("t: 0.0 s")
        self.status_current = QLabel("I: 0.00 A")
        self.status_consumed = QLabel("Used: 0.0 mAh")
        self.status_remaining = QLabel("Rem: 0.0 mAh")
        self.status_eta = QLabel("ETA: -- min")
        for w in (self.status_time, self.status_current, self.status_consumed, self.status_remaining, self.status_eta):
            status_row.addWidget(w)
        status_row.addStretch(1)
        right.addLayout(status_row)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Time (s)", "Current (A)", "Consumed (mAh)", "Remaining (mAh)", "Est. Flight (min)"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)
        right.addWidget(self.table, stretch=1)

        tips = QLabel("Coulomb counting with 80% capacity option; stops on duration or depletion.")
        tips.setObjectName("tips")
        right.addWidget(tips)

        splitter.addWidget(rightw)
        splitter.setSizes([330, 490])

        root.addWidget(splitter)

        # Defaults (compact, no sample loader)
        self.capacity_mAh.setText("1500")
        self.sampling_s.setText("0.1")
        self.duration_s.setText("120")
        self.i_min_a.setText("2.0")
        self.i_max_a.setText("10.0")

    # Actions
    def _on_start(self):
        try:
            cap = self._f(self.capacity_mAh, "Capacity (mAh)")
            samp = self._f(self.sampling_s, "Sampling (s)")
            dur = self._f(self.duration_s, "Duration (s)")
            i_min = self._f(self.i_min_a, "Current min (A)")
            i_max = self._f(self.i_max_a, "Current max (A)")
            if i_max < i_min:
                raise ValueError("Current max (A) must be >= Current min (A).")
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))
            return

        self.effective_capacity_mAh = cap * (0.8 if self.use_80.isChecked() else 1.0)
        self.sampling_interval_s = samp
        self.sim_duration_s = dur
        self.i_min = i_min
        self.i_max = i_max

        now = time.time()
        if not self.running:
            # fresh start or resume
            if self.start_time == 0.0:
                # first start
                self.start_time = now
                self.last_time = now
                self.total_elapsed_s = 0.0
                self.consumed_mAh = 0.0
                self.records.clear()
                self.table.setRowCount(0)
            else:
                # resume from pause
                self.last_time = now

        self._set_inputs_enabled(False)
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.running = True
        self.timer.start(int(self.sampling_interval_s * 1000))

    def _on_pause(self):
        if not self.running:
            return
        self.running = False
        self.timer.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self._set_inputs_enabled(True)

    def _on_reset(self):
        self.running = False
        self.timer.stop()
        self.start_time = 0.0
        self.last_time = 0.0
        self.total_elapsed_s = 0.0
        self.consumed_mAh = 0.0
        self.records.clear()
        self.table.setRowCount(0)
        self.status_time.setText("t: 0.0 s")
        self.status_current.setText("I: 0.00 A")
        self.status_consumed.setText("Used: 0.0 mAh")
        self.status_remaining.setText("Rem: 0.0 mAh")
        self.status_eta.setText("ETA: -- min")
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self._set_inputs_enabled(True)
        self.statusBar().clearMessage()

    def _on_tick(self):
        now = time.time()
        elapsed_s = now - self.last_time
        self.total_elapsed_s = now - self.start_time

        # Stop on duration
        if self.total_elapsed_s >= self.sim_duration_s:
            self.statusBar().showMessage("Reached simulation duration.")
            self._on_pause()
            return

        if elapsed_s + 1e-9 < self.sampling_interval_s:
            return  # wait until interval boundary

        # 1) random current
        current_A = random.uniform(self.i_min, self.i_max)

        # 2) elapsed hours
        elapsed_h = elapsed_s / 3600.0

        # 3) mAh used in this interval
        used_mAh = current_A * elapsed_h * 1000.0

        # 4) update totals
        self.consumed_mAh += used_mAh
        remaining_mAh = max(self.effective_capacity_mAh - self.consumed_mAh, 0.0)

        # 5) ETA
        if current_A > 0.1:
            flight_time_left_h = (remaining_mAh / 1000.0) / current_A
            flight_time_left_min = flight_time_left_h * 60.0
        else:
            flight_time_left_min = 9999.0

        # 6) append row
        self._append_row(self.total_elapsed_s, current_A, self.consumed_mAh, remaining_mAh, flight_time_left_min)

        # 7) status labels
        self.status_time.setText(f"t: {self.total_elapsed_s:0.1f} s")
        self.status_current.setText(f"I: {current_A:0.2f} A")
        self.status_consumed.setText(f"Used: {self.consumed_mAh:0.1f} mAh")
        self.status_remaining.setText(f"Rem: {remaining_mAh:0.1f} mAh")
        self.status_eta.setText(f"ETA: {flight_time_left_min:0.1f} min" if flight_time_left_min < 9999 else "ETA: -- min")

        # 8) depletion stop
        if remaining_mAh <= 0.0:
            self.statusBar().showMessage("Battery effectively depleted.")
            self._on_pause()
            return

        self.last_time = now

    # Helpers
    def _append_row(self, t: float, i: float, used: float, rem: float, eta: float):
        r = self.table.rowCount()
        self.table.insertRow(r)
        vals = [f"{t:0.1f}", f"{i:0.2f}", f"{used:0.1f}", f"{rem:0.1f}", ("--" if eta >= 9999 else f"{eta:0.1f}")]
        for c, v in enumerate(vals):
            item = QTableWidgetItem(v)
            if c >= 1:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, c, item)
        self.table.scrollToBottom()

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

    def _set_inputs_enabled(self, enabled: bool):
        for w in (self.capacity_mAh, self.sampling_s, self.duration_s, self.i_min_a, self.i_max_a, self.use_80):
            w.setEnabled(enabled)

    # Export
    def _export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "battery_sim_results.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            lines = [",".join(headers)]
            for r in range(self.table.rowCount()):
                row = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    txt = "" if item is None else item.text()
                    row.append('"' + txt.replace('"', '""') + '"')
                lines.append(",".join(row))
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
            QCheckBox {
                spacing: 6px;
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
    app.setApplicationName("Battery Monitor Simulator")
    win = BatterySimWindow()
    win.show()
    sys.exit(app.exec())
