from __future__ import annotations

import io
import re
from dataclasses import replace

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .config import AppConfig, save_config


class LLMConfigDialog(QDialog):
    """A small in-app settings panel for OpenAI-compatible model providers."""

    PRESETS = {
        "OpenAI": ("https://api.openai.com/v1", "gpt-4.1-mini"),
        "DeepSeek": ("https://api.deepseek.com", "deepseek-chat"),
        "DeepSeek Reasoner": ("https://api.deepseek.com", "deepseek-reasoner"),
        "自定义 OpenAI-compatible": ("", ""),
        "本地规则模式（不调用大模型）": ("", ""),
    }

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("大模型配置")
        self.setMinimumWidth(560)
        self.config = config
        self.saved_config: AppConfig | None = None
        self._build_ui()
        self._load_config(config)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel("选择或填写 OpenAI-compatible 接口。留空 API Key 时，软件会使用本地规则生成图表。")
        hint.setWordWrap(True)
        hint.setObjectName("Subtle")
        layout.addWidget(hint)

        form = QFormLayout()
        self.provider_box = QComboBox()
        self.provider_box.addItems(list(self.PRESETS.keys()))
        self.provider_box.currentTextChanged.connect(self._apply_preset)
        self.base_url_edit = QLineEdit()
        self.base_url_edit.setPlaceholderText("例如：https://api.openai.com/v1 或 https://api.deepseek.com")
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("例如：gpt-4.1-mini / deepseek-chat / your-model")
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-... 或服务商提供的 API Key")
        self.show_key_check = QCheckBox("显示 Key")
        self.show_key_check.stateChanged.connect(self._toggle_key_visible)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(45)
        form.addRow("服务商预设", self.provider_box)
        form.addRow("Base URL", self.base_url_edit)
        form.addRow("模型名称", self.model_edit)
        form.addRow("API Key", self.api_key_edit)
        form.addRow("", self.show_key_check)
        form.addRow("超时秒数", self.timeout_spin)
        layout.addLayout(form)

        quick = QHBoxLayout()
        local_btn = QPushButton("切换为本地规则模式")
        local_btn.setObjectName("Secondary")
        local_btn.clicked.connect(self._set_local_mode)
        quick.addWidget(local_btn)
        quick.addStretch(1)
        layout.addLayout(quick)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_config(self, config: AppConfig) -> None:
        self.base_url_edit.setText(config.base_url)
        self.model_edit.setText(config.model)
        self.api_key_edit.setText(config.api_key)
        self.timeout_spin.setValue(config.timeout)
        if "deepseek" in config.base_url.lower():
            self.provider_box.setCurrentText("DeepSeek")
        elif config.api_key:
            self.provider_box.setCurrentText("OpenAI")
        else:
            self.provider_box.setCurrentText("本地规则模式（不调用大模型）")

    def _apply_preset(self, name: str) -> None:
        base_url, model = self.PRESETS.get(name, ("", ""))
        if name == "自定义 OpenAI-compatible":
            return
        if name == "本地规则模式（不调用大模型）":
            self.api_key_edit.clear()
        self.base_url_edit.setText(base_url)
        self.model_edit.setText(model)

    def _toggle_key_visible(self) -> None:
        self.api_key_edit.setEchoMode(QLineEdit.Normal if self.show_key_check.isChecked() else QLineEdit.Password)

    def _set_local_mode(self) -> None:
        self.provider_box.setCurrentText("本地规则模式（不调用大模型）")
        self.api_key_edit.clear()
        self.base_url_edit.clear()
        self.model_edit.clear()

    def _save(self) -> None:
        cfg = replace(
            self.config,
            api_key=self.api_key_edit.text().strip(),
            base_url=(self.base_url_edit.text().strip() or "https://api.openai.com/v1").rstrip("/"),
            model=(self.model_edit.text().strip() or "local-rule-mode"),
            timeout=int(self.timeout_spin.value()),
        )
        try:
            save_config(cfg)
        except Exception as exc:
            QMessageBox.critical(self, "保存失败", str(exc))
            return
        self.saved_config = cfg
        self.accept()


