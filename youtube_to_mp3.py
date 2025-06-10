import sys
import os
import re
import subprocess
import yt_dlp
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QLabel, QProgressBar, QComboBox, QTextEdit,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont

class FFmpegInstaller:
    @staticmethod
    def is_ffmpeg_installed():
        """Check if FFmpeg is installed by attempting to run ffmpeg -version."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    @staticmethod
    def install_ffmpeg():
        """Attempt to install FFmpeg using winget, falling back to choco, with timeout."""
        try:
            print("Attempting to install FFmpeg via winget...")
            result = subprocess.run(
                ["winget", "install", "Gyan.FFmpeg"],
                capture_output=True, text=True, check=True, timeout=120
            )
            print(result.stdout)
            QMessageBox.information(
                None, "FFmpeg Installed",
                "FFmpeg was installed successfully. Please restart your terminal or system if FFmpeg is not detected."
            )
            return True
        except subprocess.TimeoutExpired:
            print("winget installation timed out after 2 minutes.")
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"winget failed: {e}")
            try:
                print("Falling back to Chocolatey...")
                subprocess.run(["choco", "--version"], capture_output=True, check=True, timeout=30)
                result = subprocess.run(
                    ["choco", "install", "ffmpeg", "-y"],
                    capture_output=True, text=True, check=True, timeout=120
                )
                print(result.stdout)
                QMessageBox.information(
                    None, "FFmpeg Installed",
                    "FFmpeg was installed successfully. Please restart your terminal or system if FFmpeg is not detected."
                )
                return True
            except subprocess.TimeoutExpired:
                print("Chocolatey installation timed out after 2 minutes.")
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"Chocolatey failed: {e}")
                return False

class DownloadThread(QThread):
    progress = pyqtSignal(int, int, int)  # current file progress, current file index, total files
    status = pyqtSignal(str, str)  # message, color
    log = pyqtSignal(str)  # log message
    finished = pyqtSignal()

    def __init__(self, url, download_folder, format_type):
        super().__init__()
        self.url = url
        self.download_folder = download_folder
        self.format_type = format_type

    def run(self):
        """Download and convert YouTube video/playlist to selected format."""
        if not re.match(r'https?://(www\.)?(youtube|youtu|vimeo)\.(com|be)/', self.url):
            self.status.emit("❌ Please enter a valid YouTube URL", "red")
            self.log.emit("Invalid URL provided.")
            self.finished.emit()
            return

        self.status.emit("⏳ Initializing download...", "yellow")
        self.log.emit(f"Starting download for: {self.url}")

        ydl_opts = {
            'outtmpl': os.path.join(self.download_folder, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'logger': self.YTDLPLogger(self.log),
            'cachedir': False,  # Prevent redundant extraction
        }

        if self.format_type == "mp3":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        elif self.format_type == "wav":
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                }],
            })
        elif self.format_type == "mp4":
            ydl_opts.update({
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }],
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            self.status.emit("✅ Download completed!", "green")
            self.log.emit("Download completed successfully.")
        except yt_dlp.DownloadError as e:
            self.status.emit(f"❌ Download error: {str(e)}", "red")
            self.log.emit(f"Download error: {str(e)}")
        except Exception as e:
            self.status.emit(f"❌ Error: {str(e)}", "red")
            self.log.emit(f"Error: {str(e)}")
        finally:
            self.finished.emit()

    def progress_hook(self, d):
        """Update download progress for single video or playlist."""
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = int(d['downloaded_bytes'] / d['total_bytes'] * 100)
                current_file = d.get('playlist_index', 1) or 1
                total_files = d.get('playlist_count', 1)
                self.progress.emit(percent, current_file, total_files)
        elif d['status'] == 'finished':
            self.log.emit(f"Finished: {d.get('filename', 'unknown')}")

    class YTDLPLogger:
        def __init__(self, log_signal):
            self.log_signal = log_signal

        def debug(self, msg):
            self.log_signal.emit(msg)

        def info(self, msg):
            self.log_signal.emit(msg)

        def warning(self, msg):
            self.log_signal.emit(f"Warning: {msg}")

        def error(self, msg):
            self.log_signal.emit(f"Error: {msg}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YouTube Converter - Manu OVG")
        self.setFixedSize(600, 500)
        self.setWindowIcon(QIcon("youtube_icon.ico"))

        # Setup download folder
        self.download_folder = os.path.join(os.path.expanduser("~"), "Music")
        os.makedirs(self.download_folder, exist_ok=True)

        # Check for FFmpeg
        if not FFmpegInstaller.is_ffmpeg_installed():
            reply = QMessageBox.question(
                self, "FFmpeg Not Found",
                "FFmpeg is required but not installed. Would you like to install it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if not FFmpegInstaller.install_ffmpeg():
                    QMessageBox.critical(
                        self, "Installation Failed",
                        "Failed to install FFmpeg. Please install it manually via 'winget install Gyan.FFmpeg' or 'choco install ffmpeg'."
                    )
                    sys.exit(1)
            else:
                QMessageBox.critical(
                    self, "FFmpeg Required",
                    "FFmpeg is required to run this application. Please install it manually."
                )
                sys.exit(1)

        # Setup UI
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header
        header = QLabel("🎵 YouTube Converter")
        header.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff;")
        layout.addWidget(header, alignment=Qt.AlignmentFlag.AlignCenter)

        # Author
        author = QLabel("Created by Manu OVG")
        author.setFont(QFont("Arial", 12))
        author.setStyleSheet("color: #aaaaaa;")
        layout.addWidget(author, alignment=Qt.AlignmentFlag.AlignCenter)

        # URL input
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter YouTube video or playlist URL")
        self.url_input.setFixedWidth(500)
        self.url_input.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
        """)
        layout.addWidget(self.url_input, alignment=Qt.AlignmentFlag.AlignCenter)

        # Format and folder selector
        selector_layout = QHBoxLayout()
        selector_layout.setSpacing(10)

        self.format_selector = QComboBox()
        self.format_selector.addItems(["MP3", "WAV", "MP4"])
        self.format_selector.setFixedWidth(150)
        self.format_selector.setStyleSheet("""
            QComboBox {
                padding: 8px;
                font-size: 14px;
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        selector_layout.addWidget(self.format_selector)

        self.folder_button = QPushButton("Choose Folder")
        self.folder_button.setFixedWidth(150)
        self.folder_button.setStyleSheet("""
            QPushButton {
                background-color: #457b9d;
                color: white;
                padding: 8px;
                font-size: 14px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #1d3557;
            }
        """)
        self.folder_button.clicked.connect(self.choose_folder)
        selector_layout.addWidget(self.folder_button)

        layout.addLayout(selector_layout)

        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.setFixedWidth(150)
        self.download_button.setStyleSheet("""
            QPushButton {
                background-color: #e63946;
                color: white;
                padding: 12px;
                font-size: 14px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d00000;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self.download_button.clicked.connect(self.start_download)
        layout.addWidget(self.download_button, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(500)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 8px;
                background-color: #2a2a2a;
                text-align: center;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #e63946;
                border-radius: 8px;
            }
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        # Progress label (for playlist progress)
        self.progress_label = QLabel("")
        self.progress_label.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        layout.addWidget(self.progress_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #ffffff; font-size: 14px;")
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Log window
        self.log_window = QTextEdit()
        self.log_window.setReadOnly(True)
        self.log_window.setFixedHeight(150)
        self.log_window.setStyleSheet("""
            QTextEdit {
                background-color: #2a2a2a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 8px;
                font-family: 'Consolas', monospace;
                font-size: 12px;
            }
        """)
        layout.addWidget(self.log_window, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()

    def choose_folder(self):
        """Open a dialog to choose the download folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.download_folder)
        if folder:
            self.download_folder = folder
            self.log_window.append(f"Download folder set to: {folder}")

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.status_label.setText("❌ Please enter a URL")
            self.status_label.setStyleSheet("color: red;")
            self.log_window.append("No URL provided.")
            return

        self.download_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText("")
        self.log_window.clear()

        format_type = self.format_selector.currentText().lower()
        self.thread = DownloadThread(url, self.download_folder, format_type)
        self.thread.progress.connect(self.update_progress)
        self.thread.status.connect(self.update_status)
        self.thread.log.connect(self.log_window.append)
        self.thread.finished.connect(self.download_finished)
        self.thread.start()

    def update_progress(self, percent, current_file, total_files):
        self.progress_bar.setValue(percent)
        if total_files > 1:
            self.progress_label.setText(f"Processing {current_file} of {total_files}")

    def update_status(self, message, color):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(f"color: {color};")

    def download_finished(self):
        self.download_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_label.setText("")
        self.url_input.clear()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow {
            background-color: #1e1e1e;
        }
        QLabel {
            color: #ffffff;
        }
    """)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
