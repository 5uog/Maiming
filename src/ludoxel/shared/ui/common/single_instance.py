# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from hashlib import sha1
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtNetwork import QLocalServer, QLocalSocket


def _server_name_for_root(project_root: Path) -> str:
    digest = sha1(str(Path(project_root).resolve()).encode("utf-8")).hexdigest()[:16]
    return f"ludoxel-{digest}"


class SingleInstanceRelay(QObject):
    activation_requested = pyqtSignal()

    def __init__(self, project_root: Path, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._server_name = _server_name_for_root(project_root)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._consume_pending_connections)

    def activate_existing_instance(self, *, timeout_ms: int = 400) -> bool:
        socket = QLocalSocket(self)
        socket.connectToServer(str(self._server_name))
        if not socket.waitForConnected(int(max(1, int(timeout_ms)))):
            socket.abort()
            socket.deleteLater()
            return False
        socket.write(b"activate\n")
        socket.flush()
        socket.waitForBytesWritten(int(max(1, int(timeout_ms))))
        socket.disconnectFromServer()
        socket.deleteLater()
        return True

    def listen(self) -> bool:
        if self._server.isListening():
            return True
        if self._server.listen(str(self._server_name)):
            return True
        QLocalServer.removeServer(str(self._server_name))
        return bool(self._server.listen(str(self._server_name)))

    def close(self) -> None:
        if self._server.isListening():
            self._server.close()
        QLocalServer.removeServer(str(self._server_name))

    def _consume_pending_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(lambda current=socket: self._consume_socket(current))
            socket.disconnected.connect(socket.deleteLater)
            self._consume_socket(socket)

    def _consume_socket(self, socket: QLocalSocket) -> None:
        payload = bytes(socket.readAll()).decode("utf-8", errors="ignore").strip().lower()
        if "activate" in payload:
            self.activation_requested.emit()
        if socket.state() == QLocalSocket.LocalSocketState.ConnectedState:
            socket.disconnectFromServer()
