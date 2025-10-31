import sys
from typing import List, Tuple

import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

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
    QCheckBox,
)


# ----------------------------
# Domain logic
# ----------------------------

def calculate_flight_time(capacity_mAh: float, avg_current_A: float, use_80_percent: bool = True) -> float:
    """Returns flight time in minutes."""
    capacity_Ah = capacity_mAh / 1000.0
    if use_80_percent:
        capacity_Ah *= 0.8
    return (capacity_Ah / max(avg_current_A, 1e-9)) * 60.0


def series_flight_time_vs_capacity(capacities: np.ndarray, current_A: float, use_80_percent: bool = True) -> np.ndarray:
    return np.array([calculate_flight_time(c, current_A, use_80_percent) for c in capacities])


def series_flight_time_vs_current(currents: np.ndarray, capacity_mAh: float, use_80_percent: bool = True) -> np.ndarray:
    return np.array([calculate_flight_time(capacity_mAh, i, use_80_percent) for i in currents])


# ----------------------------
# Help content
# ----------------------------

HELP_HTML = """
<h2 style="margin:0;">Flight Time Estimator (80% Rule)</h2>
<hr/>
<h3>Concept</h3>
<ul>
  <li><b>Capacity (mAh)</b> to <b>Ah</b>: Ah = mAh / 1000.</li>
  <li><b>80% rule</b> [battery care]: Effective_Ah = Ah * 0.8 when enabled.</li>
  <li><b>Average current (A)</b>: Mean draw during flight.</li>
  <li><b>Flight time (min)</b>: (Effective_Ah / Current_A) * 60.</li>
</ul>
<h3>Charts</h3>
<ul>
  <li><b>Flight time vs. Capacity</b>: Fix current, sweep capacity. Shows benefit of larger packs with 80% cap applied.</li>
  <li><b>Flight time vs. Current</b>: Fix capacity, sweep current. Shows the penalty of higher draw.</li>
</ul>
<h3>Notes</h3>
<ul>
  <li>Average current is scenario-dependent (prop, throttle profile, airframe).</li>
  <li>Headroom: weather, aging, voltage sag, and reserve for go-around are not modeled.</li>
  <li>This tool computes a first-order estimate, not a guarantee.</li>
</ul>
<p style="color:#aaaaaa; font-size:90%;">Use telemetry to validate. Increase margin for cold temps and high loads.</p>
"""


# ----------------------------
# Validators
# ----------------------------

def _val_float_pos() -> QRegularExpressionValidator:
    # Positive float (zero not allowed except where explicitly allowed in code)
    return QRegularExpressionValidator(QRegularExpression(r"^\s*(\d+(\.\d+)?)\s*$"))

def _val_int_pos() -> QRegularExpressionValidator:
    return QRegularExpressionValidator(QRegularExpression(r"^\s*\d+\s*$"))


# ----------------------------
# Help dialog
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


# ----------------------------
# Matplotlib canvas (dark)
# ----------------------------

class MplCanvas(FigureCanvas):
    def __init__(self):
        fig = Figure(figsize=(5, 4), dpi=100, facecolor="#121212")
        self.ax = fig.add_subplot(111)
        # Dark theme for axes
        self.ax.set_facecolor("#161616")
        self.ax.grid(True, alpha=0.25)
        for spine in self.ax.spines.values():
            spine.set_color("#aaaaaa")
        self.ax.tick_params(colors="#dddddd")
        self.ax.title.set_color("#dddddd")
        self.ax.xaxis.label.set_color("#dddddd")
        self.ax.yaxis.label.set_color("#dddddd")
        super().__init__(fig)


# ----------------------------
# Main window
# ----------------------------

