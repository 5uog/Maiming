# FILE: src/maiming/presentation/widgets/viewport/othello_ai_worker.py
from __future__ import annotations
from concurrent.futures import Future, ProcessPoolExecutor
import multiprocessing

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from ....domain.othello.ai import choose_ai_move

def _compute_ai_move(board: tuple[int, ...], side: int, difficulty: str, seed: int) -> int | None:
    return choose_ai_move(board, side, difficulty, random_seed=int(seed))

class OthelloAiWorker(QObject):
    move_ready = pyqtSignal(int, object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._executor = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
        self._pending: list[tuple[int, Future[int | None]]] = []
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(16)
        self._poll_timer.timeout.connect(self._drain_completed)

    def request_move(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int) -> None:
        future = self._executor.submit(
            _compute_ai_move,
            tuple(int(value) for value in tuple(board)),
            int(side),
            str(difficulty),
            int(seed),
        )
        self._pending.append((int(generation), future))
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def shutdown(self) -> None:
        self._poll_timer.stop()
        for _generation, future in self._pending:
            future.cancel()
        self._pending.clear()
        self._executor.shutdown(wait=False, cancel_futures=True)

    def _drain_completed(self) -> None:
        remaining: list[tuple[int, Future[int | None]]] = []
        for generation, future in self._pending:
            if not future.done():
                remaining.append((int(generation), future))
                continue
            try:
                move_index = future.result()
            except Exception:
                move_index = None
            self.move_ready.emit(int(generation), move_index)
        self._pending = remaining
        if not self._pending:
            self._poll_timer.stop()