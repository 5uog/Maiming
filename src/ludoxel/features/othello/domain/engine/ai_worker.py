# SPDX-FileCopyrightText: 2026 Kento Konishi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from concurrent.futures import Future, ProcessPoolExecutor
from dataclasses import dataclass
import multiprocessing
from queue import Empty

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from .ai import InsaneSearchCache, analyze_position, choose_ai_move
from ..book.book_learning import BookLearningCancelled, BookLearningResult, learn_opening_book
from ..game.types import DEFAULT_OTHELLO_HASH_LEVEL, DEFAULT_OTHELLO_SACRIFICE_LEVEL, DEFAULT_OTHELLO_THREAD_COUNT, OthelloSettings, normalize_hash_level, normalize_sacrifice_level, normalize_thread_count

_PROCESS_CACHE: InsaneSearchCache | None = None
_FALLBACK_CACHE: InsaneSearchCache | None = None
_ANALYSIS_STRONG_BUDGET_S = 0.28
_ANALYSIS_INSANE_BUDGET_S = 0.45
_SEARCH_EXECUTOR_WORKERS = 1
_BOOK_EXECUTOR_WORKERS = 1


def _process_cache() -> InsaneSearchCache:
    global _PROCESS_CACHE
    if _PROCESS_CACHE is None:
        _PROCESS_CACHE = InsaneSearchCache()
    return _PROCESS_CACHE


def _fallback_cache() -> InsaneSearchCache:
    global _FALLBACK_CACHE
    if _FALLBACK_CACHE is None:
        _FALLBACK_CACHE = InsaneSearchCache()
    return _FALLBACK_CACHE


def _compute_ai_move(board: tuple[int, ...], side: int, difficulty: str, seed: int, generation: int, project_root: str, sacrifice_level: int, hash_level: int) -> int | None:
    return choose_ai_move(board, side, difficulty, random_seed=int(seed), project_root=str(project_root), match_generation=int(generation), insane_cache=_process_cache(), sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))


def _compute_analysis(board: tuple[int, ...], side: int, difficulty: str, seed: int, generation: int, project_root: str, sacrifice_level: int, hash_level: int):
    return analyze_position(board, side, difficulty, random_seed=int(seed), project_root=str(project_root), strong_time_budget_s=float(_ANALYSIS_STRONG_BUDGET_S), insane_time_budget_s=float(_ANALYSIS_INSANE_BUDGET_S), match_generation=int(generation), insane_cache=_process_cache(), sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))


def _push_book_learning_progress(progress_queue, payload: dict[str, object]) -> None:
    if progress_queue is None:
        return
    try:
        progress_queue.put(dict(payload))
    except Exception:
        pass


def _compute_book_learning(depth: int, per_move_error: float, cumulative_error: float, leaf_error: float, project_root: str, hash_level: int, sacrifice_level: int, progress_queue, cancel_event) -> BookLearningResult:
    def progress_sink(payload: dict[str, object]) -> None:
        _push_book_learning_progress(progress_queue, payload)

    def cancel_check() -> bool:
        if cancel_event is None:
            return False
        try:
            return bool(cancel_event.is_set())
        except Exception:
            return False

    return learn_opening_book(depth=int(depth), per_move_error=float(per_move_error), cumulative_error=float(cumulative_error), leaf_error=float(leaf_error), project_root=str(project_root), hash_level=int(hash_level), sacrifice_level=int(sacrifice_level), progress_sink=progress_sink, cancel_check=cancel_check)


@dataclass
class _PendingTask:
    kind: str
    generation: int
    future: Future


