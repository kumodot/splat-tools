"""SplatForge - turn a video into a Gaussian Splat PLY, on Windows.

Marcelo Souza / Kumodot.art - 2026 // @Msouza3d
Support: https://ko-fi.com/msouza3d

    video  ->  sharp frames  ->  camera poses  ->  splat PLY  ->  Quest-sized PLY
               (this app)        Spirula Studio    Spirula        splat_prep

Run with run_SplatForge.bat, or:  python SplatForge_v0.1.0.py
Requires: PyQt6, opencv-python, numpy.  Spirula Studio is downloaded separately.
"""

from __future__ import annotations

import os
import sys
import traceback
from pathlib import Path

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QUrl, QSize
from PyQt6.QtGui import QDesktopServices, QFont, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import (
    QListWidget, QListWidgetItem, QScrollArea, QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QPlainTextEdit, QFileDialog, QProgressBar, QFrame, QDialog,
    QMessageBox, QSizePolicy,
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import splatforge_core as core   # noqa: E402

APP_NAME = "SplatForge"
APP_VERSION = "0.3.0"
CREDIT = "Marcelo Souza / Kumodot.art - 2026 // @Msouza3d"
KOFI = "https://ko-fi.com/msouza3d"
APP_DIR = Path(__file__).resolve().parent
DEFAULT_WORK = APP_DIR / "work"
DEFAULT_OUT = APP_DIR / "output"

SPIRULA_URL = "https://github.com/harry7557558/spirula-studio/releases"
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".insv", ".mts", ".m2ts", ".webm"}

# ---------------------------------------------------------------------------
# Design tokens
# ---------------------------------------------------------------------------
FONT_HEADING = "Hanken Grotesk"
FONT_BODY = "Inter"

SPACING_XS, SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL = 4, 8, 16, 24, 32
RADIUS_SM, RADIUS_DEFAULT, RADIUS_LG, RADIUS_FULL = 2, 4, 8, 9999

DARK_BACKGROUND = "#0B121F"
DARK_SURFACE = "#161C27"
DARK_SURFACE_CONTAINER = "#1E2738"
DARK_SURFACE_HIGH = "#252D3D"
DARK_BORDER = "#252D3D"
DARK_ON_SURFACE = "#edf0ff"
DARK_ON_SURFACE_VARIANT = "#9ca3b8"
DARK_OUTLINE = "#3d4560"
DARK_PRIMARY = "#b2c5ff"
DARK_PRIMARY_CONTAINER = "#0040a2"

COLOR_BACKGROUND = "#faf9ff"
COLOR_SURFACE_LOWEST = "#ffffff"
COLOR_SURFACE_LOW = "#f1f3ff"
COLOR_SURFACE_HIGH = "#e1e8ff"
COLOR_ON_SURFACE = "#051a3e"
COLOR_ON_SURFACE_VARIANT = "#434654"
COLOR_OUTLINE = "#737685"
COLOR_OUTLINE_VARIANT = "#c3c6d6"
COLOR_PRIMARY = "#003d9b"
COLOR_ON_PRIMARY = "#ffffff"
COLOR_PRIMARY_CONTAINER = "#0052cc"

COLOR_SUCCESS = "#1e7d4a"
COLOR_WARNING = "#b45309"
COLOR_DANGER = "#ba1a1a"

TYPO_HEADLINE_LG = 24
TYPO_HEADLINE_MD = 20
TYPO_HEADLINE_SM = 16
TYPO_BODY_MD = 14
TYPO_BODY_SM = 13
TYPO_LABEL_MD = 12
TYPO_LABEL_SM = 11


