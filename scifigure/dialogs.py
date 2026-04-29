from __future__ import annotations

import io
import re
from dataclasses import replace

import pandas as pd
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QToolButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QAbstractItemView,
)

from .charting import BACKGROUND_STYLES, CHART_TYPES, CORRELATION_METHODS, LINE_STYLES, MARKER_STYLES, NORMALIZATION_METHODS, PALETTE_NAMES, ChartSpec
from .config import AppConfig, save_config


class LLMConfigDialog(QDialog):
    PRESETS = {
        "OpenAI": ("https://api.openai.com/v1", "gpt-4.1-mini"),
        "DeepSeek": ("https://api.deepseek.com", "deepseek-v4-flash"),
        "DeepSeek Reasoner": ("https://api.deepseek.com", "deepseek-reasoner"),
        "自定义 OpenAI-compatible": ("", ""),
        "本地规则模式（不调用大模型）": ("", "local-rule-mode"),
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
        hint = QLabel("在这里直接配置 API Key、Base URL 和模型名；保存后会写入项目根目录下的 .env 文件。")
        hint.setWordWrap(True)
        hint.setObjectName("Subtle")
        layout.addWidget(hint)

        form = QFormLayout()
        self.provider_box = QComboBox()
        self.provider_box.addItems(list(self.PRESETS.keys()))
        self.provider_box.currentTextChanged.connect(self._apply_preset)
        self.base_url_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.show_key_check = QCheckBox("显示 API Key")
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
        self.table_text.setPlaceholderText(
            "从 Excel 复制后直接粘贴，例如：\nSample\tGroup\tValue\nA\tControl\t1.2\nB\tTreatment\t2.4\n\n也支持 CSV：\nSample,Group,Value\nA,Control,1.2"
        )
        table_layout.addWidget(self.header_check)
        table_layout.addWidget(self.table_text, 1)
        self.tabs.addTab(table_page, "表格文本 / Excel 粘贴")

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._parse)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _parse_values(self, text: str) -> list[str]:
        return [p for p in re.split(r"[\n,;，；\s]+", text.strip()) if p != ""]

    @staticmethod
    def _convert_columns(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="ignore")
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
            df = pd.read_csv(io.StringIO(text), sep="\t", header=header)
        if header is None:
            df.columns = [f"col_{i + 1}" for i in range(len(df.columns))]
        if df.empty:
            raise ValueError("没有解析出有效数据。")
        return self._convert_columns(df)

    def _parse(self) -> None:
        try:
            self.df = self._parse_xy() if self.tabs.currentIndex() == 0 else self._parse_table()
        except Exception as exc:
            QMessageBox.critical(self, "数据解析失败", str(exc))
            return
        self.accept()


