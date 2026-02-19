#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtWebEngineWidgets import QWebEngineView

# Import orchestrator pieces without changing core logic
from orchestrator import classify_code, choose_root, SAVED_DIR, RUNNING_DIR, BASE_DIR
from cloud_agent.cloud_client import get_plan
from runtime.plan_runner import apply_plan

URL_REGEX = re.compile(r"(https?://[^\s'\"]+)", re.IGNORECASE)
LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "[::1]", "::1"}


def extract_url(text: str) -> Optional[str]:
    for m in URL_REGEX.finditer(text):
        url = m.group(1)
        try:
            host = url.split("//", 1)[1].split("/", 1)[0].split(":")[0]
        except Exception:
            host = ""
        if not host or host.lower() in LOCAL_HOSTS or host.endswith(".local"):
            return url
    return None


class OrchestratorWorker(QtCore.QObject):
    log = QtCore.Signal(str)
    projectReady = QtCore.Signal(str, str)  # (project_dir, run_cmd)
    serverUrl = QtCore.Signal(str)
    runStopped = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.proc: Optional[QtCore.QProcess] = None
        self._last_run_cmd: str = ""

    @QtCore.Slot(str, str)
    def generate_and_run(self, prompt: str, policy: str = "A") -> None:
        try:
            bad_path = SAVED_DIR / "bad_reply.json"
            self.log.emit("Requesting plan…\n")
            plan = get_plan(prompt, bad_reply_path=str(bad_path))
            files = plan.get("files") or []
            first_code = files[0].get("code", "") if files and isinstance(files[0], dict) else ""
            is_program = classify_code(first_code) == "PROGRAM"
            root = choose_root(policy, is_program)
            self.log.emit(f"Applying plan (root={root})…\n")
            result = apply_plan(plan, root, is_app=is_program)
            project_dir = Path(result["project_dir"])  # type: ignore
            run_cmd = result.get("run_cmd", "")
            self._last_run_cmd = run_cmd or ""
            self.projectReady.emit(str(project_dir), self._last_run_cmd)
            self.run_project(project_dir)
        except Exception as e:
            self.log.emit(f"Error: {e}\n")

    @QtCore.Slot(Path)
    def run_project(self, project_dir: Path) -> None:
        # Use run.sh for consistency
        runner = project_dir / "run.sh"
        if not runner.exists():
            self.log.emit("No run.sh created; nothing to run.\n")
            return
        # Stop previous
        if self.proc is not None:
            try:
                self.proc.kill()
            except Exception:
                pass
            self.proc = None
        self.proc = QtCore.QProcess(self)
        # Environment inherit; set working directory to project
        self.proc.setWorkingDirectory(str(project_dir))
        # Shell execute to respect shebangs; cross-platform wrapper
        if os.name == "nt":
            program = "cmd"
            args = ["/c", "run.bat" if (project_dir / "run.bat").exists() else "run.sh"]
        else:
            program = "bash"
            args = [str(runner)]
        self.proc.setProgram(program)
        self.proc.setArguments(args)
        self.proc.setProcessChannelMode(QtCore.QProcess.SeparateChannels)
        self.proc.readyReadStandardOutput.connect(self._on_stdout)
        self.proc.readyReadStandardError.connect(self._on_stderr)
        self.proc.finished.connect(self._on_finished)
        self.log.emit(f"▶ Running {program} {' '.join(args)} (cwd={project_dir})…\n")
        self.proc.start()
        # Heuristic: if no URL seen shortly, try guessing a default
        QtCore.QTimer.singleShot(6000, self._maybe_guess_url)

    def _maybe_guess_url(self) -> None:
        # Try common defaults if we haven't emitted a URL yet
        cmd = (self._last_run_cmd or "").lower()
        guess: Optional[str] = None
        # Common frameworks
        if "gradio" in cmd:
            guess = "http://localhost:7860"
        elif "streamlit" in cmd:
            guess = "http://localhost:8501"
        elif "uvicorn" in cmd or "fastapi" in cmd:
            guess = "http://localhost:8000"
        elif "flask" in cmd or "werkzeug" in cmd:
            guess = "http://localhost:5000"
        if guess:
            self.serverUrl.emit(guess)

    @QtCore.Slot()
    def stop(self) -> None:
        if self.proc is None:
            return
        try:
            if os.name == "nt":
                self.proc.kill()
            else:
                self.proc.terminate()
        except Exception:
            pass

    def _on_stdout(self) -> None:
        if not self.proc:
            return
        data = self.proc.readAllStandardOutput().data().decode("utf-8", errors="ignore")
        if not data:
            return
        self.log.emit(data)
        url = extract_url(data)
        if url:
            # Normalize 0.0.0.0 to localhost for browser embedding
            url = url.replace("0.0.0.0", "localhost").replace("[::]", "localhost")
            self.serverUrl.emit(url)

    def _on_stderr(self) -> None:
        if not self.proc:
            return
        data = self.proc.readAllStandardError().data().decode("utf-8", errors="ignore")
        if not data:
            return
        self.log.emit(data)
        url = extract_url(data)
        if url:
            url = url.replace("0.0.0.0", "localhost").replace("[::]", "localhost")
            self.serverUrl.emit(url)

    def _on_finished(self, code: int, status: QtCore.QProcess.ExitStatus) -> None:
        self.log.emit(f"\nProcess exited with code {code}.\n")
        self.runStopped.emit(int(code))


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("AI Orchestrator – Desktop")
        self.resize(1100, 750)

        # Controls
        self.prompt = QtWidgets.QLineEdit(self)
        self.prompt.setPlaceholderText("What would you like me to do?")
        self.runBtn = QtWidgets.QPushButton("Generate & Run", self)
        self.stopBtn = QtWidgets.QPushButton("Stop", self)
        self.viewToggle = QtWidgets.QPushButton("Hide Webview", self)
        self.viewToggle.setCheckable(True)
        self.viewToggle.setChecked(True)
        self.openUrlBtn = QtWidgets.QPushButton("Open URL…", self)

        topBar = QtWidgets.QWidget(self)
        hl = QtWidgets.QHBoxLayout(topBar)
        hl.setContentsMargins(6, 6, 6, 6)
        hl.addWidget(self.prompt, 1)
        hl.addWidget(self.runBtn)
        hl.addWidget(self.stopBtn)
        hl.addWidget(self.openUrlBtn)
        hl.addWidget(self.viewToggle)

        # Log area
        self.log = QtWidgets.QPlainTextEdit(self)
        self.log.setReadOnly(True)
        self.log.document().setMaximumBlockCount(5000)

        # Web view
        self.web = QWebEngineView(self)

        # Splitter
        split = QtWidgets.QSplitter(self)
        split.setOrientation(QtCore.Qt.Vertical)
        split.addWidget(self.web)
        split.addWidget(self.log)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)

        # Layout
        central = QtWidgets.QWidget(self)
        vl = QtWidgets.QVBoxLayout(central)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(topBar)
        vl.addWidget(split, 1)
        self.setCentralWidget(central)

        # Worker in thread
        self.worker = OrchestratorWorker()
        self.thread = QtCore.QThread(self)
        self.worker.moveToThread(self.thread)
        self.thread.start()

        # Wire signals
        self.runBtn.clicked.connect(self._on_run_clicked)
        self.stopBtn.clicked.connect(self.worker.stop)
        self.viewToggle.toggled.connect(self._toggle_view)
        self.openUrlBtn.clicked.connect(self._prompt_open_url)

        self.worker.log.connect(self._append_log)
        self.worker.projectReady.connect(self._on_project_ready)
        self.worker.serverUrl.connect(self._on_server_url)

    def closeEvent(self, e):
        try:
            self.worker.stop()
        except Exception:
            pass
        try:
            # Gracefully stop the worker thread to avoid QThread warnings/crash
            self.thread.quit()
            self.thread.wait(3000)
        except Exception:
            pass
        super().closeEvent(e)

    @QtCore.Slot()
    def _on_run_clicked(self) -> None:
        text = self.prompt.text().strip()
        if not text:
            return
        # Default policy A; could prompt later if needed
        QtCore.QMetaObject.invokeMethod(
            self.worker,
            "generate_and_run",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, text),
            QtCore.Q_ARG(str, "A"),
        )

    @QtCore.Slot(bool)
    def _toggle_view(self, checked: bool) -> None:
        self.web.setVisible(checked)
        self.viewToggle.setText("Hide Webview" if checked else "Show Webview")

    @QtCore.Slot(str)
    def _append_log(self, text: str) -> None:
        try:
            self.log.moveCursor(QtGui.QTextCursor.End)
        except Exception:
            pass
        self.log.insertPlainText(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    @QtCore.Slot(str, str)
    def _on_project_ready(self, project_dir: str, run_cmd: str) -> None:
        self._append_log(f"\nProject ready: {project_dir}\nRun: {run_cmd}\n")

    @QtCore.Slot(str)
    def _on_server_url(self, url: str) -> None:
        self._append_log(f"\nDetected URL: {url}\n")
        try:
            self.web.load(QtCore.QUrl(url))
        except Exception:
            pass

    @QtCore.Slot()
    def _prompt_open_url(self) -> None:
        url, ok = QtWidgets.QInputDialog.getText(self, "Open URL", "URL:")
        if ok and url.strip():
            try:
                self.web.load(QtCore.QUrl(url.strip()))
            except Exception:
                pass


def main() -> None:
    # Ensure base dir on sys.path
    sys.path.insert(0, str(BASE_DIR))
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