def _qss(bg, surface, surface_alt, border, on_surface, on_variant, outline,
         primary, on_primary, primary_hover):
    return f"""
* {{
    font-family: '{FONT_BODY}';
    font-size: {TYPO_BODY_MD}px;
    color: {on_surface};
    outline: none;
}}
QMainWindow, QDialog {{ background-color: {bg}; }}
QWidget#Card {{
    background-color: {surface};
    border: 1px solid {border};
    border-radius: {RADIUS_LG}px;
}}
QLabel#H1 {{ font-family: '{FONT_HEADING}'; font-size: {TYPO_HEADLINE_LG}px; font-weight: 600; }}
QLabel#H2 {{ font-family: '{FONT_HEADING}'; font-size: {TYPO_HEADLINE_SM}px; font-weight: 600; }}
QLabel#SectionLabel {{
    font-size: {TYPO_LABEL_MD}px; font-weight: 600; color: {on_variant};
    letter-spacing: 1px;
}}
QLabel#Muted {{ color: {on_variant}; font-size: {TYPO_BODY_SM}px; }}
QLabel#Version {{ color: {primary}; font-size: {TYPO_LABEL_MD}px; font-weight: 600; }}
QLabel#Ok {{ color: {COLOR_SUCCESS}; font-size: {TYPO_BODY_SM}px; }}
QLabel#Warn {{ color: {COLOR_WARNING}; font-size: {TYPO_BODY_SM}px; }}
QLabel#Bad {{ color: {COLOR_DANGER}; font-size: {TYPO_BODY_SM}px; }}

QPushButton {{
    font-size: {TYPO_LABEL_MD}px; font-weight: 600;
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: {RADIUS_DEFAULT}px;
    padding: {SPACING_SM}px {SPACING_MD}px;
}}
QPushButton:hover {{ border-color: {primary}; }}
QPushButton:pressed {{ background-color: {border}; }}
QPushButton:disabled {{ color: {on_variant}; border-color: {border}; }}
QPushButton#Primary {{
    background-color: {primary}; color: {on_primary}; border-color: {primary};
    padding: {SPACING_SM + 2}px {SPACING_LG}px;
}}
QPushButton#Primary:hover {{ background-color: {primary_hover}; border-color: {primary_hover}; }}
QPushButton#Primary:disabled {{ background-color: {border}; color: {on_variant}; border-color: {border}; }}
QPushButton#Link {{
    background: transparent; border: none; color: {primary};
    text-decoration: underline; padding: {SPACING_XS}px;
}}

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {surface_alt};
    border: 1px solid {border};
    border-radius: {RADIUS_SM}px;
    padding: {SPACING_SM - 2}px {SPACING_SM}px;
    min-height: 20px;
    selection-background-color: {primary};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 2px solid {primary};
    padding: {SPACING_SM - 3}px {SPACING_SM - 1}px;
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {on_variant};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background-color: {surface};
    border: 1px solid {border};
    selection-background-color: {primary};
    selection-color: {on_primary};
    padding: {SPACING_XS}px;
}}
QCheckBox {{ spacing: {SPACING_SM}px; font-size: {TYPO_BODY_SM}px; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {outline}; border-radius: {RADIUS_SM}px;
    background-color: {surface_alt};
}}
QCheckBox::indicator:checked {{ background-color: {primary}; border-color: {primary}; }}
QCheckBox::indicator:hover {{ border-color: {primary}; }}

QLabel#DropZone {{
    border: 2px dashed {border}; border-radius: {RADIUS_LG}px;
    color: {on_variant}; font-size: {TYPO_BODY_SM}px;
    background-color: {surface_alt};
}}
QLabel#DropZone[hot="true"] {{
    border-color: {primary}; color: {primary};
}}
QListWidget {{
    background-color: {surface_alt}; border: 1px solid {border};
    border-radius: {RADIUS_DEFAULT}px; font-size: {TYPO_BODY_SM}px;
}}
QListWidget::item {{ padding: {SPACING_XS}px {SPACING_SM}px; }}
QListWidget::item:selected {{ background-color: {primary}; color: {on_primary}; }}
QPlainTextEdit {{
    background-color: {bg};
    border: 1px solid {border};
    border-radius: {RADIUS_DEFAULT}px;
    font-family: 'Consolas', 'ui-monospace', monospace;
    font-size: {TYPO_BODY_SM - 1}px;
    color: {on_variant};
    padding: {SPACING_SM}px;
}}
QProgressBar {{
    background-color: {surface_alt};
    border: none; border-radius: {RADIUS_FULL}px;
    height: 6px; text-align: center;
}}
QProgressBar::chunk {{ background-color: {primary}; border-radius: {RADIUS_FULL}px; }}
QFrame#Divider {{ background-color: {border}; max-height: 1px; border: none; }}

QScrollBar:vertical {{ width: 6px; background: transparent; }}
QScrollBar::handle:vertical {{ background: {outline}; border-radius: 3px; min-height: 24px; }}
QScrollBar::handle:vertical:hover {{ background: {primary}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
"""


DARK_QSS = _qss(DARK_BACKGROUND, DARK_SURFACE, DARK_SURFACE_CONTAINER, DARK_BORDER,
                DARK_ON_SURFACE, DARK_ON_SURFACE_VARIANT, DARK_OUTLINE,
                DARK_PRIMARY, "#001a4d", "#c9d6ff")
LIGHT_QSS = _qss(COLOR_BACKGROUND, COLOR_SURFACE_LOWEST, COLOR_SURFACE_LOW,
                 COLOR_OUTLINE_VARIANT, COLOR_ON_SURFACE, COLOR_ON_SURFACE_VARIANT,
                 COLOR_OUTLINE, COLOR_PRIMARY, COLOR_ON_PRIMARY, COLOR_PRIMARY_CONTAINER)


# ---------------------------------------------------------------------------
# Small widgets
# ---------------------------------------------------------------------------
def divider() -> QFrame:
    f = QFrame()
    f.setObjectName("Divider")
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    return f


def section_label(text: str) -> QLabel:
    lb = QLabel(text.upper())
    lb.setObjectName("SectionLabel")
    return lb