class ChartTypeDialog(QDialog):
    """使用例图选择图表类型。"""

    IMAGE_NAMES = {
        "柱状图": "bar.png",
        "水平柱状图": "hbar.png",
        "折线图": "line.png",
        "散点图": "scatter.png",
        "箱线图": "boxplot.png",
        "热力图": "heatmap.png",
        "饼图": "pie.png",
        "三维散点图": "scatter3d.png",
        "曲面图": "surface.png",
    }

    def __init__(self, assets_dir, current_type: str = "散点图", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("通过例图选择图表类型")
        self.setMinimumSize(780, 620)
        self.assets_dir = assets_dir
        self.current_type = current_type
        self.selected_chart_type: str | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel("点击下面的例图选择图表类型。例图仅用于说明样式和用途，不代表你的实际数据。")
        hint.setWordWrap(True)
        hint.setObjectName("Subtle")
        layout.addWidget(hint)

        grid = QGridLayout()
        grid.setSpacing(14)
        example_dir = self.assets_dir / "chart_examples"

        for idx, chart_type in enumerate(CHART_TYPES):
            button = QToolButton()
            button.setText(chart_type)
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setIconSize(QSize(190, 135))
            button.setMinimumSize(220, 185)
            button.setCheckable(True)
            button.setChecked(chart_type == self.current_type)
            button.setObjectName("ChartTypeCard")
            image_name = self.IMAGE_NAMES.get(chart_type)
            if image_name:
                image_path = example_dir / image_name
                if image_path.exists():
                    button.setIcon(QIcon(str(image_path)))
            button.clicked.connect(lambda _=False, ct=chart_type: self._choose(ct))
            grid.addWidget(button, idx // 3, idx % 3)

        layout.addLayout(grid, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _choose(self, chart_type: str) -> None:
        self.selected_chart_type = chart_type
        self.accept()


class FeatureSelectionDialog(QDialog):
    """记录特征、标签、X/Y/Z、采样和归一化配置，但不删除原始数据列。"""

    def __init__(self, df: pd.DataFrame, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("选择特征 / 标签 / X-Y-Z / 样本")
        self.setMinimumSize(740, 660)
        self.source_df = df
        self.selected_features: list[str] = []
        self.selected_label: str | None = None
        self.selected_x: str | None = None
        self.selected_y: str | None = None
        self.selected_z: str | None = None
        self.normalization: str = "无"
        self.sample_limit: int = 0
        self.sample_mode: str = "全部"
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint = QLabel(
            "选择特征列、标签列，并可按需指定图表的 X/Y/Z 字段。"
            "不勾选的字段不会从数据表中删除，下次仍可重新选择。"
            "X/Y/Z 都是可选项：二维图通常只需要 X/Y，三维图才需要 Z；保持“默认”时系统会自动匹配。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("Subtle")
        layout.addWidget(hint)

        form = QFormLayout()
        self.feature_list = QListWidget()
        self.feature_list.setSelectionMode(QAbstractItemView.MultiSelection)
        self.feature_list.setMinimumHeight(260)

        numeric_cols = list(map(str, self.source_df.select_dtypes("number").columns))
        all_cols = list(map(str, self.source_df.columns))
        for pseudo_col in ["样本序号", "样本数量", "SampleIndex"]:
            if pseudo_col not in all_cols:
                all_cols.append(pseudo_col)
        for col in all_cols:
            item = QListWidgetItem(col)
            item.setCheckState(Qt.Checked if col in numeric_cols else Qt.Unchecked)
            self.feature_list.addItem(item)

        self.label_box = QComboBox()
        self.label_box.addItem("不选择标签列")
        self.label_box.addItems(all_cols)

        def make_axis_box() -> QComboBox:
            box = QComboBox()
            box.addItem("默认")
            box.addItems(all_cols)
            return box

        self.x_box = make_axis_box()
        self.y_box = make_axis_box()
        self.z_box = make_axis_box()

        self.normalization_box = QComboBox()
        self.normalization_box.addItems(NORMALIZATION_METHODS)

        self.sample_mode_box = QComboBox()
        self.sample_mode_box.addItems(["全部", "前 N 行", "随机 N 行"])
        self.sample_spin = QSpinBox()
        self.sample_spin.setRange(1, max(1, len(self.source_df)))
        self.sample_spin.setValue(min(len(self.source_df), 500))

        form.addRow("特征列", self.feature_list)
        form.addRow("标签列", self.label_box)
        form.addRow("指定 X", self.x_box)
        form.addRow("指定 Y", self.y_box)
        form.addRow("指定 Z（三维图）", self.z_box)
        form.addRow("归一化", self.normalization_box)
        form.addRow("样本方式", self.sample_mode_box)
        form.addRow("样本数量", self.sample_spin)
        layout.addLayout(form)

        quick = QHBoxLayout()
        select_numeric_btn = QPushButton("选择全部数值列")
        select_numeric_btn.setObjectName("Secondary")
        select_numeric_btn.clicked.connect(self._select_numeric)
        select_all_btn = QPushButton("全选")
        select_all_btn.setObjectName("Secondary")
        select_all_btn.clicked.connect(self._select_all)
        clear_btn = QPushButton("清空")
        clear_btn.setObjectName("Secondary")
        clear_btn.clicked.connect(self._clear)
        quick.addWidget(select_numeric_btn)
        quick.addWidget(select_all_btn)
        quick.addWidget(clear_btn)
        layout.addLayout(quick)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._apply)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _select_numeric(self) -> None:
        numeric_cols = set(map(str, self.source_df.select_dtypes("number").columns))
        for i in range(self.feature_list.count()):
            item = self.feature_list.item(i)
            item.setCheckState(Qt.Checked if item.text() in numeric_cols else Qt.Unchecked)

    def _select_all(self) -> None:
        for i in range(self.feature_list.count()):
            self.feature_list.item(i).setCheckState(Qt.Checked)

    def _clear(self) -> None:
        for i in range(self.feature_list.count()):
            self.feature_list.item(i).setCheckState(Qt.Unchecked)

    @staticmethod
    def _axis_value(box: QComboBox) -> str | None:
        text = box.currentText().strip()
        return None if text == "默认" else text

    def _apply(self) -> None:
        features: list[str] = []
        for i in range(self.feature_list.count()):
            item = self.feature_list.item(i)
            if item.checkState() == Qt.Checked:
                features.append(item.text())

        label = self.label_box.currentText()
        if label == "不选择标签列":
            label = None

        self.selected_features = features
        self.selected_label = label
        self.selected_x = self._axis_value(self.x_box)
        self.selected_y = self._axis_value(self.y_box)
        self.selected_z = self._axis_value(self.z_box)
        self.normalization = self.normalization_box.currentText()
        self.sample_mode = self.sample_mode_box.currentText()
        self.sample_limit = 0 if self.sample_mode == "全部" else int(self.sample_spin.value())
        self.accept()


class StyleEditorDialog(QDialog):
    """图表样式设计器：按当前图表类型展示合理设置。"""

    def __init__(self, spec: ChartSpec, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"图表样式设计器 - {spec.chart_type}")
        self.setMinimumWidth(500)
        self.input_spec = spec
        self.saved_spec: ChartSpec | None = None
        self._build_ui()
        self._load_spec(spec)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        hint_map = {
            "折线图": "折线图默认只显示连续趋势线，不显示散点节点；可在这里调整线型、线宽、是否显示节点。",
            "散点图": "散点图主要调整点大小、点类型、配色和背景。",
            "柱状图": "柱状图会自动按分类聚合数值，避免类别太多导致混乱；可设置显示前 N 个类别和数值标签。",
            "水平柱状图": "水平柱状图适合类别名称较长的分组比较；可设置显示前 N 个类别和数值标签。",
            "箱线图": "箱线图适合查看一个或多个数值特征的分布、离群点和组间差异。",
            "饼图": "饼图会自动按分类聚合并限制类别数量；可设置环形图、显示前 N 个类别和百分比标签。",
            "热力图": "热力图会读取所有数值列并计算相关系数；可选择 Spearman、Pearson 或 Kendall。",
            "三维散点图": "三维散点图需要 X、Y、Z 三个数值列；可调整点大小、点类型和配色。",
            "曲面图": "曲面图需要 X、Y、Z 三个数值列；适合连续采样或较密集的三维数据。",
        }
        hint = QLabel(hint_map.get(self.input_spec.chart_type, "根据当前图表类型调整样式。"))
        hint.setWordWrap(True)
        hint.setObjectName("Subtle")
        layout.addWidget(hint)

        form = QFormLayout()
        self.palette_box = QComboBox(); self.palette_box.addItems(PALETTE_NAMES)
        self.background_box = QComboBox(); self.background_box.addItems(BACKGROUND_STYLES)
        self.value_label_check = QCheckBox("显示数值标签 / 注释")
        form.addRow("配色方案", self.palette_box)
        form.addRow("背景风格", self.background_box)

        self.line_style_box = None
        self.line_width_spin = None
        self.show_line_markers_check = None
        self.marker_box = None
        self.point_size_spin = None
        self.bar_top_n_spin = None
        self.pie_top_n_spin = None
        self.donut_check = None
        self.corr_method_box = None
        self.heatmap_max_features_spin = None
        self.heatmap_annotate_check = None
        self.heatmap_decimals_spin = None
        self.surface_alpha_spin = None

        chart_type = self.input_spec.chart_type

        if chart_type == "折线图":
            self.line_style_box = QComboBox(); self.line_style_box.addItems(LINE_STYLES)
            self.line_width_spin = QDoubleSpinBox(); self.line_width_spin.setRange(0.5, 8.0); self.line_width_spin.setSingleStep(0.2)
            self.show_line_markers_check = QCheckBox("显示节点标记")
            form.addRow("线类型", self.line_style_box)
            form.addRow("线宽", self.line_width_spin)
            form.addRow("", self.show_line_markers_check)
            form.addRow("", self.value_label_check)

        elif chart_type == "散点图":
            self.marker_box = QComboBox(); self.marker_box.addItems(MARKER_STYLES)
            self.point_size_spin = QSpinBox(); self.point_size_spin.setRange(10, 300); self.point_size_spin.setSingleStep(5)
            form.addRow("点类型", self.marker_box)
            form.addRow("点大小", self.point_size_spin)

        elif chart_type in {"柱状图", "水平柱状图"}:
            self.bar_top_n_spin = QSpinBox(); self.bar_top_n_spin.setRange(3, 80)
            form.addRow("最多显示类别数", self.bar_top_n_spin)
            form.addRow("", self.value_label_check)

        elif chart_type == "箱线图":
            self.heatmap_max_features_spin = QSpinBox(); self.heatmap_max_features_spin.setRange(1, 40)
            form.addRow("最多显示特征数", self.heatmap_max_features_spin)

        elif chart_type == "饼图":
            self.pie_top_n_spin = QSpinBox(); self.pie_top_n_spin.setRange(3, 20)
            self.donut_check = QCheckBox("环形饼图")
            form.addRow("最多显示类别数", self.pie_top_n_spin)
            form.addRow("", self.donut_check)
            form.addRow("", self.value_label_check)

        elif chart_type == "热力图":
            self.corr_method_box = QComboBox(); self.corr_method_box.addItems(CORRELATION_METHODS)
            self.heatmap_max_features_spin = QSpinBox(); self.heatmap_max_features_spin.setRange(2, 120)
            self.heatmap_decimals_spin = QSpinBox(); self.heatmap_decimals_spin.setRange(2, 6)
            self.heatmap_annotate_check = QCheckBox("显示相关系数数值")
            form.addRow("相关系数", self.corr_method_box)
            form.addRow("最多显示特征数", self.heatmap_max_features_spin)
            form.addRow("小数位数", self.heatmap_decimals_spin)
            form.addRow("", self.heatmap_annotate_check)

        elif chart_type == "三维散点图":
            self.marker_box = QComboBox(); self.marker_box.addItems(MARKER_STYLES)
            self.point_size_spin = QSpinBox(); self.point_size_spin.setRange(10, 500); self.point_size_spin.setSingleStep(5)
            form.addRow("点类型", self.marker_box)
            form.addRow("点大小", self.point_size_spin)

        elif chart_type == "曲面图":
            self.point_size_spin = QSpinBox(); self.point_size_spin.setRange(6, 200); self.point_size_spin.setSingleStep(4)
            self.surface_alpha_spin = QDoubleSpinBox(); self.surface_alpha_spin.setRange(0.1, 1.0); self.surface_alpha_spin.setSingleStep(0.05)
            form.addRow("辅助点大小", self.point_size_spin)
            form.addRow("曲面透明度", self.surface_alpha_spin)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _load_spec(self, spec: ChartSpec) -> None:
        self.palette_box.setCurrentText(spec.palette)
        self.background_box.setCurrentText(spec.background_style)
        self.value_label_check.setChecked(spec.show_value_labels)

        if self.line_style_box:
            self.line_style_box.setCurrentText(spec.line_style)
        if self.line_width_spin:
            self.line_width_spin.setValue(spec.line_width)
        if self.show_line_markers_check:
            self.show_line_markers_check.setChecked(spec.show_line_markers)
        if self.marker_box:
            self.marker_box.setCurrentText(spec.marker_style)
        if self.point_size_spin:
            self.point_size_spin.setValue(spec.point_size)
        if self.bar_top_n_spin:
            self.bar_top_n_spin.setValue(spec.bar_top_n)
        if self.pie_top_n_spin:
            self.pie_top_n_spin.setValue(spec.pie_top_n)
        if self.donut_check:
            self.donut_check.setChecked(spec.donut)
        if self.corr_method_box:
            self.corr_method_box.setCurrentText(spec.corr_method)
        if self.heatmap_max_features_spin:
            self.heatmap_max_features_spin.setValue(spec.heatmap_max_features)
        if self.heatmap_annotate_check:
            self.heatmap_annotate_check.setChecked(spec.heatmap_annotate)
        if self.heatmap_decimals_spin:
            self.heatmap_decimals_spin.setValue(spec.heatmap_decimals)
        if self.surface_alpha_spin:
            self.surface_alpha_spin.setValue(spec.surface_alpha)

    def _save(self) -> None:
        self.saved_spec = replace(
            self.input_spec,
            palette=self.palette_box.currentText(),
            background_style=self.background_box.currentText(),
            show_value_labels=self.value_label_check.isChecked(),
            line_style=self.line_style_box.currentText() if self.line_style_box else self.input_spec.line_style,
            line_width=float(self.line_width_spin.value()) if self.line_width_spin else self.input_spec.line_width,
            show_line_markers=self.show_line_markers_check.isChecked() if self.show_line_markers_check else self.input_spec.show_line_markers,
            marker_style=self.marker_box.currentText() if self.marker_box else self.input_spec.marker_style,
            point_size=int(self.point_size_spin.value()) if self.point_size_spin else self.input_spec.point_size,
            bar_top_n=int(self.bar_top_n_spin.value()) if self.bar_top_n_spin else self.input_spec.bar_top_n,
            pie_top_n=int(self.pie_top_n_spin.value()) if self.pie_top_n_spin else self.input_spec.pie_top_n,
            donut=self.donut_check.isChecked() if self.donut_check else self.input_spec.donut,
            corr_method=self.corr_method_box.currentText() if self.corr_method_box else self.input_spec.corr_method,
            heatmap_max_features=int(self.heatmap_max_features_spin.value()) if self.heatmap_max_features_spin else self.input_spec.heatmap_max_features,
            heatmap_annotate=self.heatmap_annotate_check.isChecked() if self.heatmap_annotate_check else self.input_spec.heatmap_annotate,
            heatmap_decimals=int(self.heatmap_decimals_spin.value()) if self.heatmap_decimals_spin else self.input_spec.heatmap_decimals,
            surface_alpha=float(self.surface_alpha_spin.value()) if self.surface_alpha_spin else self.input_spec.surface_alpha,
        )
        self.accept()