class FlightTimeEstimator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flight Time Estimator")
        self.resize(980, 560)

        self._apply_dark_theme()
        self._build_menu()
        self._build_ui()

    # Menu
    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")
        export_action = QAction("Export Table to CSV...", self)
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
    
    def _open_help(self):
        HelpDialog(self).exec()
    
    # UI
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: inputs and actions
        inputs_group = QGroupBox("Inputs")
        form = QFormLayout(inputs_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setHorizontalSpacing(8)
        form.setVerticalSpacing(6)
        inputs_group.setContentsMargins(8, 8, 8, 8)

        self.capacity_mAh = QLineEdit()
        self.capacity_mAh.setPlaceholderText("e.g. 1500")
        self.capacity_mAh.setValidator(_val_float_pos())
        self.capacity_mAh.setToolTip("Battery capacity in mAh.")

        self.avg_current_A = QLineEdit()
        self.avg_current_A.setPlaceholderText("e.g. 18")
        self.avg_current_A.setValidator(_val_float_pos())
        self.avg_current_A.setToolTip("Average current draw in A.")

        self.use_80 = QCheckBox("Apply 80% rule")
        self.use_80.setChecked(True)
        self.use_80.setToolTip("Use only 80% of the nominal capacity for the estimate.")

        # Plot param groups
        self.cap_min = QLineEdit()
        self.cap_min.setPlaceholderText("500")
        self.cap_min.setValidator(_val_int_pos())
        self.cap_max = QLineEdit()
        self.cap_max.setPlaceholderText("4500")
        self.cap_max.setValidator(_val_int_pos())
        self.cap_step = QLineEdit()
        self.cap_step.setPlaceholderText("500")
        self.cap_step.setValidator(_val_int_pos())

        self.cur_min = QLineEdit()
        self.cur_min.setPlaceholderText("5")
        self.cur_min.setValidator(_val_int_pos())
        self.cur_max = QLineEdit()
        self.cur_max.setPlaceholderText("30")
        self.cur_max.setValidator(_val_int_pos())
        self.cur_step = QLineEdit()
        self.cur_step.setPlaceholderText("5")
        self.cur_step.setValidator(_val_int_pos())

        form.addRow("Capacity (mAh):", self.capacity_mAh)
        form.addRow("Avg current (A):", self.avg_current_A)
        form.addRow("", self.use_80)
        form.addRow(QLabel("----- Chart Ranges -----"))
        form.addRow("Cap min/ max/ step:", self._row3(self.cap_min, self.cap_max, self.cap_step))
        form.addRow("I min/ max/ step (A):", self._row3(self.cur_min, self.cur_max, self.cur_step))

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.calc_btn = QPushButton("Calculate")
        self.calc_btn.clicked.connect(self._on_calculate)
        self.plot_cap_btn = QPushButton("Plot: Time vs Capacity")
        self.plot_cap_btn.clicked.connect(self._on_plot_vs_capacity)
        self.plot_cur_btn = QPushButton("Plot: Time vs Current")
        self.plot_cur_btn.clicked.connect(self._on_plot_vs_current)
        self.save_fig_btn = QPushButton("Save Figure...")
        self.save_fig_btn.clicked.connect(self._on_save_figure)
        self.help_btn = QPushButton("Glossary")
        self.help_btn.clicked.connect(self._open_help)

        btn_row.addWidget(self.calc_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.plot_cap_btn)
        btn_row.addWidget(self.plot_cur_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.save_fig_btn)
        btn_row.addWidget(self.help_btn)

        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(6)
        left_box.addWidget(inputs_group)
        left_box.addLayout(btn_row)
        leftw = QWidget()
        leftw.setLayout(left_box)
        splitter.addWidget(leftw)

        # Right panel: results table + chart
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
        right.addWidget(self.table)

        # Chart canvas
        self.canvas = MplCanvas()
        right.addWidget(self.canvas, stretch=1)

        tips = QLabel("80% rule reduces usable capacity. Charts update from the controls on the left.")
        tips.setObjectName("tips")
        right.addWidget(tips)

        splitter.addWidget(rightw)
        splitter.setSizes([360, 620])

        root.addWidget(splitter)

        # Defaults
        self.capacity_mAh.setText("1500")
        self.avg_current_A.setText("18")
        self.cap_min.setText("500")
        self.cap_max.setText("4500")
        self.cap_step.setText("500")
        self.cur_min.setText("5")
        self.cur_max.setText("30")
        self.cur_step.setText("5")

    # Small helper widget with 3 line edits inline
    def _row3(self, a: QLineEdit, b: QLineEdit, c: QLineEdit) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        h.addWidget(a)
        h.addWidget(b)
        h.addWidget(c)
        return w

    # Actions
    def _on_calculate(self):
        try:
            cap = self._f(self.capacity_mAh, "Capacity (mAh)")
            cur = self._f(self.avg_current_A, "Avg current (A)")
            if cur <= 0:
                raise ValueError("Avg current (A) must be > 0.")
            use80 = self.use_80.isChecked()
            ft_min = calculate_flight_time(cap, cur, use80)
            rows = [
                ("Capacity (mAh)", f"{cap:.0f}"),
                ("Avg current (A)", f"{cur:.2f}"),
                ("80% rule", "On" if use80 else "Off"),
                ("Estimated flight time (min)", f"{ft_min:.2f}"),
            ]
            self._populate_table(rows)
            self.statusBar().showMessage("Calculated.", 2500)
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_plot_vs_capacity(self):
        try:
            i_fixed = self._f(self.avg_current_A, "Avg current (A)")
            if i_fixed <= 0:
                raise ValueError("Avg current (A) must be > 0.")
            cap_min = int(self._f(self.cap_min, "Cap min"))
            cap_max = int(self._f(self.cap_max, "Cap max"))
            cap_step = int(self._f(self.cap_step, "Cap step"))
            if not (cap_min > 0 and cap_max > cap_min and cap_step > 0):
                raise ValueError("Capacity range must be positive, max > min, step > 0.")
            caps = np.arange(cap_min, cap_max + 1, cap_step)
            times = series_flight_time_vs_capacity(caps, i_fixed, self.use_80.isChecked())
            self._plot_xy(caps, times, "Battery Capacity (mAh)", "Flight Time (min)",
                          f"Flight Time vs Capacity @ {i_fixed:.2f} A")
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_plot_vs_current(self):
        try:
            cap_fixed = self._f(self.capacity_mAh, "Capacity (mAh)")
            i_min = int(self._f(self.cur_min, "I min"))
            i_max = int(self._f(self.cur_max, "I max"))
            i_step = int(self._f(self.cur_step, "I step"))
            if not (i_min > 0 and i_max > i_min and i_step > 0):
                raise ValueError("Current range must be positive, max > min, step > 0.")
            currents = np.arange(i_min, i_max + 1, i_step)
            times = series_flight_time_vs_current(currents, cap_fixed, self.use_80.isChecked())
            self._plot_xy(currents, times, "Average Current (A)", "Flight Time (min)",
                          f"Flight Time vs Current @ {cap_fixed:.0f} mAh")
        except ValueError as e:
            QMessageBox.critical(self, "Error", str(e))

    def _on_save_figure(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Figure", "flight_time.png", "PNG Files (*.png);;SVG Files (*.svg)")
        if not path:
            return
        try:
            self.canvas.figure.savefig(path, dpi=150, facecolor=self.canvas.figure.get_facecolor())
            self.statusBar().showMessage(f"Saved figure to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save figure: {e}")

    # Plot helper
    def _plot_xy(self, x: np.ndarray, y: np.ndarray, xlabel: str, ylabel: str, title: str):
        ax = self.canvas.ax
        ax.clear()
        # Re-apply dark axis styling after clear
        ax.set_facecolor("#161616")
        for spine in ax.spines.values():
            spine.set_color("#aaaaaa")
        ax.tick_params(colors="#dddddd")
        ax.title.set_color("#dddddd")
        ax.xaxis.label.set_color("#dddddd")
        ax.yaxis.label.set_color("#dddddd")

        ax.plot(x, y, marker="o")
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(True, alpha=0.25)
        self.canvas.draw()

        # Also reflect data in a table for exportability
        self._populate_table([("Series points", f"{len(x)}")])
        self._fill_series_into_table(x, y, xlabel, ylabel)

    # Table helpers
    def _populate_table(self, rows: List[Tuple[str, str]]):
        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))
        for r, (k, v) in enumerate(rows):
            k_item = QTableWidgetItem(k)
            v_item = QTableWidgetItem(v)
            v_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(r, 0, k_item)
            self.table.setItem(r, 1, v_item)
        self.table.resizeRowsToContents()

    def _fill_series_into_table(self, x: np.ndarray, y: np.ndarray, xlabel: str, ylabel: str):
        # Append series rows after current content
        start = self.table.rowCount()
        self.table.setRowCount(start + len(x) + 1)
        sep = QTableWidgetItem("--- Series Data ---")
        self.table.setItem(start, 0, sep)
        for i, (xi, yi) in enumerate(zip(x, y), start=start + 1):
            self.table.setItem(i, 0, QTableWidgetItem(f"{xlabel}: {xi:g}"))
            val = QTableWidgetItem(f"{yi:.3f}")
            val.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.setItem(i, 1, val)
        self.table.resizeRowsToContents()

    # Export
    def _export_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.information(self, "Export", "No results to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "flight_time_results.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            lines = ["Metric,Value"]
            for r in range(self.table.rowCount()):
                k = self.table.item(r, 0).text() if self.table.item(r, 0) else ""
                v = self.table.item(r, 1).text() if self.table.item(r, 1) else ""
                k = '"' + k.replace('"', '""') + '"'
                v = '"' + v.replace('"', '""') + '"'
                lines.append(f"{k},{v}")
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            self.statusBar().showMessage(f"Exported to {path}", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")

    # Parse helpers
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
            QCheckBox { spacing: 6px; }
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
    app.setApplicationName("Flight Time Estimator")
    win = FlightTimeEstimator()
    win.show()
    sys.exit(app.exec())