class ManualDataDialog(QDialog):
    """Dialog for typing/pasting data without opening a file."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("手动输入 / 粘贴数据")
        self.setMinimumSize(760, 560)
        self.df: pd.DataFrame | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel("可以直接输入 X/Y 两列，也可以从 Excel 复制整块表格后粘贴到“表格文本”里。")
        hint.setObjectName("Subtle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        xy_page = QWidget()
        xy_layout = QFormLayout(xy_page)
        self.x_name_edit = QLineEdit("x")
        self.y_name_edit = QLineEdit("y")
        self.x_values_edit = QPlainTextEdit()
        self.y_values_edit = QPlainTextEdit()
        self.x_values_edit.setPlaceholderText("例如：1, 2, 3, 4\n或每行一个值")
        self.y_values_edit.setPlaceholderText("例如：2.1, 2.9, 4.2, 5.0\n或每行一个值")
        xy_layout.addRow("X 列名", self.x_name_edit)
        xy_layout.addRow("Y 列名", self.y_name_edit)
        xy_layout.addRow("X 数据", self.x_values_edit)
        xy_layout.addRow("Y 数据", self.y_values_edit)
        self.tabs.addTab(xy_page, "X/Y 快速输入")

        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        self.header_check = QCheckBox("第一行是列名")
        self.header_check.setChecked(True)
        self.table_text = QPlainTextEdit()
        self.table_text.setPlaceholderText("从 Excel 复制后直接粘贴，例如：\nSample\tGroup\tValue\nA\tControl\t1.2\nB\tTreatment\t2.4\n\n也支持 CSV：\nSample,Group,Value\nA,Control,1.2")
        table_layout.addWidget(self.header_check)
        table_layout.addWidget(self.table_text, 1)
        self.tabs.addTab(table_page, "表格文本 / Excel 粘贴")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._parse)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _parse_values(self, text: str) -> list[str]:
        parts = [p for p in re.split(r"[\n,;，；\s]+", text.strip()) if p != ""]
        return parts

    @staticmethod
    def _convert_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.columns:
            converted = pd.to_numeric(df[col], errors="ignore")
            df[col] = converted
        return df

    def _parse_xy(self) -> pd.DataFrame:
        x = self._parse_values(self.x_values_edit.toPlainText())
        y = self._parse_values(self.y_values_edit.toPlainText())
        if not x or not y:
            raise ValueError("X 和 Y 数据不能为空。")
        if len(x) != len(y):
            raise ValueError(f"X/Y 数量不一致：X={len(x)}，Y={len(y)}。")
        x_name = self.x_name_edit.text().strip() or "x"
        y_name = self.y_name_edit.text().strip() or "y"
        return self._convert_columns(pd.DataFrame({x_name: x, y_name: y}))

    def _parse_table(self) -> pd.DataFrame:
        text = self.table_text.toPlainText().strip()
        if not text:
            raise ValueError("表格文本不能为空。")
        header = 0 if self.header_check.isChecked() else None
        try:
            df = pd.read_csv(io.StringIO(text), sep=None, engine="python", header=header)
        except Exception:
            # Excel pasted tables are usually tab-delimited; retry explicitly.
            df = pd.read_csv(io.StringIO(text), sep="\t", header=header)
        if header is None:
            df.columns = [f"col_{i + 1}" for i in range(len(df.columns))]
        if df.empty:
            raise ValueError("没有解析出有效数据。")
        return self._convert_columns(df)

    def _parse(self) -> None:
        try:
            if self.tabs.currentIndex() == 0:
                self.df = self._parse_xy()
            else:
                self.df = self._parse_table()
        except Exception as exc:
            QMessageBox.critical(self, "数据解析失败", str(exc))
            return
        self.accept()
