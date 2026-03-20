# Copyright 2026 Kento Konishi (https://github.com/5uog)
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
from concurrent.futures import Future, ProcessPoolExecutor
import multiprocessing

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .ai import choose_ai_move

def _compute_ai_move(board: tuple[int, ...], side: int, difficulty: str, seed: int) -> int | None:
    return choose_ai_move(board, side, difficulty, random_seed=int(seed))

class OthelloAiWorker(QObject):
    move_ready = pyqtSignal(int, object)

    def __init__(self, parent: QObject | None=None) -> None:
        super().__init__(parent)
        self._executor: ProcessPoolExecutor | None = None
        self._executor_unavailable = False
        self._pending: list[tuple[int, Future[int | None]]] = []
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(16)
        self._poll_timer.timeout.connect(self._drain_completed)

    def _ensure_executor(self) -> ProcessPoolExecutor | None:
        if self._executor_unavailable:
            return None
        if self._executor is not None:
            return self._executor
        try:
            self._executor = ProcessPoolExecutor(max_workers=1, mp_context=multiprocessing.get_context("spawn"))
        except Exception:
            self._executor = None
            self._executor_unavailable = True
        return self._executor

    def _emit_fallback_result(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int) -> None:

        def emit_result() -> None:
            try:
                move_index = _compute_ai_move(board, side, difficulty, seed)
            except Exception:
                move_index = None
            self.move_ready.emit(int(generation), move_index)

        QTimer.singleShot(0, emit_result)

    def request_move(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int) -> None:
        normalized_board = tuple(int(value) for value in tuple(board))
        normalized_side = int(side)
        normalized_difficulty = str(difficulty)
        normalized_seed = int(seed)
        executor = self._ensure_executor()
        if executor is None:
            self._emit_fallback_result(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed)
            return
        try:
            future = executor.submit(_compute_ai_move, normalized_board, normalized_side, normalized_difficulty, normalized_seed)
        except Exception:
            self._executor_unavailable = True
            try:
                executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._executor = None
            self._emit_fallback_result(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed)
            return
        self._pending.append((int(generation), future))
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def shutdown(self) -> None:
        self._poll_timer.stop()
        for _generation, future in self._pending:
            future.cancel()
        self._pending.clear()
        if self._executor is not None:
            self._executor.shutdown(wait=False, cancel_futures=True)
            self._executor = None

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