#! python3.12
import importlib.util
import os
import queue
import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QSize, QTimer, Qt
from PySide6.QtGui import QIcon, QPixmap, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_DIR = Path(__file__).resolve().parent
ENGINE_PATH = APP_DIR / "UltimateScraperProv2.0.py"


def load_engine():
    spec = importlib.util.spec_from_file_location("ultimate_scraper_engine", ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load scraper engine: {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


engine = load_engine()


MEDIA_LABELS = {
    "box2d": "2D Box",
    "box3d": "3D Box",
    "boxback": "Box Back",
    "boxside": "Box Side",
    "screenshot": "Screenshot",
    "screenshottitle": "Title Screenshot",
    "logo": "Logo / Wheel",
    "marquee": "Marquee",
    "fanart": "Fanart",
    "cartridge": "Cartridge",
    "mix": "Mix",
    "video": "Videos",
    "manual": "Manuals",
}

PATTERN_LABELS = {
    "box2d": "2D box pattern",
    "box3d": "3D box pattern",
    "boxback": "Back box pattern",
    "boxside": "Side/spine pattern",
    "screenshot": "Screenshot pattern",
    "screenshottitle": "Title screenshot pattern",
    "logo": "Logo / wheel pattern",
    "marquee": "Marquee pattern",
    "fanart": "Fanart pattern",
    "cartridge": "Cartridge pattern",
    "mix": "Mix pattern",
    "video": "Videos pattern",
    "manual": "Manual pattern",
}

ROM_EXTENSIONS = {
    ".zip", ".7z", ".rar", ".adf", ".uae", ".ipf", ".dms", ".adz", ".lha", ".rp9",
    ".hdf", ".iso", ".cue", ".bin", ".img", ".mdf", ".nrg", ".mds", ".chd", ".cdi",
    ".gdi", ".wbfs", ".rvz", ".gcz", ".nes", ".fds", ".unf", ".psvita", ".vpk",
    ".smc", ".sfc", ".swc", ".wsc", ".n64", ".z64", ".v64", ".ndd", ".wasm",
    ".gcm", ".min", ".vb", ".vboy", ".wad", ".ciso", ".wia", ".json", ".nsp",
    ".xci", ".ws", ".ccc", ".cpc", ".wud", ".wux", ".wua", ".rpx", ".gb", ".gbc",
    ".easyrpg", ".lbd", ".squashfs", ".gba", ".agb", ".cpr", ".nds", ".dsi",
    ".ps4", ".3ds", ".3dsx", ".cia", ".mgw", ".ngp", ".ngc", ".nso", ".nro",
    ".nca", ".kip", ".pbp", ".cso", ".v32", ".st", ".fig", ".bs", ".md", ".smd",
    ".gen", ".gg", ".sv", ".32x", ".vec", ".gam", ".sms", ".rpk", ".exe", ".bat",
    ".cmd", ".lnk", ".game", ".url", ".pc", ".win", ".windows", ".wine",
    ".wsquashfs", ".a26", ".a52", ".a78", ".tic", ".atr", ".xex", ".msa", ".stx",
    ".gemdos", ".j64", ".lnx", ".pak", ".cas", ".fd", ".sap", ".k7", ".m7",
    ".m5", ".qd", ".rom", ".daphne", ".ssd", ".prg", ".col", ".m3u", ".tap",
    ".d64", ".fba", ".wav", ".dmk", ".jvc", ".os9", ".vdk", ".t77", ".mfi",
    ".dfi", ".hfe", ".mfm", ".td0", ".imd", ".d77", ".d88", ".1dd", ".cqm",
    ".cqi", ".d98", ".98d", ".fdi", ".fdd", ".2hd", ".tfd", ".88d", ".hdm",
    ".xdf", ".dup", ".hdi", ".thd", ".nhd", ".hdd", ".hdn", ".pce", ".ccd",
    ".toc", ".dsk", ".tzx", ".z80", ".rzx", ".scl", ".trd", ".p", ".tgc",
    ".ri", ".mx1", ".mx2", ".ogv", ".sg", ".sc", ".p8", ".ngage", ".symbian",
    ".id", ".u88", ".a0", ".b0", ".crt", ".b64", ".d81", ".dim",
}


class SystemCard(QFrame):
    def __init__(self, system, pixmap, accent, on_clicked):
        super().__init__()
        self.system = system
        self.on_clicked = on_clicked
        self.accent = accent
        self.setObjectName("SystemCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumSize(210, 126)
        self.setMaximumHeight(142)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_bar = QFrame()
        accent_bar.setFixedWidth(6)
        accent_bar.setStyleSheet(f"background: {accent}; border-radius: 3px;")
        outer.addWidget(accent_bar)

        content = QWidget()
        content.setObjectName("SystemCardContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        outer.addWidget(content, 1)

        logo = QLabel()
        logo.setObjectName("SystemLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedHeight(60)
        if pixmap and not pixmap.isNull():
            logo.setPixmap(pixmap.scaled(150, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo.setText(system["name"][:2].upper())
            logo.setObjectName("FallbackSystemLogo")
        layout.addWidget(logo)

        name = QLabel(system["name"])
        name.setObjectName("SystemCardTitle")
        name.setAlignment(Qt.AlignCenter)
        name.setWordWrap(True)
        layout.addWidget(name)

        count = QLabel(f"{system['rom_count']} games")
        count.setObjectName("SystemCardMeta")
        count.setAlignment(Qt.AlignCenter)
        layout.addWidget(count)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.on_clicked(self.system)
        super().mousePressEvent(event)


class ScraperQtWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = engine.load_config()
        self.log_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.stop_flag = {"stop": False}
        self.metadata_cache = {}
        self.stats_lock = threading.Lock()
        self.stats = {
            "total_roms": 0,
            "processed": 0,
            "downloaded": 0,
            "skipped": 0,
            "no_media": 0,
            "errors": 0,
        }
        self.worker_thread = None
        self.detected_systems = []
        self.filtered_systems = []
        self.run_started_at = None

        self.setWindowTitle("Ultimate Scraper pro")
        icon_path = APP_DIR / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self._build_ui()
        self._fit_to_available_screen()
        self._load_from_config()
        self._apply_styles()
        if self.base_roms_folder.text().strip() and os.path.isdir(self.base_roms_folder.text().strip()):
            QTimer.singleShot(250, self._scan_systems)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll_queues)
        self.poll_timer.start(150)

    def _fit_to_available_screen(self):
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(1180, 760)
            return
        available = screen.availableGeometry()
        self.showNormal()
        margin = 8
        width = min(1180, max(960, available.width() - margin))
        top_gap = 48
        bottom_gap = 10
        height = min(1000, max(860, available.height() - top_gap - bottom_gap))
        self.setMinimumSize(1060, 800)
        self.setMaximumHeight(max(860, available.height() - 4))
        x = available.x() + max(8, (available.width() - width) // 2)
        y = available.y() + top_gap
        self.setGeometry(x, y, width, height)

    def _build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 14, 18, 14)
        header_layout.setSpacing(16)

        icon = QLabel()
        icon.setFixedSize(112, 112)
        icon.setAlignment(Qt.AlignCenter)
        icon_path = APP_DIR / "Gamersicon.png"
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path)).scaled(104, 104, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon.setPixmap(pixmap)
        else:
            icon.setText("US")
            icon.setObjectName("FallbackIcon")
        header_layout.addWidget(icon)

        title_box = QVBoxLayout()
        title = QLabel("Ultimate Scraper pro")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Artwork, videos, metadata, and gamelist.xml builder")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)
        header_layout.addStretch()

        self.dark_mode = QCheckBox("Dark mode")
        self.dark_mode.setChecked(bool(self.cfg.get("dark_mode", True)))
        self.dark_mode.toggled.connect(self._apply_styles)
        header_layout.addWidget(self.dark_mode)
        root_layout.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_systems_tab(), "Systems")
        self.tabs.addTab(self._build_scrape_tab(), "Scrape")
        self.tabs.addTab(self._build_layout_tab(), "Layout")
        self.tabs.addTab(self._build_about_tab(), "About")
        root_layout.addWidget(self.tabs, 1)

        self.setCentralWidget(root)

    def _build_systems_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        top = QFrame()
        top.setObjectName("ControlsBar")
        top_layout = QHBoxLayout(top)
        top_layout.setContentsMargins(12, 10, 12, 10)
        top_layout.addWidget(QLabel("All ROMs folder"))

        self.base_roms_folder = QLineEdit()
        self.base_roms_folder.setPlaceholderText("Choose the folder that contains your console folders")
        top_layout.addWidget(self.base_roms_folder, 1)
        top_layout.addWidget(self._browse_button(self.base_roms_folder, folders=True))

        self.scan_btn = QPushButton("Scan Systems")
        self.scan_btn.setObjectName("PrimaryButton")
        self.scan_btn.clicked.connect(self._scan_systems)
        top_layout.addWidget(self.scan_btn)
        layout.addWidget(top)

        self.systems_status = QLabel("Pick your all-ROMs folder, then scan. Console cards will load here.")
        self.systems_status.setObjectName("MutedLabel")
        layout.addWidget(self.systems_status)

        filter_bar = QFrame()
        filter_bar.setObjectName("ControlsBar")
        filter_layout = QHBoxLayout(filter_bar)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.addWidget(QLabel("Filter systems"))
        self.system_filter = QLineEdit()
        self.system_filter.setPlaceholderText("Type a console name, folder, or system id")
        self.system_filter.textChanged.connect(self._display_system_cards)
        filter_layout.addWidget(self.system_filter, 1)
        self.clear_filter_btn = QPushButton("Clear")
        self.clear_filter_btn.clicked.connect(self.system_filter.clear)
        filter_layout.addWidget(self.clear_filter_btn)
        layout.addWidget(filter_bar)

        self.systems_scroll = QScrollArea()
        self.systems_scroll.setWidgetResizable(True)
        self.systems_scroll.setObjectName("SystemsScroll")
        self.systems_content = QWidget()
        self.systems_grid = QGridLayout(self.systems_content)
        self.systems_grid.setContentsMargins(8, 8, 8, 8)
        self.systems_grid.setHorizontalSpacing(14)
        self.systems_grid.setVerticalSpacing(14)
        self.systems_scroll.setWidget(self.systems_content)
        layout.addWidget(self.systems_scroll, 1)
        return tab

    def _build_scrape_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        account = QGroupBox("Accounts")
        account_grid = QGridLayout(account)
        account_grid.setHorizontalSpacing(12)
        account_grid.setVerticalSpacing(10)

        self.ssid = QLineEdit()
        self.sspassword = QLineEdit()
        self.sspassword.setEchoMode(QLineEdit.Password)
        self.show_password = QCheckBox("Show")
        self.show_password.toggled.connect(self._toggle_passwords)
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.setObjectName("PrimaryButton")
        self.validate_btn.clicked.connect(self._validate_account)

        account_grid.addWidget(QLabel("ScreenScraper user"), 0, 0)
        account_grid.addWidget(self.ssid, 0, 1)
        account_grid.addWidget(QLabel("Password"), 0, 2)
        account_grid.addWidget(self.sspassword, 0, 3)
        account_grid.addWidget(self.show_password, 0, 4)
        account_grid.addWidget(self.validate_btn, 0, 5)

        self.account_status = QLabel("Threads are detected after validation.")
        self.account_status.setObjectName("MutedLabel")
        self.account_status.setWordWrap(True)
        account_grid.addWidget(self.account_status, 1, 0, 1, 6)

        self.emu_user = QLineEdit()
        self.emu_pass = QLineEdit()
        self.emu_pass.setEchoMode(QLineEdit.Password)
        account_grid.addWidget(QLabel("EmuMovies user"), 2, 0)
        account_grid.addWidget(self.emu_user, 2, 1)
        account_grid.addWidget(QLabel("EmuMovies pass"), 2, 2)
        account_grid.addWidget(self.emu_pass, 2, 3)
        layout.addWidget(account)

        paths = QGroupBox("ROMs and System")
        form = QGridLayout(paths)
        form.setHorizontalSpacing(10)
        form.setVerticalSpacing(10)

        self.rom_folder = QLineEdit()
        self.output_folder = QLineEdit()
        self.system_id = QLineEdit()
        self.system_name = QLineEdit()
        self.frontend = QComboBox()
        self.frontend.addItems(["retrobat", "launchbox"])
        self.launchbox_path = QLineEdit()

        form.addWidget(QLabel("ROM folder"), 0, 0)
        form.addWidget(self.rom_folder, 0, 1)
        form.addWidget(
            self._browse_button(self.rom_folder, folders=True, after_browse=self._on_rom_folder_selected),
            0,
            2,
        )
        form.addWidget(QLabel("Output folder"), 1, 0)
        form.addWidget(self.output_folder, 1, 1)
        form.addWidget(self._browse_button(self.output_folder, folders=True), 1, 2)
        form.addWidget(QLabel("System ID"), 2, 0)
        form.addWidget(self.system_id, 2, 1)
        form.addWidget(QLabel("System short name"), 3, 0)
        form.addWidget(self.system_name, 3, 1)
        form.addWidget(QLabel("Frontend"), 4, 0)
        form.addWidget(self.frontend, 4, 1)
        form.addWidget(QLabel("LaunchBox path"), 5, 0)
        form.addWidget(self.launchbox_path, 5, 1)
        form.addWidget(self._browse_button(self.launchbox_path, folders=True), 5, 2)
        layout.addWidget(paths)

        controls = QFrame()
        controls.setObjectName("ControlsBar")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(12, 10, 12, 10)

        self.start_btn = QPushButton("Start Scraping")
        self.start_btn.setObjectName("PrimaryButton")
        self.start_btn.clicked.connect(self._start_scraping)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_scraping)
        self.test_one_btn = QPushButton("Test 1 ROM...")
        self.test_one_btn.clicked.connect(self._test_single_rom)
        self.build_gamelist_btn = QPushButton("Build gamelist.xml")
        self.build_gamelist_btn.clicked.connect(self._build_gamelist_only)
        self.open_output_btn = QPushButton("Open Output")
        self.open_output_btn.clicked.connect(self._open_output_folder)
        self.gamelist = QCheckBox("Generate gamelist.xml")
        self.threads = QSpinBox()
        self.threads.setRange(1, 10)
        self.threads.setValue(int(self.cfg.get("max_threads", 1)))

        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.test_one_btn)
        controls_layout.addWidget(self.build_gamelist_btn)
        controls_layout.addWidget(self.open_output_btn)
        controls_layout.addWidget(self.gamelist)
        controls_layout.addStretch()
        controls_layout.addWidget(QLabel("Threads"))
        controls_layout.addWidget(self.threads)
        layout.addWidget(controls)

        progress_row = QHBoxLayout()
        self.progress_label = QLabel("Progress: 0% (0/0)")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_row.addWidget(self.progress_label)
        progress_row.addWidget(self.progress_bar, 1)
        layout.addLayout(progress_row)

        self.stats_label = QLabel("ROMs: 0/0 | Downloaded: 0 | Skipped: 0 | No media: 0 | Errors: 0")
        self.stats_label.setObjectName("MutedLabel")
        layout.addWidget(self.stats_label)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setObjectName("LogBox")
        log_tools = QHBoxLayout()
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.log.clear)
        self.copy_log_btn = QPushButton("Copy Log")
        self.copy_log_btn.clicked.connect(self._copy_log)
        log_tools.addStretch()
        log_tools.addWidget(self.clear_log_btn)
        log_tools.addWidget(self.copy_log_btn)
        layout.addLayout(log_tools)
        layout.addWidget(self.log, 1)
        return tab

    def _build_layout_tab(self):
        tab = QWidget()
        outer = QVBoxLayout(tab)
        outer.setSpacing(12)

        presets = QGroupBox("Output Layout")
        presets_layout = QVBoxLayout(presets)
        preset_row = QHBoxLayout()
        self.preset = QComboBox()
        self.preset.addItems(list(engine.OUTPUT_PRESETS.keys()))
        self.preset.currentTextChanged.connect(self._apply_preset_to_fields)
        self.preset_description = QLabel("")
        self.preset_description.setObjectName("MutedLabel")
        preset_row.addWidget(QLabel("Preset"))
        preset_row.addWidget(self.preset)
        preset_row.addWidget(self.preset_description, 1)
        presets_layout.addLayout(preset_row)
        outer.addWidget(presets)

        pattern_group = QGroupBox("Filename Patterns")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        pattern_widget = QWidget()
        pattern_form = QFormLayout(pattern_widget)
        pattern_form.setSpacing(10)
        self.pattern_fields = {}
        for key, label in PATTERN_LABELS.items():
            field = QLineEdit()
            self.pattern_fields[key] = field
            pattern_form.addRow(label, field)
        scroll.setWidget(pattern_widget)
        pattern_layout = QVBoxLayout(pattern_group)
        pattern_layout.addWidget(scroll)
        outer.addWidget(pattern_group, 1)

        toggles = QGroupBox("Media Toggles")
        toggles_grid = QGridLayout(toggles)
        self.media_toggles = {}
        for idx, (key, label) in enumerate(MEDIA_LABELS.items()):
            cb = QCheckBox(label)
            self.media_toggles[key] = cb
            toggles_grid.addWidget(cb, idx // 4, idx % 4)
        media_buttons = QHBoxLayout()
        select_all = QPushButton("Select All Media")
        select_all.clicked.connect(lambda: self._set_all_media(True))
        select_none = QPushButton("Select None")
        select_none.clicked.connect(lambda: self._set_all_media(False))
        media_buttons.addStretch()
        media_buttons.addWidget(select_all)
        media_buttons.addWidget(select_none)
        toggles_grid.addLayout(media_buttons, 4, 0, 1, 4)
        outer.addWidget(toggles)
        return tab

    def _build_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setObjectName("AboutBox")
        text.setText(
            "Ultimate Scraper pro Studio 1.2.0\n\n"
            "Qt front end for the existing scraper engine.\n\n"
            "Set your ScreenScraper account, choose ROM and output folders, "
            "pick a layout preset, choose media types, then start scraping.\n\n"
            "ScreenScraper developer credentials stay on the relay server. Enter your own ScreenScraper login in Accounts. Optional EmuMovies access requires your own API key in the EMUMOVIES_API_KEY environment variable."
        )
        layout.addWidget(text)
        return tab

    def _browse_button(self, target, folders=False, after_browse=None):
        btn = QPushButton("Browse")

        def browse():
            if folders:
                value = QFileDialog.getExistingDirectory(self, "Select folder", target.text() or str(APP_DIR))
            else:
                value, _ = QFileDialog.getOpenFileName(self, "Select file", target.text() or str(APP_DIR))
            if value:
                target.setText(value)
                if after_browse:
                    after_browse(value)

        btn.clicked.connect(browse)
        return btn

    def _on_rom_folder_selected(self, folder_path):
        self.output_folder.setText(folder_path)
        info = self._autofill_system_from_folder(folder_path, force=True)
        self._save_to_config()
        if info and hasattr(self, "log"):
            self.log.append(f"[SYSTEM] Loaded {info.get('name', os.path.basename(folder_path))}")
            self.log.append(f"[SYSTEM] Folder: {folder_path}")

    def _load_from_config(self):
        self.base_roms_folder.setText(self.cfg.get("base_roms_folder", ""))
        self.ssid.setText(self.cfg.get("ssid", ""))
        self.sspassword.setText(self.cfg.get("sspassword", ""))
        self.emu_user.setText(self.cfg.get("emumovies_user", ""))
        self.emu_pass.setText(self.cfg.get("emumovies_pass", ""))
        self.rom_folder.setText(self.cfg.get("rom_folder", ""))
        self.output_folder.setText(self.cfg.get("output_folder", ""))
        self.system_id.setText(self.cfg.get("system_id", ""))
        self.system_name.setText(self.cfg.get("system_name", ""))
        self.launchbox_path.setText(self.cfg.get("launchbox_path", ""))
        self.gamelist.setChecked(bool(self.cfg.get("generate_gamelist", True)))
        self.frontend.setCurrentText(self.cfg.get("frontend", "retrobat"))
        self.preset.setCurrentText(self.cfg.get("output_preset", "RetroBat-style"))
        self._apply_preset_to_fields()

        media = engine.DEFAULT_MEDIA_TOGGLES.copy()
        media.update(self.cfg.get("media_toggles", {}))
        for key, checkbox in self.media_toggles.items():
            checkbox.setChecked(bool(media.get(key, True)))

    def _save_to_config(self):
        self.cfg["base_roms_folder"] = self.base_roms_folder.text().strip()
        self.cfg["ssid"] = self.ssid.text().strip()
        self.cfg["sspassword"] = self.sspassword.text()
        self.cfg["emumovies_user"] = self.emu_user.text().strip()
        self.cfg["emumovies_pass"] = self.emu_pass.text()
        self.cfg["rom_folder"] = self.rom_folder.text().strip()
        self.cfg["output_folder"] = self.output_folder.text().strip()
        self.cfg["system_id"] = self.system_id.text().strip()
        self.cfg["system_name"] = self.system_name.text().strip()
        self.cfg["launchbox_path"] = self.launchbox_path.text().strip()
        self.cfg["frontend"] = self.frontend.currentText()
        self.cfg["output_preset"] = self.preset.currentText()
        self.cfg["generate_gamelist"] = self.gamelist.isChecked()
        self.cfg["max_threads"] = self.threads.value()
        self.cfg["media_toggles"] = {key: cb.isChecked() for key, cb in self.media_toggles.items()}
        self.cfg["dark_mode"] = self.dark_mode.isChecked()
        if self.preset.currentText() == "Custom":
            self.cfg["custom_patterns"] = self._patterns_from_fields()
        engine.save_config(self.cfg)

    def _scan_systems(self):
        base_folder = self.base_roms_folder.text().strip()
        if not base_folder or not os.path.isdir(base_folder):
            QMessageBox.warning(self, "Invalid folder", "Choose the all-ROMs folder first.")
            return
        self._save_to_config()
        self.scan_btn.setEnabled(False)
        self.systems_status.setText("Scanning for console folders...")
        self._clear_system_cards()

        def scan():
            detected = []
            error = None
            try:
                for entry in sorted(os.listdir(base_folder)):
                    full_path = os.path.join(base_folder, entry)
                    if not os.path.isdir(full_path):
                        continue
                    system_info = engine.get_system_info(entry)
                    if not system_info:
                        continue
                    rom_count = self._count_roms_in_folder(full_path)
                    if rom_count <= 0:
                        continue
                    system_info["path"] = full_path
                    system_info["rom_count"] = rom_count
                    detected.append(system_info)
            except Exception as exc:
                error = str(exc)
            self.log_queue.put(("systems", detected, error))

        threading.Thread(target=scan, daemon=True).start()

    def _finish_system_scan(self, detected, error=None):
        self.scan_btn.setEnabled(True)
        if error:
            self.systems_status.setText("Scan failed.")
            QMessageBox.critical(self, "Scan Error", f"Failed to scan folder:\n{error}")
            return
        self.detected_systems = detected
        self._display_system_cards()
        if hasattr(self, "log"):
            self.log.append(f"[SCAN] Found {len(detected)} systems with ROMs.")

    def _count_roms_in_folder(self, folder_path):
        count = 0
        try:
            for root, _dirs, files in os.walk(folder_path):
                for name in files:
                    if os.path.splitext(name)[1].lower() in ROM_EXTENSIONS:
                        count += 1
        except Exception:
            return count
        return count

    def _clear_system_cards(self):
        while self.systems_grid.count():
            item = self.systems_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _display_system_cards(self):
        self._clear_system_cards()
        term = self.system_filter.text().strip().lower() if hasattr(self, "system_filter") else ""
        if term:
            systems = [
                system for system in self.detected_systems
                if term in str(system.get("name", "")).lower()
                or term in str(system.get("folder", "")).lower()
                or term in str(system.get("id", "")).lower()
            ]
        else:
            systems = list(self.detected_systems)
        self.filtered_systems = systems

        if not systems:
            empty = QLabel("No console folders with ROMs were found.")
            empty.setObjectName("MutedLabel")
            empty.setAlignment(Qt.AlignCenter)
            self.systems_grid.addWidget(empty, 0, 0)
            if self.detected_systems:
                self.systems_status.setText(f"No systems match '{term}'.")
            else:
                self.systems_status.setText("No console folders with ROMs were found.")
            return

        columns = 4
        for index, system in enumerate(systems):
            accent = engine.get_brand_info(system.get("id", "0")).get("color", "#ff7a2d")
            pixmap = self._system_logo_pixmap(system)
            card = SystemCard(system, pixmap, accent, self._load_system)
            self.systems_grid.addWidget(card, index // columns, index % columns)
        for col in range(columns):
            self.systems_grid.setColumnStretch(col, 1)
        if term:
            self.systems_status.setText(f"Showing {len(systems)} of {len(self.detected_systems)} systems.")
        else:
            self.systems_status.setText(f"Found {len(systems)} console folders with ROMs.")

    def _system_logo_pixmap(self, system):
        logo_dir = APP_DIR / "console_logos"
        folder = str(system.get("folder", "")).lower()
        candidates = []
        icon_name = system.get("icon")
        if icon_name:
            candidates.append(icon_name)
        if folder:
            for ext in (".png", ".jpg", ".jpeg", ".svg"):
                candidates.append(f"{folder}{ext}")
        mapped = engine.SYSTEM_TO_LOGO.get(str(system.get("id", "")))
        if mapped:
            for ext in (".png", ".jpg", ".jpeg", ".svg"):
                candidates.append(f"{mapped}{ext}")
        candidates.extend(["mame.png", "arcade.png"])

        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            path = logo_dir / candidate
            if path.exists():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    return pixmap
        return QPixmap()

    def _load_system(self, system):
        self.stop_flag["stop"] = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.rom_folder.setText(system["path"])
        self.output_folder.setText(system["path"])
        self.system_id.setText(str(system.get("id", "")))
        self.system_name.setText(system.get("name", ""))
        self._save_to_config()
        self.tabs.setCurrentIndex(1)
        self.log.append(f"[SYSTEM] Loaded {system['name']} ({system['rom_count']} ROMs)")
        self.log.append(f"[SYSTEM] Folder: {system['path']}")

    def _patterns_from_fields(self):
        return {key: field.text().strip() for key, field in self.pattern_fields.items()}

    def _enabled_media_keys(self):
        return [key for key, cb in self.media_toggles.items() if cb.isChecked()]

    def _set_all_media(self, enabled):
        for checkbox in self.media_toggles.values():
            checkbox.setChecked(enabled)
        self._save_to_config()

    def _open_output_folder(self):
        output_folder = self.output_folder.text().strip() or self.rom_folder.text().strip()
        if not output_folder or not os.path.isdir(output_folder):
            QMessageBox.warning(self, "Missing output folder", "Choose a valid output folder first.")
            return
        try:
            os.startfile(output_folder)
        except Exception as exc:
            QMessageBox.critical(self, "Open Folder Error", str(exc))

    def _copy_log(self):
        QApplication.clipboard().setText(self.log.toPlainText())
        self.log.append("[LOG] Copied log to clipboard.")

    def _apply_preset_to_fields(self):
        preset_name = self.preset.currentText() if hasattr(self, "preset") else "RetroBat-style"
        preset = engine.OUTPUT_PRESETS.get(preset_name, engine.OUTPUT_PRESETS["RetroBat-style"])
        self.preset_description.setText(preset.get("description", ""))
        if preset_name == "Custom":
            patterns = self.cfg.get("custom_patterns", engine.OUTPUT_PRESETS["Custom"]["patterns"])
        else:
            patterns = preset.get("patterns", {})
        for key, field in self.pattern_fields.items():
            value = patterns.get(key, "")
            if key == "video" and not value:
                value = patterns.get("videos", "")
            field.setText(value)

    def _toggle_passwords(self, checked):
        mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.sspassword.setEchoMode(mode)
        self.emu_pass.setEchoMode(mode)

    def _validate_account(self):
        self._save_to_config()
        self.validate_btn.setEnabled(False)
        self.account_status.setText("Validating account...")

        def worker():
            info = engine.fetch_screenscraper_user_info(self.cfg)
            self.log_queue.put(("account", info))

        threading.Thread(target=worker, daemon=True).start()

    def _start_scraping(self):
        self._start_scraping_common()

    def _test_single_rom(self):
        initial_dir = self.rom_folder.text().strip() or self.base_roms_folder.text().strip() or str(APP_DIR)
        file_path, _ = QFileDialog.getOpenFileName(self, "Select a ROM to test", initial_dir)
        if not file_path:
            return
        rom_folder = os.path.dirname(file_path)
        rom_filename = os.path.basename(file_path)
        self.rom_folder.setText(rom_folder)
        if not self.output_folder.text().strip():
            self.output_folder.setText(rom_folder)
        self._autofill_system_from_folder(rom_folder)
        self._start_scraping_common(single_rom=rom_filename, do_gamelist=False, label=f"[TEST] {rom_filename}")

    def _build_gamelist_only(self):
        self._save_to_config()
        rom_folder = self.rom_folder.text().strip()
        output_folder = self.output_folder.text().strip()
        if not rom_folder or not os.path.isdir(rom_folder):
            QMessageBox.warning(self, "Missing ROM folder", "Choose a valid ROM folder first.")
            return
        if not output_folder:
            QMessageBox.warning(self, "Missing output folder", "Choose an output folder first.")
            return
        self._autofill_system_from_folder(rom_folder)
        self.log.append("[GAMELIST] Building gamelist.xml...")
        try:
            engine.generate_gamelist_xml(
                self.cfg,
                rom_folder,
                output_folder,
                self.system_id.text().strip(),
                self.system_name.text().strip(),
                self._patterns_from_fields(),
                log_queue=self.log_queue,
                metadata_cache=self.metadata_cache,
            )
            self.log.append("[GAMELIST] Done.")
        except Exception as exc:
            QMessageBox.critical(self, "gamelist.xml error", str(exc))

    def _autofill_system_from_folder(self, folder_path, force=False):
        folder_name = os.path.basename(os.path.normpath(folder_path))
        info = engine.get_system_info(folder_name)
        if info:
            if force or not self.system_id.text().strip() or self.system_id.text().strip() == "0":
                self.system_id.setText(str(info.get("id", "")))
            if force or not self.system_name.text().strip():
                self.system_name.setText(info.get("name", folder_name))
        return info

    def _set_busy(self, busy):
        self.start_btn.setEnabled(not busy)
        self.test_one_btn.setEnabled(not busy)
        self.build_gamelist_btn.setEnabled(not busy)
        self.open_output_btn.setEnabled(not busy)
        self.scan_btn.setEnabled(not busy)
        self.validate_btn.setEnabled(not busy)
        self.stop_btn.setEnabled(busy)

    def _start_scraping_common(self, single_rom=None, do_gamelist=True, label="[START] Scraping started."):
        if self.worker_thread and self.worker_thread.is_alive():
            return
        self._save_to_config()
        rom_folder = self.rom_folder.text().strip()
        output_folder = self.output_folder.text().strip()
        if not rom_folder or not os.path.isdir(rom_folder):
            QMessageBox.warning(self, "Missing ROM folder", "Choose a valid ROM folder first.")
            return
        if not output_folder:
            QMessageBox.warning(self, "Missing output folder", "Choose an output folder first.")
            return

        self._autofill_system_from_folder(rom_folder)
        self.stop_flag["stop"] = False
        self.run_started_at = time.time()
        self._set_busy(True)
        with self.stats_lock:
            self.stats["total_roms"] = 0
            self.stats["processed"] = 0
            self.stats["downloaded"] = 0
            self.stats["skipped"] = 0
            self.stats["no_media"] = 0
            self.stats["errors"] = 0
        self._update_stats()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Progress: 0% (0/0)")
        self.log.append(label)

        run_config = dict(self.cfg)
        requested_threads = self.threads.value()

        def run():
            try:
                account = engine.fetch_screenscraper_user_info(run_config)
                if not account:
                    self.log_queue.put("[ERROR] " + run_config.get("_screenscraper_error", "Account validation failed.") + "\n")
                    return
                self.log_queue.put(("account", account))
                engine.scrape_worker(
                    run_config,
                    rom_folder,
                    output_folder,
                    self.system_id.text().strip(),
                    self.system_name.text().strip(),
                    self.preset.currentText(),
                    self._patterns_from_fields(),
                    self.log_queue,
                    self.progress_queue,
                    self.stop_flag,
                    min(requested_threads, account["maxthreads"]),
                    metadata_cache=self.metadata_cache,
                    enabled_media_keys=self._enabled_media_keys(),
                    stats=self.stats,
                    stats_lock=self.stats_lock,
                    single_rom=single_rom,
                )
                if do_gamelist and self.gamelist.isChecked() and not self.stop_flag["stop"]:
                    engine.generate_gamelist_xml(
                        self.cfg,
                        rom_folder,
                        output_folder,
                        self.system_id.text().strip(),
                        self.system_name.text().strip(),
                        self._patterns_from_fields(),
                        log_queue=self.log_queue,
                        metadata_cache=self.metadata_cache,
                    )
            except Exception as exc:
                self.log_queue.put(f"[ERROR] {exc}\n")
            finally:
                self.progress_queue.put(("done", self.stats.get("processed", 0), self.stats.get("total_roms", 0)))

        self.worker_thread = threading.Thread(target=run, daemon=True)
        self.worker_thread.start()

    def _stop_scraping(self):
        self.stop_flag["stop"] = True
        self.log.append("[STOP] Stop requested.")
        self.stop_btn.setEnabled(False)

    def _poll_queues(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if isinstance(msg, tuple) and msg[0] == "account":
                self._finish_account_validation(msg[1])
            elif isinstance(msg, tuple) and msg[0] == "systems":
                self._finish_system_scan(msg[1], msg[2])
            else:
                self.log.moveCursor(QTextCursor.End)
                self.log.insertPlainText(str(msg))
                self.log.moveCursor(QTextCursor.End)

        while True:
            try:
                msg = self.progress_queue.get_nowait()
            except queue.Empty:
                break
            kind, done, total = msg
            percent = int((done / total) * 100) if total else 0
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"Progress: {percent}% ({done}/{total})")
            self._update_stats()
            if kind == "done":
                self._set_busy(False)
                elapsed = int(time.time() - self.run_started_at) if self.run_started_at else 0
                if self.stop_flag["stop"]:
                    self.log.append(f"[DONE] Stopped after {elapsed}s.")
                else:
                    self.log.append(f"[DONE] Finished in {elapsed}s.")
                self.run_started_at = None

    def _finish_account_validation(self, info):
        self.validate_btn.setEnabled(True)
        if not info:
            self.account_status.setText(self.cfg.get("_screenscraper_error", "Could not validate account. Please try again."))
            return
        threads = int(info.get("maxthreads", 1))
        self.threads.setValue(max(1, min(10, threads)))
        self.account_status.setText(
            f"Validated. Level: {info.get('niveau', '0')} | Threads: {threads} | "
            f"Requests today: {info.get('requeststoday', 0)}"
        )

    def _update_stats(self):
        with self.stats_lock:
            total = self.stats.get("total_roms", 0)
            processed = self.stats.get("processed", 0)
            downloaded = self.stats.get("downloaded", 0)
            skipped = self.stats.get("skipped", 0)
            no_media = self.stats.get("no_media", 0)
            errors = self.stats.get("errors", 0)
        self.stats_label.setText(
            f"ROMs: {processed}/{total} | Downloaded: {downloaded} | "
            f"Skipped: {skipped} | No media: {no_media} | Errors: {errors}"
        )

    def _apply_styles(self):
        dark = self.dark_mode.isChecked()
        if dark:
            stylesheet = DARK_QSS
        else:
            stylesheet = LIGHT_QSS
        QApplication.instance().setStyleSheet(stylesheet)


DARK_QSS = """
QWidget {
    background: #0b1018;
    color: #edf4ff;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QFrame#Header, QFrame#ControlsBar, QGroupBox {
    background: #111b2b;
    border: 1px solid #22324a;
    border-radius: 12px;
}
QFrame#SystemCard {
    background: #121d2e;
    border-top: 1px solid #263a58;
    border-right: 1px solid #263a58;
    border-bottom: 1px solid #263a58;
    border-radius: 10px;
}
QFrame#SystemCard:hover {
    background: #1a2940;
    border-top: 1px solid #3b557b;
    border-right: 1px solid #3b557b;
    border-bottom: 1px solid #3b557b;
}
QLabel#SystemLogo {
    background: #070b12;
    border: 1px solid #22324a;
    border-radius: 8px;
    padding: 4px;
}
QLabel#SystemCardTitle {
    color: #edf4ff;
    font-weight: 800;
}
QLabel#SystemCardMeta {
    color: #9fb0c8;
}
QLabel#FallbackSystemLogo {
    color: #ff8a3d;
    font-size: 24px;
    font-weight: 900;
}
QFrame#Header {
    background: #0a0f18;
}
QLabel#AppTitle {
    color: #ff8a3d;
    font-size: 28px;
    font-weight: 800;
}
QLabel#AppSubtitle, QLabel#MutedLabel {
    color: #9fb0c8;
}
QGroupBox {
    margin-top: 16px;
    padding: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: #ffb15f;
    font-weight: 700;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background: #0e1624;
    border: 1px solid #2a3d5b;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #ff8a3d;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 24px;
    font-size: 10.5pt;
    padding: 5px 10px;
}
QPushButton {
    background: #22324a;
    border: 1px solid #344b6e;
    border-radius: 10px;
    padding: 9px 15px;
    font-weight: 700;
}
QPushButton:hover {
    background: #2e4261;
}
QPushButton:disabled {
    color: #6f7f95;
    background: #182233;
}
QPushButton#PrimaryButton {
    background: #ff7a2d;
    border-color: #ff9b55;
    color: #14120f;
}
QPushButton#PrimaryButton:hover {
    background: #ff934f;
}
QCheckBox {
    spacing: 8px;
}
QTabWidget::pane {
    border: 1px solid #22324a;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: #111b2b;
    border: 1px solid #22324a;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 20px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #ff7a2d;
    color: #111111;
}
QProgressBar {
    border: 1px solid #2a3d5b;
    border-radius: 8px;
    text-align: center;
    background: #0e1624;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: #39d98a;
}
"""


LIGHT_QSS = """
QWidget {
    background: #f3f6fb;
    color: #1c2738;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QLabel, QCheckBox, QGroupBox, QRadioButton {
    color: #1c2738;
}
QFrame#Header, QFrame#ControlsBar, QGroupBox {
    background: #ffffff;
    border: 1px solid #d2dbe9;
    border-radius: 12px;
}
QFrame#SystemCard {
    background: #ffffff;
    border-top: 1px solid #d2dbe9;
    border-right: 1px solid #d2dbe9;
    border-bottom: 1px solid #d2dbe9;
    border-radius: 10px;
}
QFrame#SystemCard:hover {
    background: #f6f9fe;
    border-top: 1px solid #b7c6db;
    border-right: 1px solid #b7c6db;
    border-bottom: 1px solid #b7c6db;
}
QLabel#SystemLogo {
    background: #101827;
    border: 1px solid #24354f;
    border-radius: 8px;
    padding: 4px;
}
QLabel#SystemCardTitle {
    color: #1c2738;
    font-weight: 800;
}
QLabel#SystemCardMeta {
    color: #62758f;
}
QLabel#FallbackSystemLogo {
    color: #d9531e;
    font-size: 24px;
    font-weight: 900;
}
QLabel#AppTitle {
    color: #d9531e;
    font-size: 28px;
    font-weight: 800;
}
QLabel#AppSubtitle, QLabel#MutedLabel {
    color: #62758f;
}
QGroupBox {
    margin-top: 16px;
    padding: 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 7px;
    color: #d9531e;
    font-weight: 700;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit {
    background: #ffffff;
    color: #1c2738;
    border: 1px solid #c3cede;
    border-radius: 8px;
    padding: 8px;
    selection-background-color: #ff8a3d;
    selection-color: #111111;
}
QLineEdit, QComboBox, QSpinBox {
    min-height: 24px;
    font-size: 10.5pt;
    padding: 5px 10px;
}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QTextEdit:disabled {
    background: #edf2f8;
    color: #62758f;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #1c2738;
    selection-background-color: #ff8a3d;
    selection-color: #111111;
}
QPushButton {
    background: #e7edf6;
    color: #1c2738;
    border: 1px solid #c3cede;
    border-radius: 10px;
    padding: 9px 15px;
    font-weight: 700;
}
QPushButton:hover {
    background: #d6e1ef;
}
QPushButton:disabled {
    background: #edf2f8;
    color: #8b9ab0;
}
QPushButton#PrimaryButton {
    background: #ff7a2d;
    border-color: #e0641e;
    color: #111111;
}
QTabWidget::pane {
    border: 1px solid #d2dbe9;
    border-radius: 10px;
    top: -1px;
}
QTabBar::tab {
    background: #e7edf6;
    color: #1c2738;
    border: 1px solid #c3cede;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 10px 20px;
    margin-right: 4px;
}
QTabBar::tab:selected {
    background: #ff7a2d;
    color: #111111;
}
QProgressBar {
    border: 1px solid #c3cede;
    border-radius: 8px;
    text-align: center;
    background: #ffffff;
    color: #1c2738;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: #24b36b;
}
"""


def main():
    app = QApplication(sys.argv)
    window = ScraperQtWindow()
    window.show()
    window._fit_to_available_screen()
    QTimer.singleShot(100, window._fit_to_available_screen)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
