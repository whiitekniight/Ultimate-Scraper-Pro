#! python3.12
import os
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QScrollArea, QSplitter, QGroupBox, QSizePolicy)
import scraper_ui as base

ROOT = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
# Settings live in this user's LocalAppData; never load the personal Studio settings.
RESOURCES = Path(__file__).resolve().parent

STYLE = '''
QWidget { background:#0c0e17; color:#edf0ff; font-family:"Segoe UI"; font-size:10pt; }
QLabel, QCheckBox { background:transparent; }
QFrame#Header { background:qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #252043,stop:.6 #151c32,stop:1 #123236); border:1px solid #45426a; border-radius:18px; }
QLabel#AppTitle { color:#ffffff; font-size:27px; font-weight:800; }
QLabel#AppSubtitle, QLabel#MutedLabel { color:#a5afcb; }
QLabel#Eyebrow { color:#76f2d1; font-size:10px; font-weight:800; letter-spacing:2px; }
QGroupBox, QFrame#ControlsBar { background:#141827; border:1px solid #2c334d; border-radius:14px; padding:12px; margin-top:16px; }
QGroupBox::title { subcontrol-origin:margin; left:15px; padding:0 8px; color:#b5a4ff; font-weight:700; }
QLineEdit, QComboBox, QSpinBox, QTextEdit { background:#0e1220; color:#eff3ff; border:1px solid #303b56; border-radius:8px; padding:8px; selection-background-color:#7255db; }
QLineEdit, QComboBox { min-height:22px; }
QComboBox QAbstractItemView { background:#1b2034; color:#ffffff; selection-background-color:#7255db; }
QPushButton { background:#232b43; color:#edf0ff; border:1px solid #3b4662; border-radius:9px; padding:9px 12px; font-weight:600; min-height:18px; }
QPushButton:hover { background:#353257; border-color:#9d88f7; }
QPushButton:disabled { background:#161c2a; color:#69768d; }
QPushButton#PrimaryButton { background:qlineargradient(x1:0,y1:0,x2:1,y2:0,stop:0 #9269f5,stop:1 #6959da); border:1px solid #b49bff; color:white; }
QPushButton#PrimaryButton:hover { background:#a081f6; }
QCheckBox { spacing:8px; }
QCheckBox::indicator { width:16px; height:16px; border:1px solid #586580; border-radius:4px; background:#0e1220; }
QCheckBox::indicator:checked { background:#83eacb; border-color:#83eacb; image:none; }
QTabWidget::pane { border:0; }
QTabBar::tab { background:#171d2e; color:#aab7d4; border:1px solid #2c3650; border-radius:9px; padding:8px 24px; margin:0 7px 4px 0; }
QTabBar::tab:selected { background:#7860d9; color:white; border-color:#ab90ff; }
QProgressBar { background:#0d1323; border:1px solid #36445e; border-radius:7px; text-align:center; min-height:20px; }
QProgressBar::chunk { background:#64d9b5; border-radius:6px; }
QTextEdit#LogBox { font-family:"Consolas"; font-size:11pt; padding:14px; border:1px solid #34405b; border-radius:12px; background:#0a0e19; color:#d5e4f6; }
QScrollArea { background:transparent; border:0; }
QScrollBar:vertical { background:#12182a; width:12px; margin:0; }
QScrollBar::handle:vertical { background:#475374; min-height:35px; border-radius:6px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
QSplitter::handle { background:#303952; width:5px; }
QFrame#SystemCard { background:#171d30; border:1px solid #36415b; border-radius:12px; }
QFrame#CollectionControls { background:#141827; border:1px solid #2c334d; border-radius:12px; padding:0; margin:0; }
QFrame#SystemCard:hover { border-color:#a085ff; background:#242440; }
QLabel#SystemLogo { background:#0b1020; border:1px solid #2c3952; border-radius:8px; padding:4px; }
QLabel#SystemCardTitle { color:#edf0ff; font-weight:700; }
QLabel#SystemCardMeta { color:#a0b2cd; }
QLabel#FallbackSystemLogo { color:#82ebd0; font-size:24px; font-weight:800; }
'''

