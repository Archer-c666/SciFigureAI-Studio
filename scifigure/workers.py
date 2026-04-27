from __future__ import annotations

import traceback

import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal

from .charting import ChartEngine, ChartSpec
from .llm import AIResult, LLMChartAssistant


class AIPlotWorker(QThread):
    finished_ok = pyqtSignal(object, object, object)  # AIResult, Figure, ChartSpec
    failed = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame, request: str, language: str, assistant: LLMChartAssistant, engine: ChartEngine) -> None:
        super().__init__()
        self.df = df.copy()
        self.request = request
        self.language = language
        self.assistant = assistant
        self.engine = engine

    def run(self) -> None:
        try:
            result: AIResult = self.assistant.create_spec(self.df, self.request, self.language)
            fig = self.engine.render(self.df, result.spec)
            self.finished_ok.emit(result, fig, result.spec)
        except Exception:
            self.failed.emit(traceback.format_exc())


class PlotWorker(QThread):
    finished_ok = pyqtSignal(object, object)  # Figure, ChartSpec
    failed = pyqtSignal(str)

    def __init__(self, df: pd.DataFrame, spec: ChartSpec, engine: ChartEngine) -> None:
        super().__init__()
        self.df = df.copy()
        self.spec = spec
        self.engine = engine

    def run(self) -> None:
        try:
            fig = self.engine.render(self.df, self.spec)
            self.finished_ok.emit(fig, self.spec)
        except Exception:
            self.failed.emit(traceback.format_exc())