class Card(QWidget):
    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self.v.setSpacing(SPACING_SM)
        if title:
            self.v.addWidget(section_label(title))


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------
class JobThread(QThread):
    log_line = pyqtSignal(str)
    step_changed = pyqtSignal(str)
    progressed = pyqtSignal(int, int)
    finished_job = pyqtSignal(object)

    def __init__(self, job: core.JobSettings):
        super().__init__()
        self.job = job
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            res = core.run_job(
                self.job,
                log=self.log_line.emit,
                progress=lambda d, t: self.progressed.emit(d, t),
                step=self.step_changed.emit,
                cancel=lambda: self._cancel,
            )
        except core.Cancelled:
            res = core.JobResult(failed_step="cancelled", message="Cancelled.")
        except Exception as e:
            self.log_line.emit(traceback.format_exc())
            res = core.JobResult(failed_step="error", message=str(e))
        self.finished_job.emit(res)


class HelpThread(QThread):
    """Runs `spirula --help` so the real options land in the log."""
    log_line = pyqtSignal(str)
    done = pyqtSignal()

    def __init__(self, exe: str, sub: str):
        super().__init__()
        self.exe, self.sub = exe, sub

    def run(self):
        try:
            core.spirula_help(self.exe, self.sub, log=self.log_line.emit)
        except Exception as e:
            self.log_line.emit(f"could not run it: {e}")
        self.done.emit()


