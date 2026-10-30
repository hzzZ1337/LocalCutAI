from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QAbstractScrollArea,
    QCheckBox,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFontComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QSpinBox,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .ai import transcribe_video
from .captions import apply_caption_text_edit, flatten_words, group_words, save_transcript_json, write_ass, write_srt
from .video_ops import burn_subtitles, create_short, probe_duration, remove_silence, suggest_moments
from .tts import VOICE_CATALOG, SPEECH_STYLE_CATALOG, generate_voice_preview, render_voice_replacement
from .worker import TaskWorker


DARK_STYLE = """
QWidget { background: #111318; color: #edf0f6; font-family: 'Segoe UI'; font-size: 10pt; }
QMainWindow { background: #111318; }
QGroupBox { border: 1px solid #303643; border-radius: 10px; margin-top: 12px; padding: 14px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 7px; color: #aeb9cf; }
QPushButton { background: #242a36; border: 1px solid #3a4354; border-radius: 8px; padding: 9px 13px; font-weight: 600; }
QPushButton:hover { background: #30394b; border-color: #7488ad; }
QPushButton:pressed { background: #1c2230; }
QPushButton:disabled { color: #747b89; background: #1b1e25; border-color: #282c35; }
QPushButton#Primary { background: #6553e8; border-color: #8174f5; color: white; }
QPushButton#Primary:hover { background: #7768f2; }
QLineEdit, QComboBox, QSpinBox, QFontComboBox, QListWidget, QPlainTextEdit { background: #191d25; border: 1px solid #343b49; border-radius: 7px; padding: 7px; selection-background-color: #6553e8; }
QComboBox QAbstractItemView { background: #191d25; selection-background-color: #6553e8; }
QScrollBar:vertical { background: #191d25; width: 15px; margin: 2px; border: 1px solid #343b49; border-radius: 6px; }
QScrollBar::handle:vertical { background: #58647a; min-height: 28px; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #7a89a5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QCheckBox { spacing: 8px; }
QProgressBar { background: #191d25; border: 1px solid #343b49; border-radius: 5px; text-align: center; min-height: 13px; }
QProgressBar::chunk { background: #6553e8; border-radius: 4px; }
QFrame#TTSFooter { background: #151922; border: 1px solid #303643; border-radius: 8px; }
QLabel#Brand { font-size: 24pt; font-weight: 800; letter-spacing: 1px; color: #ffffff; }
QLabel#Muted { color: #9aa3b5; }
QLabel#Status { color: #c7cce0; padding: 3px; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        asset_dir = Path(__file__).resolve().parent.parent / "assets"
        app_icon_path = asset_dir / "LocalCutAI.ico"
        if app_icon_path.is_file():
            self.setWindowIcon(QIcon(str(app_icon_path)))
        self.setWindowTitle("LocalCut AI — lokalny montaż filmów")
        self.resize(1180, 900)
        self.setMinimumSize(940, 660)
        self.input_path: str | None = None
        self.words: list[dict[str, Any]] = []
        self.segments: list[dict[str, Any]] = []
        self.caption_row_groups: list[list[dict[str, Any]]] = []
        self.candidates: list[dict[str, Any]] = []
        self.video_duration: float = 0.0
        self.worker: TaskWorker | None = None
        self.text_color = "#FFFFFF"
        self.highlight_color = "#FFD400"

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        logo_label = QLabel()
        logo_label.setFixedSize(52, 52)
        logo_path = asset_dir / "localcutai-logo.png"
        if logo_path.is_file():
            logo_label.setPixmap(
                QPixmap(str(logo_path)).scaled(
                    48, 48,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        header.addWidget(logo_label)
        brand_box = QVBoxLayout()
        brand = QLabel("LOCALCUT AI")
        brand.setObjectName("Brand")
        tagline = QLabel("Lokalny asystent montażu • Windows • polskie napisy AI")
        tagline.setObjectName("Muted")
        brand_box.addWidget(brand)
        brand_box.addWidget(tagline)
        header.addLayout(brand_box, 1)
        self.status_label = QLabel("Gotowy do pracy")
        self.status_label.setObjectName("Status")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.status_label)
        layout.addLayout(header)

        file_group = QGroupBox("1. Film i folder wynikowy")
        file_layout = QVBoxLayout(file_group)
        video_row = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Wybierz film MP4, MKV, MOV lub inny obsługiwany przez FFmpeg…")
        browse_video = QPushButton("Wybierz film")
        browse_video.clicked.connect(self.pick_video)
        video_row.addWidget(self.path_edit, 1)
        video_row.addWidget(browse_video)
        file_layout.addLayout(video_row)
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Zapis wyników:"))
        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("Domyślnie: LocalCutAI_output obok filmu")
        browse_output = QPushButton("Wybierz folder")
        browse_output.clicked.connect(self.pick_output)
        output_row.addWidget(self.output_edit, 1)
        output_row.addWidget(browse_output)
        file_layout.addLayout(output_row)
        layout.addWidget(file_group)

        settings_group = QGroupBox("2. Ustawienia AI i wygląd napisów")
        settings_layout = QVBoxLayout(settings_group)
        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model mowy:"))
        self.model_combo = QComboBox()
        self.model_combo.addItem("base — polecany na CPU, szybszy", "base")
        self.model_combo.addItem("small — dokładniejszy, wolniejszy na CPU", "small")
        self.model_combo.addItem("medium — dokładniejszy, najwolniejszy na CPU", "medium")
        self.model_combo.setMinimumWidth(255)
        model_row.addWidget(self.model_combo)
        model_row.addSpacing(12)
        model_row.addWidget(QLabel("Czcionka:"))
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(self.font_combo.currentFont())
        model_row.addWidget(self.font_combo, 1)
        model_row.addWidget(QLabel("Rozmiar:"))
        self.font_size = QSpinBox()
        self.font_size.setRange(20, 100)
        self.font_size.setValue(54)
        self.font_size.setSuffix(" px")
        model_row.addWidget(self.font_size)
        settings_layout.addLayout(model_row)

        style_row = QHBoxLayout()
        self.text_color_btn = QPushButton("Kolor tekstu: biały")
        self.text_color_btn.clicked.connect(self.choose_text_color)
        self.highlight_color_btn = QPushButton("Podświetlenie: żółte")
        self.highlight_color_btn.clicked.connect(self.choose_highlight_color)
        self.karaoke_check = QCheckBox("Podświetlaj słowa w rytmie mowy")
        self.karaoke_check.setChecked(True)
        style_row.addWidget(self.text_color_btn)
        style_row.addWidget(self.highlight_color_btn)
        style_row.addWidget(self.karaoke_check, 1)
        style_row.addWidget(QLabel("Animacja:"))
        self.animation_combo = QComboBox()
        self.animation_combo.addItems(["Pop-in", "Fade-in", "Slide-up", "Zoom-in", "Bounce", "Bez animacji"])
        style_row.addWidget(self.animation_combo)
        settings_layout.addLayout(style_row)
        save_style_btn = QPushButton("Zapisz ponownie plik .ASS z aktualnym stylem")
        save_style_btn.clicked.connect(self.regenerate_ass)
        settings_layout.addWidget(save_style_btn, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(settings_group)

        actions_group = QGroupBox("3. Narzędzia montażowe")
        actions_layout = QVBoxLayout(actions_group)
        actions_row_1 = QHBoxLayout()
        actions_row_2 = QHBoxLayout()
        self.caption_btn = QPushButton("Generuj polskie napisy AI")
        self.caption_btn.setObjectName("Primary")
        self.caption_btn.clicked.connect(self.start_transcription)
        self.burn_btn = QPushButton("Wypal animowane napisy do MP4")
        self.burn_btn.setObjectName("Primary")
        self.burn_btn.clicked.connect(self.start_burn_subtitles)
        self.silence_btn = QPushButton("Wykryj i usuń ciszę")
        self.silence_btn.clicked.connect(self.start_silence_removal)
        self.moments_btn = QPushButton("Znajdź najlepsze fragmenty")
        self.moments_btn.clicked.connect(self.start_moment_analysis)
        self.shorts_btn = QPushButton("Utwórz pionowe Shortsy")
        self.shorts_btn.setObjectName("Primary")
        self.shorts_btn.clicked.connect(self.start_shorts_export)
        for button in (self.caption_btn, self.burn_btn, self.silence_btn):
            button.setMinimumHeight(48)
            button.setMinimumWidth(190)
            actions_row_1.addWidget(button, 1)
        for button in (self.moments_btn, self.shorts_btn):
            button.setMinimumHeight(48)
            button.setMinimumWidth(190)
            actions_row_2.addWidget(button, 1)
        actions_layout.addLayout(actions_row_1)
        actions_layout.addLayout(actions_row_2)
        layout.addWidget(actions_group)

        lower = QHBoxLayout()
        workspace_tabs = QTabWidget()

        moments_tab = QWidget()
        moments_layout = QVBoxLayout(moments_tab)
        self.moments_list = QListWidget()
        self.moments_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.moments_list.setMinimumHeight(170)
        moments_layout.addWidget(self.moments_list)
        moment_hint = QLabel("Ranking heurystyczny: gęstość mowy i interpunkcja, nie pełne rozumienie sensu filmu.")
        moment_hint.setObjectName("Muted")
        moment_hint.setWordWrap(True)
        moments_layout.addWidget(moment_hint)
        workspace_tabs.addTab(moments_tab, "Propozycje fragmentów")

        editor_tab = QWidget()
        editor_layout = QVBoxLayout(editor_tab)
        editor_hint = QLabel("Edytuj tekst oraz Start/Koniec (format HH:MM:SS.mmm, np. 00:00:03.500). Dodaj własny napis albo zaznacz jeden lub kilka wierszy i kliknij „Usuń zaznaczone”. Po zmianach kliknij „Zapisz poprawki” albo „Zapisz i wypal MP4”.")
        editor_hint.setObjectName("Muted")
        editor_hint.setWordWrap(True)
        editor_layout.addWidget(editor_hint)
        self.caption_table = QTableWidget(0, 3)
        self.caption_table.setHorizontalHeaderLabels(["Start (HH:MM:SS.mmm)", "Koniec (HH:MM:SS.mmm)", "Tekst napisów (edytuj)"])
        self.caption_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.caption_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.caption_table.setAlternatingRowColors(True)
        self.caption_table.setWordWrap(True)
        self.caption_table.verticalHeader().setVisible(False)
        self.caption_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.caption_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.caption_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.caption_table.setMinimumHeight(190)
        editor_layout.addWidget(self.caption_table, 1)
        editor_buttons = QHBoxLayout()
        self.load_transcript_btn = QPushButton("Wczytaj zapisane napisy")
        self.load_transcript_btn.clicked.connect(self.load_saved_transcript)
        self.add_caption_btn = QPushButton("+ Dodaj napis")
        self.add_caption_btn.clicked.connect(self.add_caption_row)
        self.remove_caption_btn = QPushButton("Usuń zaznaczone")
        self.remove_caption_btn.clicked.connect(self.remove_caption_rows)
        self.save_edits_btn = QPushButton("Zapisz poprawki")
        self.save_edits_btn.clicked.connect(self.save_caption_edits)
        self.save_burn_btn = QPushButton("Zapisz i wypal MP4")
        self.save_burn_btn.setObjectName("Primary")
        self.save_burn_btn.clicked.connect(self.save_edits_and_burn)
        editor_buttons.addWidget(self.load_transcript_btn)
        editor_buttons.addWidget(self.add_caption_btn)
        editor_buttons.addWidget(self.remove_caption_btn)
        editor_buttons.addWidget(self.save_edits_btn)
        editor_buttons.addWidget(self.save_burn_btn)
        editor_layout.addLayout(editor_buttons)
        workspace_tabs.addTab(editor_tab, "Popraw tekst napisów")

        # Local speech synthesis / voice replacement workspace.
        # A compact editor + a dedicated fixed footer keeps all actions below the
        # table, even after adding many fragments or when Windows DPI scaling is on.
        tts_tab = QWidget()
        tts_layout = QVBoxLayout(tts_tab)
        tts_layout.setContentsMargins(8, 8, 8, 8)
        tts_layout.setSpacing(6)

        tts_hint = QLabel(
            "Lektor AI działa lokalnie. Wczytaj tekst, wybierz głos i styl, a potem wypal MP4. "
            "Oryginalna ścieżka audio zostanie zastąpiona nową mową."
        )
        tts_hint.setObjectName("Muted")
        tts_hint.setWordWrap(True)
        tts_hint.setMaximumHeight(38)
        tts_layout.addWidget(tts_hint)

        # Keep voice and delivery-style selectors on one compact row to reserve
        # vertical space for the transcript table and the footer controls.
        tts_voice_row = QHBoxLayout()
        tts_voice_row.setSpacing(6)
        tts_voice_row.addWidget(QLabel("Głos AI:"))
        self.tts_voice_combo = QComboBox()
        for voice_key, voice_info in VOICE_CATALOG.items():
            self.tts_voice_combo.addItem(voice_info["label"], voice_key)
        self.tts_voice_combo.setMinimumWidth(120)
        tts_voice_row.addWidget(self.tts_voice_combo, 3)
        tts_voice_row.addWidget(QLabel("Styl:"))
        self.tts_style_combo = QComboBox()
        for style_key, style_info in SPEECH_STYLE_CATALOG.items():
            self.tts_style_combo.addItem(style_info["label"], style_key)
            self.tts_style_combo.setItemData(
                self.tts_style_combo.count() - 1,
                style_info.get("help", ""),
                Qt.ItemDataRole.ToolTipRole,
            )
        self.tts_style_combo.setCurrentIndex(max(0, self.tts_style_combo.findData("natural")))
        self.tts_style_combo.setMinimumWidth(145)
        self.tts_style_combo.setToolTip(
            "Profile zmieniają tempo i parametry syntezy Piper. Nie klonują głosu osoby z filmu "
            "ani nie gwarantują ludzkiej intonacji — najlepiej odsłuchać próbkę przed eksportem."
        )
        tts_voice_row.addWidget(self.tts_style_combo, 4)
        tts_layout.addLayout(tts_voice_row)

        self.tts_table = QTableWidget(0, 3)
        self.tts_table.setHorizontalHeaderLabels(["START", "KONIEC", "Tekst wypowiadany przez AI"])
        self.tts_table.horizontalHeaderItem(0).setToolTip("Początek wypowiedzi, np. 00:00:03.500")
        self.tts_table.horizontalHeaderItem(1).setToolTip("Koniec wypowiedzi, np. 00:00:06.000")
        self.tts_table.horizontalHeaderItem(2).setToolTip("Tekst, który ma wypowiedzieć wybrany głos AI")
        self.tts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tts_table.setAlternatingRowColors(True)
        self.tts_table.setWordWrap(True)
        self.tts_table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustIgnored)
        self.tts_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tts_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.tts_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.tts_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.tts_table.verticalHeader().setVisible(False)
        # Fixed row heights stop new fragments from making the table demand more
        # vertical space and pushing the footer outside the visible tab.
        self.tts_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tts_table.verticalHeader().setDefaultSectionSize(48)
        self.tts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.tts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.tts_table.setColumnWidth(0, 112)
        self.tts_table.setColumnWidth(1, 112)
        self.tts_table.setMinimumHeight(78)
        tts_layout.addWidget(self.tts_table, 1)

        # A separate frame with fixed vertical size creates a clear, non-overlapping
        # footer. The table above owns the available stretch and scrolls internally.
        tts_footer = QFrame(tts_tab)
        tts_footer.setObjectName("TTSFooter")
        tts_footer.setFrameShape(QFrame.Shape.StyledPanel)
        tts_footer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        tts_footer.setMinimumHeight(100)
        tts_footer.setMaximumHeight(112)
        tts_footer_layout = QVBoxLayout(tts_footer)
        tts_footer_layout.setContentsMargins(7, 6, 7, 6)
        tts_footer_layout.setSpacing(5)

        tts_button_row = QHBoxLayout()
        tts_button_row.setSpacing(6)
        self.tts_load_btn = QPushButton("Wczytaj tekst z edytora napisów")
        self.tts_load_btn.setToolTip("Kopiuje tekst i czasy z zakładki Popraw tekst napisów")
        self.tts_load_btn.clicked.connect(self.load_tts_from_editor)
        self.tts_add_btn = QPushButton("+ Dodaj fragment")
        self.tts_add_btn.clicked.connect(self.add_tts_row)
        self.tts_remove_btn = QPushButton("Usuń zaznaczony")
        self.tts_remove_btn.clicked.connect(self.remove_tts_row)
        self.tts_load_btn.setMinimumWidth(190)
        self.tts_add_btn.setMinimumWidth(110)
        self.tts_remove_btn.setMinimumWidth(115)
        for button in (self.tts_load_btn, self.tts_add_btn, self.tts_remove_btn):
            button.setMinimumHeight(35)
        tts_button_row.addWidget(self.tts_load_btn, 2)
        tts_button_row.addWidget(self.tts_add_btn, 1)
        tts_button_row.addWidget(self.tts_remove_btn, 1)
        tts_footer_layout.addLayout(tts_button_row)

        tts_bottom_row = QHBoxLayout()
        tts_bottom_row.setSpacing(6)
        self.tts_preview_btn = QPushButton("Odsłuchaj próbkę głosu")
        self.tts_preview_btn.clicked.connect(self.start_tts_preview)
        self.tts_preview_btn.setMinimumHeight(37)
        self.tts_export_btn = QPushButton("Generuj lektora i wypal MP4")
        self.tts_export_btn.setObjectName("Primary")
        self.tts_export_btn.setMinimumHeight(37)
        self.tts_export_btn.clicked.connect(self.start_tts_export)
        tts_bottom_row.addWidget(self.tts_preview_btn, 1)
        tts_bottom_row.addWidget(self.tts_export_btn, 2)
        tts_footer_layout.addLayout(tts_bottom_row)
        tts_layout.addWidget(tts_footer, 0)
        workspace_tabs.addTab(tts_tab, "Lektor AI")
        lower.addWidget(workspace_tabs, 3)

        log_group = QGroupBox("Dziennik pracy")
        log_layout = QVBoxLayout(log_group)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("Tutaj pojawią się informacje o przebiegu pracy i zapisanych plikach…")
        self.log.setMaximumBlockCount(800)
        log_layout.addWidget(self.log)
        lower.addWidget(log_group, 2)
        layout.addLayout(lower, 1)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        footer = QLabel("Prywatność: rozpoznawanie mowy działa lokalnie. Pierwsze użycie modelu wymaga pobrania jego plików.")
        footer.setObjectName("Muted")
        layout.addWidget(footer)

        self.setStyleSheet(DARK_STYLE)
        self._log("Witaj! Wygeneruj napisy, a następnie wybierz „Wypal animowane napisy do MP4”, żeby zachować styl i animacje w DaVinci Resolve.")

    def _log(self, text: str) -> None:
        self.log.appendPlainText(text)
        self.status_label.setText(text.splitlines()[0][:80])

    def _ensure_video(self) -> bool:
        if self.input_path and Path(self.input_path).exists():
            return True
        QMessageBox.information(self, "Wybierz film", "Najpierw wybierz plik wideo.")
        return False

    def _output_dir(self) -> Path:
        custom = self.output_edit.text().strip()
        if custom:
            path = Path(custom).expanduser()
        elif self.input_path:
            path = Path(self.input_path).parent / "LocalCutAI_output"
        else:
            path = Path.cwd() / "LocalCutAI_output"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def pick_video(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Wybierz film", "", "Pliki wideo (*.mp4 *.mkv *.mov *.avi *.webm *.m4v);;Wszystkie pliki (*.*)"
        )
        if not file_path:
            return
        self.input_path = file_path
        self.path_edit.setText(file_path)
        if not self.output_edit.text().strip():
            self.output_edit.setText(str(Path(file_path).parent / "LocalCutAI_output"))
        self.words = []
        self.segments = []
        self.caption_row_groups = []
        self.caption_table.setRowCount(0)
        self.tts_table.setRowCount(0)
        self.candidates = []
        self.moments_list.clear()
        self._log(f"Wybrano: {Path(file_path).name}")
        # Automatically reopen transcript edits from a previous session, if present.
        loaded = self.load_saved_transcript(silent=True)
        if loaded:
            self.load_tts_from_editor(silent=True)

    def pick_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder wynikowy", self.output_edit.text().strip() or str(Path.home()))
        if folder:
            self.output_edit.setText(folder)

    @staticmethod
    def _precise_time(seconds: float) -> str:
        ms = max(0, int(round(float(seconds) * 1000)))
        h, ms = divmod(ms, 3_600_000)
        m, ms = divmod(ms, 60_000)
        sec, ms = divmod(ms, 1000)
        return f"{h:02}:{m:02}:{sec:02}.{ms:03}"

    def _populate_caption_editor(self) -> None:
        self.caption_table.setRowCount(0)
        self.caption_row_groups = []
        if not self.words:
            return
        # After manual edits, preserve the exact editor rows (including added captions)
        # when reopening the saved transcript. For raw AI output, group word timings automatically.
        editor_groups = []
        if self.segments and all(segment.get("_editor_group") for segment in self.segments):
            editor_groups = [
                [dict(word) for word in segment.get("words", [])]
                for segment in sorted(self.segments, key=lambda item: float(item.get("start", 0.0)))
                if segment.get("words")
            ]
        groups = editor_groups or group_words(self.words)
        self.caption_table.setRowCount(len(groups))
        for row, group in enumerate(groups):
            copied_group = [dict(word) for word in group]
            self.caption_row_groups.append(copied_group)
            start = min(float(item.get("start", 0.0)) for item in group)
            end = max(float(item.get("end", start + 0.04)) for item in group)
            start_item = QTableWidgetItem(self._precise_time(start))
            end_item = QTableWidgetItem(self._precise_time(end))
            # Start and end are intentionally editable: users can retime each caption.
            text = " ".join(str(item.get("word", "")).strip() for item in group).strip()
            text_item = QTableWidgetItem(text)
            self.caption_table.setItem(row, 0, start_item)
            self.caption_table.setItem(row, 1, end_item)
            self.caption_table.setItem(row, 2, text_item)
        self.caption_table.resizeRowsToContents()

    @staticmethod
    def _parse_editor_time(value: str) -> float:
        """Parse HH:MM:SS.mmm, MM:SS, or plain seconds entered in the caption table."""
        value = (value or "").strip().replace(",", ".")
        if not value:
            raise ValueError("Pole czasu nie może być puste.")
        try:
            if ":" not in value:
                seconds = float(value)
            else:
                parts = value.split(":")
                if len(parts) == 2:
                    minutes, seconds_part = parts
                    seconds = int(minutes) * 60 + float(seconds_part)
                elif len(parts) == 3:
                    hours, minutes, seconds_part = parts
                    seconds = int(hours) * 3600 + int(minutes) * 60 + float(seconds_part)
                else:
                    raise ValueError
        except (TypeError, ValueError):
            raise ValueError(f"Nieprawidłowy czas: '{value}'. Użyj HH:MM:SS.mmm, np. 00:00:02.500.")
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("Czas musi być skończoną, nieujemną liczbą.")
        return seconds

    @staticmethod
    def _make_words_for_interval(text: str, start: float, end: float) -> list[dict[str, Any]]:
        tokens = (text or "").split()
        if not tokens:
            return []
        if end - start < max(0.08, 0.04 * len(tokens)):
            raise ValueError(
                f"Przedział {start:.3f}–{end:.3f} s jest za krótki dla {len(tokens)} słów. "
                "Wydłuż czas wyświetlania napisu."
            )
        weights = [max(1, len(token.strip(".,!?;:…()[]{}\"'"))) for token in tokens]
        total = float(sum(weights))
        duration = end - start
        # Reserve at least 40 ms for each word, then distribute remaining time by word length.
        remaining = max(0.0, duration - 0.04 * len(tokens))
        durations = [0.04 + remaining * weight / total for weight in weights]
        cursor = start
        result: list[dict[str, Any]] = []
        for index, (token, word_duration) in enumerate(zip(tokens, durations)):
            word_start = cursor
            word_end = end if index == len(tokens) - 1 else min(end, cursor + word_duration)
            result.append({"word": token, "start": word_start, "end": max(word_start + 0.04, word_end), "probability": 1.0})
            cursor = word_end
        result[-1]["end"] = end
        return result

    def add_caption_row(self) -> None:
        """Add a manually authored caption with editable start/end times."""
        row = self.caption_table.rowCount()
        self.caption_table.insertRow(row)
        start_item = QTableWidgetItem("00:00:00.000")
        end_item = QTableWidgetItem("00:00:02.000")
        text_item = QTableWidgetItem("")
        text_item.setToolTip("Wpisz nowy napis")
        self.caption_table.setItem(row, 0, start_item)
        self.caption_table.setItem(row, 1, end_item)
        self.caption_table.setItem(row, 2, text_item)
        self.caption_row_groups.append([])
        # The editor is the second workspace tab (index 1); switch before starting in-place editing.
        parent_tabs = self.caption_table.parentWidget()
        while parent_tabs is not None and not isinstance(parent_tabs, QTabWidget):
            parent_tabs = parent_tabs.parentWidget()
        if parent_tabs is not None:
            parent_tabs.setCurrentIndex(1)
        self.caption_table.selectRow(row)
        self.caption_table.setCurrentCell(row, 2)
        self.caption_table.editItem(text_item)
        self._log("Dodano pusty wiersz. Wpisz tekst oraz ustaw czas Start i Koniec.")

    def remove_caption_rows(self) -> None:
        """Remove selected subtitle rows from the editor; changes persist on Save or Save & Burn."""
        selected_rows = sorted(
            {index.row() for index in self.caption_table.selectionModel().selectedRows()},
            reverse=True,
        )
        # A current row is a useful fallback if selection state is unusual on some Qt builds.
        if not selected_rows and self.caption_table.currentRow() >= 0:
            selected_rows = [self.caption_table.currentRow()]
        if not selected_rows:
            QMessageBox.information(
                self,
                "Nie zaznaczono napisów",
                "Kliknij wiersz napisu, który chcesz usunąć. Możesz zaznaczyć kilka wierszy, używając Ctrl lub Shift.",
            )
            return

        count = len(selected_rows)
        answer = QMessageBox.question(
            self,
            "Usuń zaznaczone napisy",
            f"Czy na pewno usunąć zaznaczone napisy? Liczba wierszy: {count}.\n\n"
            "Aby utrwalić zmianę w plikach SRT/ASS/JSON, kliknij potem „Zapisz poprawki” albo „Zapisz i wypal MP4”.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        for row in selected_rows:
            self.caption_table.removeRow(row)
            if 0 <= row < len(self.caption_row_groups):
                self.caption_row_groups.pop(row)

        if self.caption_table.rowCount() > 0:
            self.caption_table.selectRow(min(selected_rows[-1], self.caption_table.rowCount() - 1))
        if count == 1:
            count_label = "1 napis"
        elif count in (2, 3, 4):
            count_label = f"{count} napisy"
        else:
            count_label = f"{count} napisów"
        self._log(
            f"Usunięto z edytora: {count_label}. Kliknij „Zapisz poprawki” lub „Zapisz i wypal MP4”, "
            "aby zapisać zmiany w plikach wynikowych."
        )

    def load_saved_transcript(self, checked: bool = False, silent: bool = False) -> bool:
        if not self.input_path:
            if not silent:
                QMessageBox.information(self, "Wybierz film", "Najpierw wybierz film, dla którego zapisano napisy.")
            return False
        transcript_path = self._output_dir() / f"{Path(self.input_path).stem}_transkrypcja.json"
        if not transcript_path.is_file():
            if not silent:
                QMessageBox.information(self, "Brak zapisanej transkrypcji", f"Nie znaleziono pliku:\n{transcript_path}\n\nNajpierw wygeneruj napisy AI lub wybierz właściwy folder wynikowy.")
            return False
        try:
            saved = json.loads(transcript_path.read_text(encoding="utf-8"))
            self.segments = saved.get("segments", []) or []
            self.words = saved.get("words", []) or flatten_words(self.segments)
            if not self.words:
                if not silent:
                    QMessageBox.information(self, "Brak tekstu", "Zapisana transkrypcja nie zawiera słów do edycji.")
                return False
            self._populate_caption_editor()
            self._log(f"Wczytano napisy do edycji: {transcript_path}")
            return True
        except Exception as exc:
            if not silent:
                QMessageBox.critical(self, "Nie można wczytać napisów", str(exc))
            else:
                self._log(f"Nie udało się automatycznie wczytać zapisanych napisów: {exc}")
            return False

    def _apply_caption_edits(self, show_message: bool = True) -> bool:
        if not self.input_path:
            if show_message:
                QMessageBox.information(self, "Wybierz film", "Najpierw wybierz film.")
            return False
        if self.caption_table.rowCount() == 0:
            if show_message:
                QMessageBox.information(self, "Brak napisów", "Najpierw wygeneruj napisy AI, wczytaj transkrypcję lub dodaj nowy napis.")
            return False

        updated_words: list[dict[str, Any]] = []
        updated_segments: list[dict[str, Any]] = []
        for row in range(self.caption_table.rowCount()):
            cell = self.caption_table.item(row, 2)
            edited_text = cell.text().strip() if cell else ""
            tokens = edited_text.split()
            # Empty row = remove this caption. This also makes an unused newly-added row harmless.
            if not tokens:
                continue

            try:
                start_item = self.caption_table.item(row, 0)
                end_item = self.caption_table.item(row, 1)
                desired_start = self._parse_editor_time(start_item.text() if start_item else "")
                desired_end = self._parse_editor_time(end_item.text() if end_item else "")
            except ValueError as exc:
                QMessageBox.warning(self, "Nieprawidłowy czas", f"Wiersz {row + 1}: {exc}")
                return False
            if desired_end <= desired_start:
                QMessageBox.warning(self, "Nieprawidłowy przedział", f"Wiersz {row + 1}: czas Koniec musi być późniejszy niż Start.")
                return False

            original_group = self.caption_row_groups[row] if row < len(self.caption_row_groups) else []
            if original_group:
                old_start = min(float(item.get("start", 0.0)) for item in original_group)
                old_end = max(float(item.get("end", old_start + 0.08)) for item in original_group)
                row_words = apply_caption_text_edit(original_group, edited_text)
                if not row_words:
                    continue
                if desired_end - desired_start < max(0.08, 0.04 * len(row_words)):
                    QMessageBox.warning(
                        self, "Za krótki czas",
                        f"Wiersz {row + 1}: przedział jest za krótki dla {len(row_words)} słów. Wydłuż czas wyświetlania."
                    )
                    return False
                old_duration = max(0.001, old_end - old_start)
                new_duration = desired_end - desired_start
                for word in row_words:
                    word_start = float(word.get("start", old_start))
                    word_end = float(word.get("end", old_end))
                    word["start"] = desired_start + (word_start - old_start) / old_duration * new_duration
                    word["end"] = desired_start + (word_end - old_start) / old_duration * new_duration
                    word["start"] = max(desired_start, min(word["start"], desired_end - 0.04))
                    word["end"] = min(desired_end, max(word["start"] + 0.04, word["end"]))
            else:
                try:
                    row_words = self._make_words_for_interval(edited_text, desired_start, desired_end)
                except ValueError as exc:
                    QMessageBox.warning(self, "Za krótki czas", f"Wiersz {row + 1}: {exc}")
                    return False

            # Mark word-to-caption membership so nearby/overlapping subtitles remain separate ASS events.
            for word in row_words:
                word["_caption_group"] = row
            updated_words.extend(row_words)
            updated_segments.append({
                "start": desired_start,
                "end": desired_end,
                "text": " ".join(tokens),
                "words": [dict(word) for word in row_words],
                "_editor_group": True,
            })

        if not updated_words:
            if show_message:
                QMessageBox.warning(self, "Brak tekstu", "Wszystkie wiersze są puste. Wpisz tekst przynajmniej w jednym wierszu.")
            return False

        self.words = sorted(updated_words, key=lambda item: (float(item.get("start", 0.0)), float(item.get("end", 0.0))))
        self.segments = sorted(updated_segments, key=lambda item: (float(item.get("start", 0.0)), float(item.get("end", 0.0))))
        output_dir = self._output_dir()
        stem = Path(self.input_path).stem
        try:
            srt_path = write_srt(self.segments, output_dir / f"{stem}_napisy.srt")
            ass_path = write_ass(self.words, output_dir / f"{stem}_napisy.ass", style=self._style())
            json_path = save_transcript_json(self.segments, self.words, output_dir / f"{stem}_transkrypcja.json")
        except Exception as exc:
            QMessageBox.critical(self, "Nie można zapisać poprawek", str(exc))
            return False
        self._populate_caption_editor()
        self._log(f"Zapisano poprawione napisy i czasy:\nSRT: {srt_path}\nASS: {ass_path}\nTranskrypcja: {json_path}")
        return True

    def save_caption_edits(self) -> None:
        self._apply_caption_edits(show_message=True)

    def save_edits_and_burn(self) -> None:
        # start_burn_subtitles applies the currently edited table and then renders it.
        self.start_burn_subtitles()

    def load_tts_from_editor(self, checked: bool = False, silent: bool = False) -> bool:
        """Copy the current edited caption rows into the editable voice-over table."""
        if self.caption_table.rowCount() == 0:
            loaded = self.load_saved_transcript(silent=True)
            if not loaded and self.input_path and self.words:
                self._populate_caption_editor()
            if self.caption_table.rowCount() == 0:
                if not silent:
                    QMessageBox.information(
                        self, "Brak napisów",
                        "Najpierw wygeneruj polskie napisy AI albo wczytaj zapisane napisy. "
                        "Lektor AI używa tekstu i czasów z edytora napisów."
                    )
                return False

        self.tts_table.setRowCount(0)
        for row in range(self.caption_table.rowCount()):
            start_item = self.caption_table.item(row, 0)
            end_item = self.caption_table.item(row, 1)
            text_item = self.caption_table.item(row, 2)
            if not start_item or not end_item or not text_item or not text_item.text().strip():
                continue
            target_row = self.tts_table.rowCount()
            self.tts_table.insertRow(target_row)
            self.tts_table.setItem(target_row, 0, QTableWidgetItem(start_item.text()))
            self.tts_table.setItem(target_row, 1, QTableWidgetItem(end_item.text()))
            self.tts_table.setItem(target_row, 2, QTableWidgetItem(text_item.text()))
        if self.tts_table.rowCount() > 0:
            first_text_item = self.tts_table.item(0, 2)
            if first_text_item is not None:
                self.tts_table.scrollToItem(
                    first_text_item, QAbstractItemView.ScrollHint.PositionAtTop
                )
        if not silent:
            self._log(f"Wczytano {self.tts_table.rowCount()} fragmentów do zakładki Lektor AI. Możesz edytować tekst i czasy przed generowaniem.")
        return self.tts_table.rowCount() > 0

    def add_tts_row(self) -> None:
        row = self.tts_table.rowCount()
        self.tts_table.insertRow(row)
        self.tts_table.setItem(row, 0, QTableWidgetItem("00:00:00.000"))
        self.tts_table.setItem(row, 1, QTableWidgetItem("00:00:02.000"))
        self.tts_table.setItem(row, 2, QTableWidgetItem("Wpisz tekst, który ma powiedzieć lektor AI"))
        self.tts_table.selectRow(row)
        self.tts_table.setCurrentCell(row, 2)
        # Rows have a fixed height and the table uses its own scrollbar, so new
        # fragments cannot push the footer down or make it overlap START/KONIEC.
        # Force the new fragment into view even when the table already has many rows.
        new_text_item = self.tts_table.item(row, 2)
        if new_text_item is not None:
            self.tts_table.scrollToItem(
                new_text_item, QAbstractItemView.ScrollHint.PositionAtBottom
            )
            self.tts_table.editItem(new_text_item)

    def remove_tts_row(self) -> None:
        row = self.tts_table.currentRow()
        if row >= 0:
            self.tts_table.removeRow(row)
        else:
            QMessageBox.information(self, "Zaznacz fragment", "Kliknij wiersz, który chcesz usunąć.")

    def _read_tts_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in range(self.tts_table.rowCount()):
            text_item = self.tts_table.item(row, 2)
            text = text_item.text().strip() if text_item else ""
            if not text:
                continue
            try:
                start_item = self.tts_table.item(row, 0)
                end_item = self.tts_table.item(row, 1)
                start = self._parse_editor_time(start_item.text() if start_item else "")
                end = self._parse_editor_time(end_item.text() if end_item else "")
            except ValueError as exc:
                raise ValueError(f"Wiersz {row + 1}: {exc}") from exc
            if end <= start:
                raise ValueError(f"Wiersz {row + 1}: Koniec musi być późniejszy niż Start.")
            rows.append({"start": start, "end": end, "text": text})
        if not rows:
            raise ValueError("Tabela lektora AI nie zawiera tekstu. Wczytaj napisy lub dodaj fragment.")
        return sorted(rows, key=lambda item: (item["start"], item["end"]))

    def start_tts_preview(self) -> None:
        voice_key = str(self.tts_voice_combo.currentData())
        style_key = str(self.tts_style_combo.currentData())
        sample_text = "Cześć! To jest próbka polskiego głosu z LocalCut AI. Mówię spokojnie i naturalnie, w zwykłym tempie."
        row = self.tts_table.currentRow()
        if row >= 0:
            item = self.tts_table.item(row, 2)
            if item and item.text().strip():
                sample_text = item.text().strip()
        try:
            output_dir = self._output_dir()
        except Exception as exc:
            QMessageBox.critical(self, "Błąd folderu", str(exc))
            return
        preview_path = output_dir / f"probka_lektora_{voice_key}_{style_key}.wav"

        def task(progress):
            result = generate_voice_preview(voice_key, str(preview_path), sample_text, progress, style_key=style_key)
            return {"kind": "tts_preview", "result": result}

        self._run_task("Przygotowuję próbkę głosu AI…", task, self._handle_result)

    def start_tts_export(self) -> None:
        if not self._ensure_video():
            return
        if self.tts_table.rowCount() == 0:
            if not self.load_tts_from_editor(silent=False):
                return
        try:
            rows = self._read_tts_rows()
        except ValueError as exc:
            QMessageBox.warning(self, "Sprawdź tekst i czasy lektora", str(exc))
            return

        input_path = self.input_path or ""
        output_dir = self._output_dir()
        stem = Path(input_path).stem
        voice_key = str(self.tts_voice_combo.currentData())
        style_key = str(self.tts_style_combo.currentData())
        output_mp4 = output_dir / f"{stem}_lektor_ai.mp4"
        output_wav = output_dir / f"{stem}_lektor_ai.wav"

        def task(progress):
            result = render_voice_replacement(
                input_path, str(output_mp4), str(output_wav), rows, voice_key,
                progress=progress, style_key=style_key,
            )
            return {"kind": "tts_export", "result": result}

        self._run_task("Generuję głos AI i podmieniam audio w filmie…", task, self._handle_result)

    def choose_text_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.text_color), self, "Kolor napisów")
        if color.isValid():
            self.text_color = color.name().upper()
            self.text_color_btn.setText(f"Kolor tekstu: {self.text_color}")
            self.text_color_btn.setStyleSheet(f"border-bottom: 3px solid {self.text_color};")

    def choose_highlight_color(self) -> None:
        color = QColorDialog.getColor(QColor(self.highlight_color), self, "Kolor podświetlanego słowa")
        if color.isValid():
            self.highlight_color = color.name().upper()
            self.highlight_color_btn.setText(f"Podświetlenie: {self.highlight_color}")
            self.highlight_color_btn.setStyleSheet(f"border-bottom: 3px solid {self.highlight_color};")

    def _style(self) -> dict[str, Any]:
        return {
            "font": self.font_combo.currentFont().family(),
            "font_size": int(self.font_size.value()),
            "text_color": self.text_color,
            "highlight_color": self.highlight_color,
            "karaoke": self.karaoke_check.isChecked(),
            "animation": self.animation_combo.currentText(),
            "margin_v": 80,
            "short_margin_v": 170,
        }

    def regenerate_ass(self) -> None:
        if not self.words or not self.input_path:
            QMessageBox.information(self, "Brak napisów", "Najpierw wygeneruj napisy AI.")
            return
        output = self._output_dir() / f"{Path(self.input_path).stem}_napisy.ass"
        try:
            write_ass(self.words, output, style=self._style())
            self._log(f"Zapisano wygląd napisów: {output}")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd zapisu", str(exc))

    def _run_task(self, title: str, function, handler) -> None:
        if self.worker and self.worker.isRunning():
            return
        self._log(title)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        for name in ("caption_btn", "burn_btn", "silence_btn", "moments_btn", "shorts_btn", "load_transcript_btn", "add_caption_btn", "remove_caption_btn", "save_edits_btn", "save_burn_btn", "tts_load_btn", "tts_preview_btn", "tts_add_btn", "tts_remove_btn", "tts_export_btn"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(False)
        self.worker = TaskWorker(function, self)
        self.worker.progress.connect(self._log)
        self.worker.succeeded.connect(handler)
        self.worker.failed.connect(self._task_failed)
        self.worker.finished.connect(self._task_finished)
        self.worker.start()

    def _task_finished(self) -> None:
        self.progress.setVisible(False)
        for name in ("caption_btn", "burn_btn", "silence_btn", "moments_btn", "shorts_btn", "load_transcript_btn", "add_caption_btn", "remove_caption_btn", "save_edits_btn", "save_burn_btn", "tts_load_btn", "tts_preview_btn", "tts_add_btn", "tts_remove_btn", "tts_export_btn"):
            button = getattr(self, name, None)
            if button is not None:
                button.setEnabled(True)
        self.worker = None

    def _task_failed(self, message: str) -> None:
        self._log("BŁĄD: " + message.splitlines()[0])
        self.log.appendPlainText(message)
        QMessageBox.critical(self, "Operacja nie powiodła się", message[:2400])

    def start_transcription(self) -> None:
        if not self._ensure_video():
            return
        input_path = self.input_path or ""
        model_size = str(self.model_combo.currentData())
        output_dir = self._output_dir()

        def task(progress):
            data = transcribe_video(input_path, model_size=model_size, progress=progress)
            return {"kind": "transcription", "data": data, "output_dir": str(output_dir), "input": input_path}

        self._run_task("Start rozpoznawania mowy…", task, self._handle_result)

    def start_burn_subtitles(self) -> None:
        if not self._ensure_video():
            return
        # Always render what is currently visible in the text editor, even if the user
        # did not click the separate save button first.
        if self.caption_row_groups and self.caption_table.rowCount() > 0:
            if not self._apply_caption_edits(show_message=False):
                return
        input_path = self.input_path or ""
        output_dir = self._output_dir()
        stem = Path(input_path).stem

        # The app can also reuse word timings from a previous run, even after it was restarted.
        words = list(self.words)
        if not words:
            transcript_path = output_dir / f"{stem}_transkrypcja.json"
            if transcript_path.is_file():
                try:
                    import json
                    saved = json.loads(transcript_path.read_text(encoding="utf-8"))
                    words = saved.get("words", []) or flatten_words(saved.get("segments", []))
                    self.words = list(words)
                    self.segments = saved.get("segments", [])
                except Exception as exc:
                    QMessageBox.warning(self, "Nie można odczytać transkrypcji", str(exc))
                    return
        if not words:
            QMessageBox.information(self, "Najpierw napisy", "Najpierw wygeneruj napisy AI. Jeżeli robiono to wcześniej, wybierz ten sam folder „Zapis wyników”.")
            return

        style = self._style()
        ass_path = output_dir / f"{stem}_napisy.ass"
        output_path = output_dir / f"{stem}_napisy_animowane.mp4"

        def task(progress):
            duration = probe_duration(input_path)
            write_ass(words, ass_path, style=style, duration=duration)
            result = burn_subtitles(input_path, str(ass_path), str(output_path), progress=progress)
            return {"kind": "burn_subtitles", "result": result}

        self._run_task("Przygotowuję film z wypalonymi napisami…", task, self._handle_result)

    def start_silence_removal(self) -> None:
        if not self._ensure_video():
            return
        input_path = self.input_path or ""
        output_path = self._output_dir() / f"{Path(input_path).stem}_bez_ciszy.mp4"

        def task(progress):
            result = remove_silence(input_path, str(output_path), progress=progress)
            return {"kind": "silence", "result": result}

        self._run_task("Start wykrywania i usuwania ciszy…", task, self._handle_result)

    def start_moment_analysis(self) -> None:
        if not self._ensure_video():
            return
        if not self.words:
            QMessageBox.information(self, "Najpierw napisy", "W pierwszej wersji analiza fragmentów korzysta ze znaczników czasu słów. Najpierw kliknij „Generuj polskie napisy AI”.")
            return
        input_path = self.input_path or ""
        words = list(self.words)

        def task(progress):
            progress("Sprawdzanie długości filmu…")
            duration = probe_duration(input_path)
            progress("Ranking fragmentów według gęstości mowy i interpunkcji…")
            items = suggest_moments(words, duration, target_seconds=35.0, limit=8)
            if not items:
                raise RuntimeError("Za mało rozpoznanej mowy, aby zaproponować fragmenty.")
            return {"kind": "moments", "items": items, "duration": duration}

        self._run_task("Analizuję najlepsze fragmenty…", task, self._handle_result)

    def start_shorts_export(self) -> None:
        if not self._ensure_video():
            return
        if not self.words:
            QMessageBox.information(self, "Najpierw napisy", "Wygeneruj napisy, aby Shortsy mogły dostać podświetlane słowa.")
            return
        selected = self.moments_list.selectedItems()
        candidate_items = [item.data(Qt.ItemDataRole.UserRole) for item in selected] if selected else list(self.candidates[:3])
        if not candidate_items:
            QMessageBox.information(self, "Brak propozycji", "Najpierw kliknij „Znajdź najlepsze fragmenty”.")
            return
        candidate_items = candidate_items[:5]
        input_path = self.input_path or ""
        output_dir = self._output_dir()
        words = list(self.words)
        style = self._style()

        def task(progress):
            results = []
            for index, item in enumerate(candidate_items, 1):
                output = output_dir / f"{Path(input_path).stem}_short_{index:02}.mp4"
                progress(f"Shorts {index}/{len(candidate_items)} — {item['start']:.1f}–{item['end']:.1f} s")
                results.append(create_short(input_path, str(output), item["start"], item["end"], words, style=style, progress=progress))
            return {"kind": "shorts", "results": results}

        self._run_task("Przygotowuję pionowe Shortsy 9:16…", task, self._handle_result)

    def _handle_result(self, result: dict[str, Any]) -> None:
        kind = result.get("kind")
        if kind == "transcription":
            data = result["data"]
            self.segments = data["segments"]
            self.words = data["words"] or flatten_words(self.segments)
            self._populate_caption_editor()
            self.load_tts_from_editor(silent=True)
            out = Path(result["output_dir"])
            stem = Path(result["input"]).stem
            srt = write_srt(self.segments, out / f"{stem}_napisy.srt")
            ass = write_ass(self.words, out / f"{stem}_napisy.ass", style=self._style())
            js = save_transcript_json(self.segments, self.words, out / f"{stem}_transkrypcja.json")
            self._log(f"Gotowe. Urządzenie: {data['device']}; rozpoznano {len(self.words)} słów.")
            self._log(f"SRT: {srt}\nASS (podświetlanie): {ass}\nTranskrypcja JSON: {js}")
            self._log("Sprawdź tekst przed publikacją — rozpoznawanie mowy może popełniać błędy, zwłaszcza przy muzyce lub kilku rozmówcach.")
        elif kind == "burn_subtitles":
            item = result["result"]
            self._log(f"{item['message']}\nMP4 do importu w DaVinci Resolve: {item['path']}\nPlik źródłowy ASS: {item['ass_path']}")
        elif kind == "silence":
            item = result["result"]
            self._log(f"{item['message']} Plik: {item['path']}")
        elif kind == "moments":
            self.candidates = result["items"]
            self.video_duration = result["duration"]
            self.moments_list.clear()
            for index, item in enumerate(self.candidates, 1):
                label = f"{index}. {self._fmt_time(item['start'])} – {self._fmt_time(item['end'])}  |  wynik {item['score']:.1f}  |  {item['reason']}"
                row = QListWidgetItem(label)
                row.setData(Qt.ItemDataRole.UserRole, item)
                self.moments_list.addItem(row)
            self._log(f"Znaleziono {len(self.candidates)} propozycji. Zaznacz wybrane i kliknij „Utwórz pionowe Shortsy”.")
        elif kind == "shorts":
            self._log(f"Utworzono {len(result['results'])} Shortsów:")
            for item in result["results"]:
                subnote = "napisy wypalone w filmie" if item["burned_subtitles"] else "napisy .ASS zapisane obok filmu"
                self._log(f"• {item['path']} ({subnote})")
        elif kind == "tts_preview":
            item = result["result"]
            style_label = item.get("style", "")
            self._log(f"Gotowa próbka głosu: {item['voice']}\nStyl: {style_label}\n{item['path']}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(item["path"]).resolve())))
        elif kind == "tts_export":
            item = result["result"]
            style_label = item.get("style", "")
            self._log(f"{item['message']}\nGłos: {item['voice']}\nStyl: {style_label}\nMP4: {item['path']}\nŚcieżka WAV: {item['wav_path']}")

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        seconds = max(0, int(seconds))
        return f"{seconds // 60:02}:{seconds % 60:02}"


def main() -> None:
    app = QApplication([])
    app.setApplicationName("LocalCut AI")
    app_asset_dir = Path(__file__).resolve().parent / "assets"
    app_icon_path = app_asset_dir / "LocalCutAI.ico"
    if app_icon_path.is_file():
        app.setWindowIcon(QIcon(str(app_icon_path)))
    window = MainWindow()
    # Maximizing on launch gives the table and its fixed footer enough room on
    # common Windows displays, including when display scaling is enabled.
    window.showMaximized()
    app.exec()
