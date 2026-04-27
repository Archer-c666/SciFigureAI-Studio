from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt


@dataclass
class DataProfile:
    rows: int
    columns: int
    missing_ratio: float
    duplicate_rows: int
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    datetime_columns: list[str] = field(default_factory=list)
    bool_columns: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        return (
            f"**数据概览**\n"
            f"- 行数：{self.rows}\n"
            f"- 列数：{self.columns}\n"
            f"- 缺失率：{self.missing_ratio:.2%}\n"
            f"- 重复行：{self.duplicate_rows}\n"
            f"- 数值列：{', '.join(self.numeric_columns) or '无'}\n"
            f"- 分类列：{', '.join(self.categorical_columns) or '无'}\n"
            f"- 时间列：{', '.join(self.datetime_columns) or '无'}"
        )


class DataProject:
    def __init__(self) -> None:
        self.path: Path | None = None
        self.df: pd.DataFrame | None = None

    @property
    def loaded(self) -> bool:
        return self.df is not None and not self.df.empty

    @property
    def name(self) -> str:
        if self.path:
            return self.path.name
        return getattr(self, "_manual_name", "未命名数据集")

    def load(self, path: str | Path) -> pd.DataFrame:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix in {".csv", ".txt"}:
            df = pd.read_csv(path)
        elif suffix in {".xls", ".xlsx"}:
            df = pd.read_excel(path)
        elif suffix == ".parquet":
            df = pd.read_parquet(path)
        elif suffix == ".json":
            df = pd.read_json(path)
        else:
            raise ValueError(f"暂不支持的文件格式：{suffix}")

        df = self._clean_columns(df)
        self.path = path
        self.df = df
        return df

    def load_clipboard(self) -> pd.DataFrame:
        df = pd.read_clipboard()
        df = self._clean_columns(df)
        self.path = None
        self._manual_name = "剪贴板数据"
        self.df = df
        return df

    def load_dataframe(self, df: pd.DataFrame, name: str = "手动输入数据") -> pd.DataFrame:
        df = self._clean_columns(df)
        self.path = None
        self._manual_name = name
        self.df = df
        return df

    @staticmethod
    def _clean_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [str(c).strip() or f"column_{i}" for i, c in enumerate(df.columns)]
        # 尝试把明显的日期字符串识别为 datetime，但不强行改变高基数文本列。
        for col in df.columns:
            if df[col].dtype == object:
                sample = df[col].dropna().astype(str).head(30)
                if sample.empty:
                    continue
                parsed = pd.to_datetime(sample, errors="coerce")
                if parsed.notna().mean() > 0.8:
                    df[col] = pd.to_datetime(df[col], errors="coerce")
        return df

    def profile(self) -> DataProfile:
        if self.df is None:
            raise ValueError("请先加载数据")
        df = self.df
        return DataProfile(
            rows=len(df),
            columns=len(df.columns),
            missing_ratio=float(df.isna().mean().mean()) if len(df.columns) else 0.0,
            duplicate_rows=int(df.duplicated().sum()),
            numeric_columns=list(df.select_dtypes(include=np.number).columns),
            categorical_columns=list(df.select_dtypes(include=["object", "category"]).columns),
            datetime_columns=list(df.select_dtypes(include=["datetime", "datetimetz"]).columns),
            bool_columns=list(df.select_dtypes(include=["bool"]).columns),
        )


class PandasTableModel(QAbstractTableModel):
    def __init__(self, df: pd.DataFrame | None = None, max_rows: int = 500) -> None:
        super().__init__()
        self.max_rows = max_rows
        self._df = pd.DataFrame() if df is None else df.head(max_rows).copy()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df.head(self.max_rows).copy()
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._df)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802
        return 0 if parent.isValid() else len(self._df.columns)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or role not in {Qt.DisplayRole, Qt.ToolTipRole}:
            return None
        value = self._df.iat[index.row(), index.column()]
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:  # noqa: N802
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        return str(section + 1)