# ---------------------------------------------------------------------------
# About
# ---------------------------------------------------------------------------
class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        v.setSpacing(SPACING_MD)

        title = QLabel(f"{APP_NAME}")
        title.setObjectName("H1")
        row = QHBoxLayout()
        row.addWidget(title)
        ver = QLabel(f"v{APP_VERSION}")
        ver.setObjectName("Version")
        ver.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(ver)
        row.addStretch(1)
        v.addLayout(row)

        body = QLabel(
            "Turns a video into a Gaussian Splat PLY you can walk through in VR.\n\n"
            "Frames are chosen by sharpness so motion blur never reaches the solver. "
            "Camera poses and training are done by Spirula Studio, and the result is "
            "shrunk to headset size by splat_prep."
        )
        body.setWordWrap(True)
        v.addWidget(body)
        v.addWidget(divider())

        credit = QLabel(CREDIT)
        credit.setObjectName("Muted")
        v.addWidget(credit)

        kofi = QPushButton("Support Marcelo Souza on Ko-fi")
        kofi.setObjectName("Link")
        kofi.setCursor(Qt.CursorShape.PointingHandCursor)
        kofi.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(KOFI)))
        v.addWidget(kofi, alignment=Qt.AlignmentFlag.AlignLeft)

        third = QLabel(
            "Uses Spirula Studio (GPL-3.0) as a separate, unmodified program, "
            "OpenCV, and PyQt6."
        )
        third.setObjectName("Muted")
        third.setWordWrap(True)
        v.addWidget(third)

        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        v.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 780)
        self.setAcceptDrops(True)
        self.settings = QSettings("Kumodot", "SplatForge")
        self.info: core.VideoInfo | None = None
        self.thread: JobThread | None = None
        self.help_thread: HelpThread | None = None
        self.result: core.JobResult | None = None
        self.pending: list[str] = []
        self.batch_done: list[core.JobResult] = []
        self.batch_total = 0

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        outer.setSpacing(SPACING_MD)

        outer.addLayout(self._header())

        cols = QHBoxLayout()
        cols.setSpacing(SPACING_MD)
        left = QVBoxLayout()
        left.setSpacing(SPACING_MD)
        left.addWidget(self._card_input())
        left.addWidget(self._card_frames())
        left.addWidget(self._card_engine())
        left.addWidget(self._card_output())
        left.addStretch(1)
        lw = QWidget()
        lw.setLayout(left)
        scroll = QScrollArea()
        scroll.setWidget(lw)
        scroll.setWidgetResizable(True)
        lw.setMaximumWidth(424)
        scroll.setFixedWidth(452)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        cols.addWidget(scroll)
        cols.addWidget(self._card_run(), 1)
        outer.addLayout(cols, 1)

        self._load_settings()
        self._autodetect_spirula(quiet=True)
        self._update_estimate()

    # -- header ------------------------------------------------------------
    def _header(self):
        row = QHBoxLayout()
        t = QLabel(APP_NAME)
        t.setObjectName("H1")
        row.addWidget(t)
        v = QLabel(f"v{APP_VERSION}")
        v.setObjectName("Version")
        v.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addWidget(v)
        sub = QLabel("video to Gaussian Splat")
        sub.setObjectName("Muted")
        sub.setAlignment(Qt.AlignmentFlag.AlignBottom)
        row.addSpacing(SPACING_SM)
        row.addWidget(sub)
        row.addStretch(1)
        self.theme_btn = QPushButton("Light")
        self.theme_btn.clicked.connect(self._toggle_theme)
        row.addWidget(self.theme_btn)
        about = QPushButton("About")
        about.clicked.connect(lambda: AboutDialog(self).exec())
        row.addWidget(about)
        return row

    # -- cards -------------------------------------------------------------
    def _card_input(self):
        c = Card("1. Videos")
        self.drop_hint = QLabel("Drop videos here")
        self.drop_hint.setObjectName("DropZone")
        self.drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_hint.setMinimumHeight(52)
        c.v.addWidget(self.drop_hint)

        self.queue = QListWidget()
        self.queue.setMaximumHeight(110)
        self.queue.currentRowChanged.connect(self._queue_selected)
        c.v.addWidget(self.queue)

        r = QHBoxLayout()
        b = QPushButton("Add")
        b.clicked.connect(self._browse_video)
        r.addWidget(b)
        rm = QPushButton("Remove")
        rm.clicked.connect(self._queue_remove)
        r.addWidget(rm)
        cl = QPushButton("Clear")
        cl.clicked.connect(self._queue_clear)
        r.addWidget(cl)
        r.addStretch(1)
        c.v.addLayout(r)

        self.video_edit = QLineEdit()          # kept so the rest of the app is unchanged
        self.video_edit.setVisible(False)
        c.v.addWidget(self.video_edit)

        self.video_info = QLabel("No video loaded.")
        self.video_info.setObjectName("Muted")
        self.video_info.setWordWrap(True)
        c.v.addWidget(self.video_info)
        return c

    # -- queue -------------------------------------------------------------
    def _add_videos(self, paths):
        added = 0
        existing = {self.queue.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.queue.count())}
        for p in paths:
            p = Path(p)
            if p.suffix.lower() not in VIDEO_EXTS or str(p) in existing:
                continue
            existing.add(str(p))
            it = QListWidgetItem(p.name)
            it.setData(Qt.ItemDataRole.UserRole, str(p))
            it.setToolTip(str(p))
            self.queue.addItem(it)
            added += 1
        if added and self.queue.currentRow() < 0:
            self.queue.setCurrentRow(0)
        self._update_queue_label()
        if added:
            setattr(self, "_last_added", added)
            self.setStatusText(f"{added} video{'s' if added > 1 else ''} queued.")
        return added

    def setStatusText(self, msg):
        self.step_label.setText(msg) if hasattr(self, "step_label") else None

    def _queue_paths(self):
        return [self.queue.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.queue.count())]

    def _queue_selected(self, row):
        if row < 0:
            self.video_edit.setText("")
            self.info = None
            self.video_info.setText("No video loaded.")
            self._update_estimate()
            return
        self.video_edit.setText(self.queue.item(row).data(Qt.ItemDataRole.UserRole))
        self._probe()

    def _queue_remove(self):
        row = self.queue.currentRow()
        if row >= 0:
            self.queue.takeItem(row)
            self._update_queue_label()

    def _queue_clear(self):
        self.queue.clear()
        self._update_queue_label()

    def _update_queue_label(self):
        n = self.queue.count()
        self.drop_hint.setText("Drop videos here" if not n
                               else f"Drop more here  ({n} queued)")
        if hasattr(self, "run_btn"):
            self.run_btn.setText("Make the splat" if n <= 1 else f"Make {n} splats")

    def _card_frames(self):
        c = Card("2. Frames")
        g = QGridLayout()
        g.setHorizontalSpacing(SPACING_SM)
        g.setVerticalSpacing(SPACING_SM)

        g.addWidget(QLabel("Target frames"), 0, 0)
        self.target_spin = QSpinBox()
        self.target_spin.setRange(20, 5000)
        self.target_spin.setValue(150)
        self.target_spin.valueChanged.connect(self._target_changed)
        g.addWidget(self.target_spin, 0, 1)

        g.addWidget(QLabel("Window"), 0, 2)
        self.keep_spin = QSpinBox()
        self.keep_spin.setRange(0, 60)
        self.keep_spin.setValue(0)
        self.keep_spin.setToolTip("How many frames each written frame is the sharpest of.\n"
                                  "0 = half the spacing, which is the Spirula default.")
        self.keep_spin.valueChanged.connect(self._update_estimate)
        g.addWidget(self.keep_spin, 0, 3)

        g.addWidget(QLabel("Scale"), 1, 0)
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(0.1, 1.0)
        self.scale_spin.setSingleStep(0.05)
        self.scale_spin.setValue(1.0)
        self.scale_spin.setToolTip("Leave at 1.0. The solver wants full detail;\n"
                                   "the trainer downscales on its own.")
        g.addWidget(self.scale_spin, 1, 1)

        g.addWidget(QLabel("JPEG q"), 1, 2)
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(70, 101)
        self.quality_spin.setValue(95)
        self.quality_spin.setToolTip("101 writes PNG instead of JPEG.")
        g.addWidget(self.quality_spin, 1, 3)

        g.addWidget(QLabel("Rotate"), 2, 0)
        self.rotate_combo = QComboBox()
        self.rotate_combo.addItems(["0", "90", "180", "270"])
        g.addWidget(self.rotate_combo, 2, 1)
        c.v.addLayout(g)

        self.estimate = QLabel("")
        self.estimate.setObjectName("Muted")
        self.estimate.setWordWrap(True)
        c.v.addWidget(self.estimate)
        return c

    def _card_engine(self):
        c = Card("3. Spirula Studio")
        r = QHBoxLayout()
        self.spirula_edit = QLineEdit()
        self.spirula_edit.setPlaceholderText("path to spirula.exe")
        r.addWidget(self.spirula_edit)
        b = QPushButton("Browse")
        b.clicked.connect(self._browse_spirula)
        r.addWidget(b)
        c.v.addLayout(r)

        r2 = QHBoxLayout()
        self.spirula_status = QLabel("not found")
        self.spirula_status.setObjectName("Bad")
        r2.addWidget(self.spirula_status, 1)
        find = QPushButton("Find")
        find.clicked.connect(lambda: self._autodetect_spirula(quiet=False))
        r2.addWidget(find)
        self.help_btn = QPushButton("Show options")
        self.help_btn.setToolTip("Runs `spirula train --help` and prints it in the log,\n"
                                 "so you can copy any extra flag into the boxes below.")
        self.help_btn.clicked.connect(self._show_spirula_help)
        r2.addWidget(self.help_btn)
        get = QPushButton("Get it")
        get.setObjectName("Link")
        get.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(SPIRULA_URL)))
        r2.addWidget(get)
        c.v.addLayout(r2)

        g = QGridLayout()
        g.setHorizontalSpacing(SPACING_SM)
        g.setVerticalSpacing(SPACING_SM)
        g.addWidget(QLabel("SfM quality"), 0, 0)
        self.sfm_quality = QComboBox()
        self.sfm_quality.addItems(core.SFM_QUALITIES)
        self.sfm_quality.setCurrentText("high")
        g.addWidget(self.sfm_quality, 0, 1)
        g.addWidget(QLabel("Preset"), 0, 2)
        self.train_preset = QComboBox()
        self.train_preset.addItems(core.TRAIN_PRESETS)
        g.addWidget(self.train_preset, 0, 3)
        g.addWidget(QLabel("Steps"), 1, 0)
        self.train_steps = QSpinBox()
        self.train_steps.setRange(200, 200000)
        self.train_steps.setSingleStep(1000)
        self.train_steps.setValue(30000)
        self.train_steps.setGroupSeparatorShown(True)
        self.train_steps.setToolTip("Training iterations. 30000 is Spirula's default.\n"
                                    "Drop to a few hundred for a quick look at whether\n"
                                    "the capture solved at all.")
        g.addWidget(self.train_steps, 1, 1)
        c.v.addLayout(g)

        self.sfm_extra = QLineEdit()
        self.sfm_extra.setPlaceholderText("extra flags for: spirula sfm auto")
        c.v.addWidget(self.sfm_extra)
        self.train_extra = QLineEdit()
        self.train_extra.setPlaceholderText("extra flags for: spirula train")
        c.v.addWidget(self.train_extra)
        return c

    def _card_output(self):
        c = Card("4. Output")
        c.v.addWidget(QLabel("Working folder (frames, poses, checkpoints)"))
        r = QHBoxLayout()
        self.out_edit = QLineEdit()
        self.out_edit.setPlaceholderText(str(DEFAULT_WORK))
        r.addWidget(self.out_edit)
        b = QPushButton("Browse")
        b.clicked.connect(self._browse_out)
        r.addWidget(b)
        c.v.addLayout(r)

        c.v.addWidget(QLabel("Finished splats go here"))
        r4 = QHBoxLayout()
        self.deliver_edit = QLineEdit()
        self.deliver_edit.setPlaceholderText(str(DEFAULT_OUT))
        r4.addWidget(self.deliver_edit)
        b3 = QPushButton("Browse")
        b3.clicked.connect(self._browse_deliver)
        r4.addWidget(b3)
        self.open_out_btn = QPushButton("Open")
        self.open_out_btn.clicked.connect(self._open_out_folder)
        r4.addWidget(self.open_out_btn)
        c.v.addLayout(r4)

        r5 = QHBoxLayout()
        r5.addWidget(QLabel("When done"))
        self.cleanup_combo = QComboBox()
        self.cleanup_combo.addItem("Keep every working file", "keep")
        self.cleanup_combo.addItem("Delete the rebuildable leftovers (recommended)", "tidy")
        self.cleanup_combo.addItem("Keep only the splat", "minimal")
        self.cleanup_combo.setCurrentIndex(1)
        self.cleanup_combo.setToolTip(
            "Recommended keeps the frames and camera poses, so you can retry training\n"
            "with another preset without re-solving. Only the splat throws those away too.")
        r5.addWidget(self.cleanup_combo, 1)
        c.v.addLayout(r5)

        c.v.addWidget(divider())
        self.prep_check = QCheckBox("Shrink for the Quest with splat_prep")
        self.prep_check.setChecked(True)
        self.prep_check.stateChanged.connect(self._sync_prep_enabled)
        c.v.addWidget(self.prep_check)

        r2 = QHBoxLayout()
        self.prep_edit = QLineEdit()
        self.prep_edit.setPlaceholderText("path to splat_prep_v*.py")
        r2.addWidget(self.prep_edit)
        b2 = QPushButton("Browse")
        b2.clicked.connect(self._browse_prep)
        r2.addWidget(b2)
        c.v.addLayout(r2)

        r3 = QHBoxLayout()
        r3.addWidget(QLabel("Target splats"))
        self.prep_target = QSpinBox()
        self.prep_target.setRange(100_000, 8_000_000)
        self.prep_target.setSingleStep(100_000)
        self.prep_target.setValue(1_500_000)
        self.prep_target.setGroupSeparatorShown(True)
        r3.addWidget(self.prep_target)
        r3.addStretch(1)
        c.v.addLayout(r3)
        return c

    def _open_out_folder(self):
        d = Path(self.deliver_edit.text().strip('" ') or DEFAULT_OUT)
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def _card_run(self):
        c = Card("Run")
        toggles = QHBoxLayout()
        self.step_extract = QCheckBox("Extract")
        self.step_sfm = QCheckBox("Poses")
        self.step_train = QCheckBox("Train")
        for cb in (self.step_extract, self.step_sfm, self.step_train):
            cb.setChecked(True)
            toggles.addWidget(cb)
        toggles.addStretch(1)
        c.v.addLayout(toggles)

        run_row = QHBoxLayout()
        self.run_btn = QPushButton("Make the splat")
        self.run_btn.setObjectName("Primary")
        self.run_btn.clicked.connect(self._start)
        run_row.addWidget(self.run_btn)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel)
        run_row.addWidget(self.cancel_btn)
        run_row.addStretch(1)
        c.v.addLayout(run_row)

        self.step_label = QLabel("Idle.")
        self.step_label.setObjectName("H2")
        c.v.addWidget(self.step_label)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        c.v.addWidget(self.progress)

        c.v.addWidget(divider())
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(4000)
        self.log.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        c.v.addWidget(self.log, 1)

        out_row = QHBoxLayout()
        self.result_label = QLabel("")
        self.result_label.setObjectName("Muted")
        self.result_label.setWordWrap(True)
        out_row.addWidget(self.result_label, 1)
        self.open_btn = QPushButton("Open folder")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_result)
        out_row.addWidget(self.open_btn)
        c.v.addLayout(out_row)
        return c

    # -- drag and drop -----------------------------------------------------
    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self.drop_hint.setProperty("hot", True)
            self._restyle(self.drop_hint)

    def dragLeaveEvent(self, e):
        self.drop_hint.setProperty("hot", False)
        self._restyle(self.drop_hint)

    def dropEvent(self, e):
        self.drop_hint.setProperty("hot", False)
        self._restyle(self.drop_hint)
        paths = []
        for url in e.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_dir():                      # a dropped folder brings its videos
                paths += sorted(str(f) for f in p.iterdir()
                                if f.suffix.lower() in VIDEO_EXTS)
            elif p.is_file():
                paths.append(str(p))
        n = self._add_videos(paths)
        if not n and paths:
            QMessageBox.information(self, APP_NAME, "None of those look like videos.")

    @staticmethod
    def _restyle(w):
        w.style().unpolish(w)
        w.style().polish(w)

    # -- actions -----------------------------------------------------------
    def _browse_video(self):
        p, _ = QFileDialog.getOpenFileName(
            self, "Choose a video", self.video_edit.text() or "",
            "Video (*.mp4 *.mov *.mkv *.avi *.m4v *.insv);;All files (*)")
        if p:
            self.video_edit.setText(p)
            self._probe()

    def _browse_spirula(self):
        p, _ = QFileDialog.getOpenFileName(self, "Find spirula.exe",
                                           self.spirula_edit.text() or "",
                                           "Executable (*.exe);;All files (*)")
        if p:
            self.spirula_edit.setText(p)
            self._check_spirula()

    def _browse_out(self):
        p = QFileDialog.getExistingDirectory(self, "Working folder", self.out_edit.text() or "")
        if p:
            self.out_edit.setText(p)

    def _browse_prep(self):
        p, _ = QFileDialog.getOpenFileName(self, "Find splat_prep", self.prep_edit.text() or "",
                                           "Python (*.py);;All files (*)")
        if p:
            self.prep_edit.setText(p)

    def _browse_deliver(self):
        p = QFileDialog.getExistingDirectory(self, "Deliver the finished PLY to",
                                             self.deliver_edit.text() or "")
        if p:
            self.deliver_edit.setText(p)

    def _probe(self):
        path = self.video_edit.text().strip('" ')
        if not path or not Path(path).is_file():
            self.info = None
            self.video_info.setText("No video loaded.")
            self._update_estimate()
            return
        self.info = core.probe_video(path)
        if not self.info.ok:
            self.video_info.setText("Could not read that file as a video.")
            self.video_info.setObjectName("Bad")
        else:
            self.video_info.setText(self.info.describe())
            self.video_info.setObjectName("Muted")
            s = core.suggest_settings(self.info)
            self.target_spin.blockSignals(True)
            self.target_spin.setValue(s.target_frames)
            self.target_spin.blockSignals(False)
        self.video_info.style().unpolish(self.video_info)
        self.video_info.style().polish(self.video_info)
        self._update_estimate()

    def _target_changed(self):
        self._update_estimate()

    def _settings_from_ui(self) -> core.ExtractSettings:
        s = core.ExtractSettings()
        s.target_frames = self.target_spin.value()
        s.keep = self.keep_spin.value()
        s.scale = self.scale_spin.value()
        s.quality = self.quality_spin.value()
        s.rotate = int(self.rotate_combo.currentText())
        if self.info and self.info.n_frames:
            s.skip = max(1, round(self.info.n_frames / max(1, s.target_frames)))
        return s

    def _update_estimate(self):
        if not self.info or not self.info.ok:
            self.estimate.setText("Load a video to see how many frames will be kept.")
            return
        s = self._settings_from_ui()
        n = core.expected_frame_count(self.info, s)
        fps_kept = n / self.info.duration if self.info.duration else 0
        self.estimate.setText(
            f"Writes about {n} frames, one every {s.skip} source frames "
            f"({fps_kept:.1f} per second of video), each the sharpest of "
            f"{s.effective_keep()}. Two to three frames per second is the sweet spot "
            f"for photogrammetry; more mostly costs solve time."
        )

    def _autodetect_spirula(self, quiet: bool):
        found = core.find_spirula(self.spirula_edit.text().strip('" ') or None)
        if found:
            self.spirula_edit.setText(str(found))
        elif not quiet:
            QMessageBox.information(
                self, "Spirula Studio not found",
                "Could not find spirula.exe on PATH or in the usual folders.\n\n"
                "Download it from the Releases page, unzip it anywhere, then point "
                "this box at spirula.exe.")
        self._check_spirula()

    def _check_spirula(self):
        p = self.spirula_edit.text().strip('" ')
        ok = bool(p) and Path(p).is_file()
        self.spirula_status.setText("ready" if ok else "not found")
        self.spirula_status.setObjectName("Ok" if ok else "Bad")
        self.spirula_status.style().unpolish(self.spirula_status)
        self.spirula_status.style().polish(self.spirula_status)
        self.help_btn.setEnabled(ok)

    def _show_spirula_help(self):
        p = self.spirula_edit.text().strip('" ')
        if not Path(p).is_file():
            return
        self.help_btn.setEnabled(False)
        self._append("")
        self._append("--- spirula train --help ---")
        self.help_thread = HelpThread(p, "train")
        self.help_thread.log_line.connect(self._append)
        self.help_thread.done.connect(lambda: self.help_btn.setEnabled(True))
        self.help_thread.start()

    def _sync_prep_enabled(self):
        on = self.prep_check.isChecked()
        self.prep_edit.setEnabled(on)
        self.prep_target.setEnabled(on)

    # -- run ---------------------------------------------------------------
    def _start(self):
        self.pending = [p for p in self._queue_paths() if Path(p).is_file()]
        if not self.pending:
            QMessageBox.warning(self, APP_NAME, "Drop a video in first.")
            return
        self.batch_total = len(self.pending)
        self.batch_done = []
        self._start_next()

    def _start_next(self):
        if not self.pending:
            self._batch_finished()
            return
        video = self.pending.pop(0)
        self.video_edit.setText(video)
        self._probe()
        self._start_one(video)

    def _batch_finished(self):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.progress.setRange(0, 100)
        ok = [r for r in self.batch_done if r.ok]
        self.progress.setValue(100 if ok else 0)
        if self.batch_total > 1:
            self.step_label.setText(f"Done: {len(ok)} of {self.batch_total}.")
        elif ok:
            self.step_label.setText("Done.")
        else:
            last = self.batch_done[-1] if self.batch_done else None
            self.step_label.setText("Stopped: " + (last.failed_step if last else "error"))
        if ok:
            last = ok[-1]
            final = last.delivered or last.quest_ply or last.raw_ply
            self.result_label.setText(str(final) if final else "")
            self.open_btn.setEnabled(bool(final))
            self.result = last
        elif self.batch_done:
            self.result_label.setText(self.batch_done[-1].message)

    def _start_one(self, video):
        out_root = self.out_edit.text().strip('" ') or str(DEFAULT_WORK)
        spirula = self.spirula_edit.text().strip('" ')
        needs_spirula = self.step_sfm.isChecked() or self.step_train.isChecked()
        if needs_spirula and not Path(spirula).is_file():
            QMessageBox.warning(
                self, APP_NAME,
                "Spirula Studio is needed for the poses and training steps.\n\n"
                "Point section 3 at spirula.exe, or untick those steps to only "
                "extract frames.")
            return

        prep = self.prep_edit.text().strip('" ')
        job = core.JobSettings(
            video=Path(video),
            out_root=Path(out_root),
            spirula=Path(spirula) if spirula else None,
            extract=self._settings_from_ui(),
            sfm_quality=self.sfm_quality.currentText(),
            sfm_data_type="video",
            train_preset=self.train_preset.currentText(),
            train_iterations=self.train_steps.value(),
            sfm_extra=self.sfm_extra.text().split(),
            train_extra=self.train_extra.text().split(),
            do_extract=self.step_extract.isChecked(),
            do_sfm=self.step_sfm.isChecked(),
            do_train=self.step_train.isChecked(),
            do_prep=self.prep_check.isChecked() and bool(prep),
            prep_script=Path(prep) if prep else None,
            prep_target=self.prep_target.value(),
            prep_crop=1.0,
            deliver_to=Path(self.deliver_edit.text().strip('" ') or DEFAULT_OUT),
            cleanup=self.cleanup_combo.currentData(),
        )

        if not self.batch_done:
            self.log.clear()
            self._append(f"{APP_NAME} v{APP_VERSION}")
        idx = self.batch_total - len(self.pending)
        self._append("")
        self._append(f"=== [{idx}/{self.batch_total}] {Path(video).name}")
        self.result = None
        self.open_btn.setEnabled(False)
        self.result_label.setText("")
        self.run_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress.setRange(0, 0)

        self.thread = JobThread(job)
        self.thread.log_line.connect(self._append)
        self.thread.step_changed.connect(self._on_step)
        self.thread.progressed.connect(self._on_progress)
        self.thread.finished_job.connect(self._on_done)
        self.thread.start()

    def _cancel(self):
        if self.thread:
            self.thread.cancel()
            self.step_label.setText("Cancelling...")

    def _append(self, line: str):
        self.log.appendPlainText(line)

    def _on_step(self, name: str):
        self.step_label.setText(name)
        if name != "Extracting frames":
            self.progress.setRange(0, 0)

    def _on_progress(self, done: int, total: int):
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(done)

    def _on_done(self, res: core.JobResult):
        self.result = res
        self.batch_done.append(res)
        self._report(res)
        if res.failed_step == "cancelled":
            self.pending = []          # cancelling stops the whole queue, not one clip
        if self.pending:
            self._start_next()
            return
        self._batch_finished()

    def _report(self, res: core.JobResult):
        if res.ok:
            final = res.delivered or res.quest_ply or res.raw_ply
            if final:
                self._append(f"DONE: {final}")
            elif res.frames:
                self._append(f"DONE: {res.frames} frames in {res.image_dir}")
            else:
                self._append("DONE.")
            if res.freed_bytes:
                self._append(f"({res.freed_bytes / 1e6:.0f} MB of working files removed)")
        else:
            self._append(f"STOPPED at {res.failed_step}: {res.message}")

    def _open_result(self):
        res = self.result
        if not res:
            return
        final = res.delivered or res.quest_ply or res.raw_ply
        if final:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(final).parent)))

    # -- theme and persistence --------------------------------------------
    def _toggle_theme(self):
        app = QApplication.instance()
        dark = self.settings.value("dark", True, type=bool)
        dark = not dark
        self.settings.setValue("dark", dark)
        app.setStyleSheet(DARK_QSS if dark else LIGHT_QSS)
        self.theme_btn.setText("Light" if dark else "Dark")

    def _load_settings(self):
        s = self.settings
        self.spirula_edit.setText(s.value("spirula", "", type=str))
        self.out_edit.setText(s.value("out_root", "", type=str))
        self.prep_edit.setText(s.value("prep", "", type=str))
        self.deliver_edit.setText(s.value("deliver", "", type=str))
        self.sfm_quality.setCurrentText(s.value("sfm_quality", "high", type=str))
        self.train_preset.setCurrentText(s.value("preset", "3dgs", type=str))
        self.prep_target.setValue(s.value("prep_target", 1_500_000, type=int))
        self.train_steps.setValue(s.value("steps", 30000, type=int))
        idx = self.cleanup_combo.findData(s.value("cleanup", "tidy", type=str))
        self.cleanup_combo.setCurrentIndex(idx if idx >= 0 else 1)
        self.prep_check.setChecked(s.value("do_prep", True, type=bool))
        dark = s.value("dark", True, type=bool)
        QApplication.instance().setStyleSheet(DARK_QSS if dark else LIGHT_QSS)
        self.theme_btn.setText("Light" if dark else "Dark")
        self._sync_prep_enabled()

    def closeEvent(self, e):
        s = self.settings
        s.setValue("spirula", self.spirula_edit.text())
        s.setValue("out_root", self.out_edit.text())
        s.setValue("prep", self.prep_edit.text())
        s.setValue("deliver", self.deliver_edit.text())
        s.setValue("sfm_quality", self.sfm_quality.currentText())
        s.setValue("preset", self.train_preset.currentText())
        s.setValue("prep_target", self.prep_target.value())
        s.setValue("steps", self.train_steps.value())
        s.setValue("cleanup", self.cleanup_combo.currentData())
        s.setValue("do_prep", self.prep_check.isChecked())
        if self.thread and self.thread.isRunning():
            self.thread.cancel()
            self.thread.wait(3000)
        super().closeEvent(e)


def app_icon() -> QIcon:
    pm = QPixmap(64, 64)
    pm.fill(QColor(DARK_BACKGROUND))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    for cx, cy, r, col in ((22, 26, 16, "#5ee0c1"), (40, 34, 14, "#b2c5ff"), (30, 44, 11, "#f7b955")):
        c = QColor(col)
        c.setAlpha(190)
        p.setBrush(c)
        p.drawEllipse(cx - r, cy - r, 2 * r, 2 * r)
    p.end()
    return QIcon(pm)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setFont(QFont(FONT_BODY, 10))
    app.setWindowIcon(app_icon())
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