class OthelloAiWorker(QObject):
    move_ready = pyqtSignal(int, object)
    analysis_ready = pyqtSignal(int, object)
    book_learning_progress = pyqtSignal(object)
    book_learning_ready = pyqtSignal(object)

    def __init__(self, parent: QObject | None=None) -> None:
        super().__init__(parent)
        self._search_executor: ProcessPoolExecutor | None = None
        self._search_executor_unavailable = False
        self._book_executor: ProcessPoolExecutor | None = None
        self._book_executor_unavailable = False
        self._pending: list[_PendingTask] = []
        self._worker_count = int(DEFAULT_OTHELLO_THREAD_COUNT)
        self._book_learning_manager = None
        self._book_learning_progress_queue = None
        self._book_learning_cancel_event = None
        self._book_learning_cancelled = False
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(16)
        self._poll_timer.timeout.connect(self._drain_completed)

    def _recreate_search_executor(self) -> None:
        if self._search_executor is not None:
            try:
                self._search_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._search_executor = None

    def _recreate_book_executor(self) -> None:
        if self._book_executor is not None:
            try:
                self._book_executor.shutdown(wait=False, cancel_futures=True)
            except Exception:
                pass
            self._book_executor = None

    def _ensure_search_executor(self, *, worker_count: int) -> ProcessPoolExecutor | None:
        normalized_worker_count = normalize_thread_count(worker_count, default=DEFAULT_OTHELLO_THREAD_COUNT)
        if self._search_executor_unavailable:
            return None
        if self._search_executor is not None and int(normalized_worker_count) == int(self._worker_count):
            return self._search_executor
        self._worker_count = int(normalized_worker_count)
        self._recreate_search_executor()
        try:
            self._search_executor = ProcessPoolExecutor(max_workers=int(_SEARCH_EXECUTOR_WORKERS), mp_context=multiprocessing.get_context("spawn"))
        except Exception:
            self._search_executor = None
            self._search_executor_unavailable = True
        return self._search_executor

    def _ensure_book_executor(self) -> ProcessPoolExecutor | None:
        if self._book_executor_unavailable:
            return None
        if self._book_executor is not None:
            return self._book_executor
        try:
            self._book_executor = ProcessPoolExecutor(max_workers=int(_BOOK_EXECUTOR_WORKERS), mp_context=multiprocessing.get_context("spawn"))
        except Exception:
            self._book_executor = None
            self._book_executor_unavailable = True
        return self._book_executor

    def _ensure_book_learning_manager(self):
        if self._book_learning_manager is None:
            self._book_learning_manager = multiprocessing.Manager()
        return self._book_learning_manager

    def _clear_book_learning_ipc(self) -> None:
        self._book_learning_progress_queue = None
        self._book_learning_cancel_event = None

    def _cancel_pending_kind(self, kind: str) -> None:
        remaining: list[_PendingTask] = []
        for task in self._pending:
            if str(task.kind) == str(kind):
                task.future.cancel()
                continue
            remaining.append(task)
        self._pending = remaining
        if not self._pending:
            self._poll_timer.stop()

    def _emit_fallback_move(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int, project_root: str, sacrifice_level: int, hash_level: int) -> None:

        def emit_result() -> None:
            try:
                move_index = choose_ai_move(board, side, difficulty, random_seed=int(seed), project_root=str(project_root), match_generation=int(generation), insane_cache=_fallback_cache(), sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))
            except Exception:
                move_index = None
            self.move_ready.emit(int(generation), move_index)

        QTimer.singleShot(0, emit_result)

    def _emit_fallback_analysis(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int, project_root: str, sacrifice_level: int, hash_level: int) -> None:

        def emit_result() -> None:
            try:
                analysis = analyze_position(board, side, difficulty, random_seed=int(seed), project_root=str(project_root), strong_time_budget_s=float(_ANALYSIS_STRONG_BUDGET_S), insane_time_budget_s=float(_ANALYSIS_INSANE_BUDGET_S), match_generation=int(generation), insane_cache=_fallback_cache(), sacrifice_level=int(sacrifice_level), hash_level=int(hash_level))
            except Exception:
                analysis = None
            self.analysis_ready.emit(int(generation), analysis)

        QTimer.singleShot(0, emit_result)

    def _emit_fallback_book_learning(self, *, settings: OthelloSettings, project_root: str) -> None:

        def emit_result() -> None:
            try:
                result = learn_opening_book(depth=int(settings.book_learning_depth), per_move_error=float(settings.book_per_move_error), cumulative_error=float(settings.book_cumulative_error), leaf_error=float(settings.book_leaf_error), project_root=str(project_root), hash_level=int(settings.hash_level), sacrifice_level=int(settings.sacrifice_level))
                payload = {"ok": True, "result": result, "error": ""}
            except Exception as exc:
                payload = {"ok": False, "result": None, "error": str(exc)}
            self.book_learning_ready.emit(payload)

        QTimer.singleShot(0, emit_result)

    def request_move(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int, project_root: str="", thread_count: int=DEFAULT_OTHELLO_THREAD_COUNT, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL, hash_level: int=DEFAULT_OTHELLO_HASH_LEVEL) -> None:
        normalized_board = tuple(int(value) for value in tuple(board))
        normalized_side = int(side)
        normalized_difficulty = str(difficulty)
        normalized_seed = int(seed)
        normalized_project_root = str(project_root or "")
        normalized_sacrifice_level = normalize_sacrifice_level(sacrifice_level, default=DEFAULT_OTHELLO_SACRIFICE_LEVEL)
        normalized_hash_level = normalize_hash_level(hash_level, default=DEFAULT_OTHELLO_HASH_LEVEL)

        self._cancel_pending_kind("move")
        executor = self._ensure_search_executor(worker_count=int(thread_count))
        if executor is None:
            self._emit_fallback_move(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed, project_root=normalized_project_root, sacrifice_level=int(normalized_sacrifice_level), hash_level=int(normalized_hash_level))
            return

        try:
            future = executor.submit(_compute_ai_move, normalized_board, normalized_side, normalized_difficulty, normalized_seed, int(generation), normalized_project_root, int(normalized_sacrifice_level), int(normalized_hash_level))
        except Exception:
            self._search_executor_unavailable = True
            self._recreate_search_executor()
            self._emit_fallback_move(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed, project_root=normalized_project_root, sacrifice_level=int(normalized_sacrifice_level), hash_level=int(normalized_hash_level))
            return
        self._pending.append(_PendingTask(kind="move", generation=int(generation), future=future))
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def request_analysis(self, *, generation: int, board: tuple[int, ...], side: int, difficulty: str, seed: int, project_root: str="", thread_count: int=DEFAULT_OTHELLO_THREAD_COUNT, sacrifice_level: int=DEFAULT_OTHELLO_SACRIFICE_LEVEL, hash_level: int=DEFAULT_OTHELLO_HASH_LEVEL) -> None:
        normalized_board = tuple(int(value) for value in tuple(board))
        normalized_side = int(side)
        normalized_difficulty = str(difficulty)
        normalized_seed = int(seed)
        normalized_project_root = str(project_root or "")
        normalized_sacrifice_level = normalize_sacrifice_level(sacrifice_level, default=DEFAULT_OTHELLO_SACRIFICE_LEVEL)
        normalized_hash_level = normalize_hash_level(hash_level, default=DEFAULT_OTHELLO_HASH_LEVEL)

        self._cancel_pending_kind("analysis")
        executor = self._ensure_search_executor(worker_count=int(thread_count))
        if executor is None:
            self._emit_fallback_analysis(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed, project_root=normalized_project_root, sacrifice_level=int(normalized_sacrifice_level), hash_level=int(normalized_hash_level))
            return

        try:
            future = executor.submit(_compute_analysis, normalized_board, normalized_side, normalized_difficulty, normalized_seed, int(generation), normalized_project_root, int(normalized_sacrifice_level), int(normalized_hash_level))
        except Exception:
            self._search_executor_unavailable = True
            self._recreate_search_executor()
            self._emit_fallback_analysis(generation=int(generation), board=normalized_board, side=normalized_side, difficulty=normalized_difficulty, seed=normalized_seed, project_root=normalized_project_root, sacrifice_level=int(normalized_sacrifice_level), hash_level=int(normalized_hash_level))
            return
        self._pending.append(_PendingTask(kind="analysis", generation=int(generation), future=future))
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def request_book_learning(self, *, settings: OthelloSettings, project_root: str="") -> None:
        normalized_settings = settings.normalized()
        normalized_project_root = str(project_root or "")
        self.cancel_book_learning(emit_ready=False)
        self._cancel_pending_kind("book_learning")
        executor = self._ensure_book_executor()
        if executor is None:
            self._emit_fallback_book_learning(settings=normalized_settings, project_root=normalized_project_root)
            return

        manager = self._ensure_book_learning_manager()
        self._book_learning_progress_queue = manager.Queue()
        self._book_learning_cancel_event = manager.Event()
        self._book_learning_cancelled = False
        try:
            future = executor.submit(_compute_book_learning, int(normalized_settings.book_learning_depth), float(normalized_settings.book_per_move_error), float(normalized_settings.book_cumulative_error), float(normalized_settings.book_leaf_error), normalized_project_root, int(normalized_settings.hash_level), int(normalized_settings.sacrifice_level), self._book_learning_progress_queue, self._book_learning_cancel_event)
        except Exception:
            self._book_executor_unavailable = True
            self._recreate_book_executor()
            self._clear_book_learning_ipc()
            self._emit_fallback_book_learning(settings=normalized_settings, project_root=normalized_project_root)
            return
        self._pending.append(_PendingTask(kind="book_learning", generation=-1, future=future))
        if not self._poll_timer.isActive():
            self._poll_timer.start()

    def cancel_book_learning(self, *, emit_ready: bool=True) -> None:
        if self._book_learning_cancel_event is None and not any(str(task.kind) == "book_learning" for task in self._pending):
            return
        self._book_learning_cancelled = True
        if self._book_learning_cancel_event is not None:
            try:
                self._book_learning_cancel_event.set()
            except Exception:
                pass
        if self._book_executor is not None:
            try:
                self._book_executor.terminate_workers()
            except Exception:
                pass
        self._recreate_book_executor()
        self._cancel_pending_kind("book_learning")
        self._clear_book_learning_ipc()
        if bool(emit_ready):
            self.book_learning_ready.emit({"ok": False, "result": None, "error": "", "cancelled": True})

    def shutdown(self) -> None:
        self._poll_timer.stop()
        self.cancel_book_learning(emit_ready=False)
        for task in self._pending:
            task.future.cancel()
        self._pending.clear()
        self._recreate_search_executor()
        self._recreate_book_executor()
        if self._book_learning_manager is not None:
            try:
                self._book_learning_manager.shutdown()
            except Exception:
                pass
            self._book_learning_manager = None

    def _drain_book_learning_progress(self) -> None:
        if self._book_learning_progress_queue is None:
            return
        while True:
            try:
                payload = self._book_learning_progress_queue.get_nowait()
            except Empty:
                return
            except Exception:
                return
            self.book_learning_progress.emit(payload)

    def _drain_completed(self) -> None:
        self._drain_book_learning_progress()
        remaining: list[_PendingTask] = []
        for task in self._pending:
            if not task.future.done():
                remaining.append(task)
                continue

            if str(task.kind) == "move":
                try:
                    move_index = task.future.result()
                except Exception:
                    move_index = None
                self.move_ready.emit(int(task.generation), move_index)
                continue

            if str(task.kind) == "analysis":
                try:
                    analysis = task.future.result()
                except Exception:
                    analysis = None
                self.analysis_ready.emit(int(task.generation), analysis)
                continue

            if str(task.kind) == "book_learning":
                self._drain_book_learning_progress()
                try:
                    result = task.future.result()
                    payload = {"ok": True, "result": result, "error": ""}
                except BookLearningCancelled:
                    payload = {"ok": False, "result": None, "error": "", "cancelled": True}
                except Exception as exc:
                    if bool(self._book_learning_cancelled):
                        payload = {"ok": False, "result": None, "error": "", "cancelled": True}
                    else:
                        payload = {"ok": False, "result": None, "error": str(exc)}
                self._book_learning_cancelled = False
                self._clear_book_learning_ipc()
                self.book_learning_ready.emit(payload)
                continue

            remaining.append(task)

        self._pending = remaining
        if not self._pending:
            self._poll_timer.stop()