class StudioWindow(base.ScraperQtWindow):
    def _fit_to_available_screen(self):
        screen=QApplication.primaryScreen()
        if screen:
            rect=screen.availableGeometry()
            self.setMinimumSize(1000,700)
            self.setMaximumHeight(16777215)
            self.resize(min(1440,rect.width()-30),min(940,rect.height()-40))
            self.move(rect.x()+(rect.width()-self.width())//2,rect.y()+(rect.height()-self.height())//2)
    def _apply_styles(self):
        self.setStyleSheet(STYLE if self.dark_mode.isChecked() else base.LIGHT_QSS + '\nQLabel, QCheckBox { background:transparent; } QTextEdit#LogBox { font-family:"Consolas"; font-size:11pt; }')
    def _build_ui(self):
        super()._build_ui()
        self.setWindowTitle('Ultimate Scraper pro • Studio 1.2.0')
        header=self.findChild(QFrame,'Header')
        header.setFixedHeight(160)
        header.layout().setContentsMargins(18, 14, 18, 14)
        self.setWindowIcon(QIcon(str(RESOURCES / 'studio_logo_hd.ico')))
        for label in header.findChildren(QLabel):
            if label.objectName()=='AppSubtitle': label.setText('Your collection. Fully dressed.  /  Artwork • video • metadata')
            elif not label.objectName():
                label.setFixedSize(132, 132)
                label.setAlignment(Qt.AlignCenter)
                # Preserve the existing layout slot; enlarge only the artwork.
                label.clear()
                header.layout().setAlignment(label, Qt.AlignVCenter)
                logo = QLabel(header)
                logo.setObjectName('HeaderLogoArtwork')
                logo.setFixedSize(156, 156)
                logo.setAlignment(Qt.AlignCenter)
                logo.setAttribute(Qt.WA_TransparentForMouseEvents)
                logo.setPixmap(QPixmap(str(RESOURCES / 'Gamersicon-HD.png')).scaled(
                    156, 156, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                def position_logo(slot=label, artwork=logo):
                    artwork.move(slot.x() + (slot.width() - artwork.width()) // 2,
                                 (header.height() - artwork.height()) // 2)
                    artwork.raise_()
                QTimer.singleShot(0, position_logo)
        self.dark_mode.setText('Night mode')
        self.centralWidget().layout().setSpacing(8)
        collection = self.tabs.widget(0)
        collection.layout().setSpacing(6)
        collection.layout().setContentsMargins(9, 0, 9, 0)
        for bar in collection.findChildren(QFrame, 'ControlsBar'):
            bar.setObjectName('CollectionControls')
            bar.layout().setContentsMargins(12, 6, 12, 6)
            bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.systems_grid.setVerticalSpacing(8)
        self.systems_grid.setContentsMargins(8, 4, 8, 4)
        scrape=self.tabs.widget(1)
        layout=scrape.layout()
        account=layout.takeAt(0).widget()
        paths=layout.takeAt(0).widget()
        controls=layout.takeAt(0).widget()
        progress=layout.takeAt(0).layout()
        stats=layout.takeAt(0).widget()
        tools=layout.takeAt(0).layout()
        log=layout.takeAt(0).widget()
        accounts_tab=QWidget()
        accounts_layout=QVBoxLayout(accounts_tab)
        accounts_layout.addWidget(account)
        tip=QLabel('Sign in with your own ScreenScraper account.\nYour login is sent securely through the scraper service. Developer credentials stay on the server.')
        tip.setObjectName('MutedLabel'); tip.setWordWrap(True)
        accounts_layout.addWidget(tip); accounts_layout.addStretch()
        self.tabs.insertTab(3,accounts_tab,'Accounts')
        splitter=QSplitter(Qt.Horizontal)
        left=QWidget(); left_layout=QVBoxLayout(left); left_layout.setContentsMargins(0,0,12,0)
        left_layout.addWidget(paths)
        media=QGroupBox('What to collect'); grid=QGridLayout(media)
        for idx,checkbox in enumerate(self.media_toggles.values()): grid.addWidget(checkbox,idx//3,idx%3)
        left_layout.addWidget(media)
        self.video_path_hint=QLabel('Videos save to: videos/{GAME}-video.mp4')
        self.video_path_hint.setObjectName('MutedLabel'); self.video_path_hint.setWordWrap(True)
        left_layout.addWidget(self.video_path_hint)
        left_layout.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(left);scroll.setMinimumWidth(440)
        right=QWidget();right_layout=QVBoxLayout(right);right_layout.setContentsMargins(12,0,0,0)
        heading=QLabel('LIVE ACTIVITY');heading.setObjectName('Eyebrow');right_layout.addWidget(heading)
        log.setMinimumHeight(300);right_layout.addWidget(log,1)
        right_layout.addLayout(tools)
        splitter.addWidget(scroll);splitter.addWidget(right);splitter.setSizes([650,650])
        layout.addWidget(splitter,1)
        controls_layout=controls.layout()
        reused_controls = {self.start_btn, self.stop_btn, self.test_one_btn,
                           self.build_gamelist_btn, self.open_output_btn, self.threads, self.gamelist}
        while controls_layout.count():
            item = controls_layout.takeAt(0)
            widget = item.widget()
            if widget is not None and widget not in reused_controls:
                widget.hide()
                if widget is not self.gamelist:
                    widget.deleteLater()
        controls.setLayout(controls_layout)
        controls_layout.setContentsMargins(10,8,10,8)
        for button in [self.start_btn,self.stop_btn,self.test_one_btn,self.build_gamelist_btn,self.open_output_btn]: controls_layout.addWidget(button)
        controls_layout.addStretch();controls_layout.addWidget(QLabel('Threads'));controls_layout.addWidget(self.threads)
        footer=QHBoxLayout();footer.addWidget(stats,1);footer.addWidget(self.gamelist)
        layout.addWidget(controls);layout.addLayout(progress);layout.addLayout(footer)
        self.tabs.setTabText(0,'Collection');self.tabs.setTabText(1,'Scrape studio');self.tabs.setTabText(2,'Output & filenames')
    def _apply_preset_to_fields(self):
        super()._apply_preset_to_fields()
        if hasattr(self,'video_path_hint'):
            self.video_path_hint.setText('Videos save to: '+(self._patterns_from_fields().get('video') or 'Choose a video filename in Output & filenames'))

if __name__=='__main__':
    if sys.platform == 'win32':
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('UltimateScraperPro.Studio.Public')
    app=QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(RESOURCES / 'studio_logo_hd.ico')))
    app.setStyle('Fusion')
    app.setFont(QFont('Segoe UI',10))
    window=StudioWindow()
    def report_error(kind, value, tb):
        import traceback
        window.log.append('[ERROR] An unexpected error occurred. Please restart the app.')
    sys.excepthook=report_error
    window.show()
    sys.exit(app.exec())
