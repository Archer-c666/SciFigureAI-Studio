from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from matplotlib.figure import Figure

from .charting import CHART_TYPES, LANGUAGES, STYLEABLE_CHARTS, THEMES, ChartEngine, ChartSpec
from .codegen import generate_reproducible_code
from .config import load_config
from .data_model import DataProject, PandasTableModel
from .dialogs import ChartTypeDialog, FeatureSelectionDialog, LLMConfigDialog, ManualDataDialog, StyleEditorDialog
from .llm import LLMChartAssistant
from .styles import APP_QSS
from .widgets import ChatInput, MetricCard
from .workers import AIPlotWorker, PlotWorker


class SciFigureStudio(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = load_config()
        self.project = DataProject()
        self.engine = ChartEngine()
        self.assistant = LLMChartAssistant(self.config)
        self.current_spec = ChartSpec()
        self.table_model = PandasTableModel()
        self.worker = None
        self.assets_dir = Path(__file__).resolve().parents[1] / "assets"

        self.setWindowTitle("SciFigure AI Studio - 科研绘图工作台")
        icon_path = self.assets_dir / "pixel_style.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        self.resize(1540, 940)
        self.setStyleSheet(APP_QSS)
        self._build_ui()
        self._build_menu()
        self._sync_controls_from_spec(self.current_spec)
        self._append_chat("系统", "欢迎使用工作台")

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("文件")
        open_action = QAction("打开数据文件", self)
        open_action.triggered.connect(self.open_data)
        file_menu.addAction(open_action)
        manual_action = QAction("手动输入数据", self)
        manual_action.triggered.connect(self.open_manual_data)
        file_menu.addAction(manual_action)
        export_action = QAction("导出图像", self)
        export_action.triggered.connect(self.export_figure)
        file_menu.addAction(export_action)

        settings_menu = self.menuBar().addMenu("设置")
        model_action = QAction("大模型配置", self)
        model_action.triggered.connect(self.open_model_config)
        settings_menu.addAction(model_action)
        style_action = QAction("图表样式设计器", self)
        style_action.triggered.connect(self.open_style_editor)
        settings_menu.addAction(style_action)

        view_menu = self.menuBar().addMenu("视图")
        reset_action = QAction("重置画布", self)
        reset_action.triggered.connect(self.reset_canvas)
        view_menu.addAction(reset_action)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(12)
        self.setCentralWidget(root)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel("SciFigure AI Studio")
        title.setObjectName("AppTitle")
        subtitle = QLabel("生成绘图 · 论文级风格 · 手动录入 · 样式设计器 · 代码可复现")
        subtitle.setObjectName("Subtle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header.addLayout(title_block)
        header.addStretch(1)
        self.model_label = QLabel(f"模型：{self.config.model if self.config.api_key else '本地规则模式'}")
        self.model_label.setObjectName("Subtle")
        header.addWidget(self.model_label)
        config_btn = QPushButton("⚙️ 大模型配置")
        config_btn.setObjectName("Secondary")
        config_btn.clicked.connect(self.open_model_config)
        header.addWidget(config_btn)
        root_layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(splitter, 1)
        splitter.addWidget(self._build_side_panel())
        splitter.addWidget(self._build_workspace())
        splitter.addWidget(self._build_inspector())
        splitter.setSizes([280, 900, 330])

    def _build_side_panel(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("SidePanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        open_btn = QPushButton("📂 导入数据")
        open_btn.clicked.connect(self.open_data)
        paste_btn = QPushButton("📋 从剪贴板读取")
        paste_btn.setObjectName("Secondary")
        paste_btn.clicked.connect(self.load_clipboard)
        manual_btn = QPushButton("✍️ 手动输入数据")
        manual_btn.setObjectName("Secondary")
        manual_btn.clicked.connect(self.open_manual_data)
        feature_btn = QPushButton("选择特征 / 标签 / X-Y-Z / 样本")
        feature_btn.setObjectName("Secondary")
        feature_btn.clicked.connect(self.open_feature_selection)

        layout.addWidget(open_btn)
        layout.addWidget(paste_btn)
        layout.addWidget(manual_btn)
        layout.addWidget(feature_btn)

        self.dataset_label = QLabel("当前数据：未加载")
        self.dataset_label.setWordWrap(True)
        self.dataset_label.setObjectName("Subtle")
        layout.addWidget(self.dataset_label)

        metric_grid = QGridLayout()
        self.metric_rows = MetricCard("行数")
        self.metric_cols = MetricCard("列数")
        self.metric_missing = MetricCard("缺失率")
        self.metric_dup = MetricCard("重复行")
        metric_grid.addWidget(self.metric_rows, 0, 0)
        metric_grid.addWidget(self.metric_cols, 0, 1)
        metric_grid.addWidget(self.metric_missing, 1, 0)
        metric_grid.addWidget(self.metric_dup, 1, 1)
        layout.addLayout(metric_grid)

        profile_title = QLabel("字段画像")
        profile_title.setStyleSheet("font-weight: 800; margin-top: 8px;")
        layout.addWidget(profile_title)
        self.profile_text = QTextEdit()
        self.profile_text.setReadOnly(True)
        self.profile_text.setMinimumHeight(160)
        layout.addWidget(self.profile_text)

        batch_btn = QPushButton("⚡ 批量导出数值列")
        batch_btn.setObjectName("Secondary")
        batch_btn.clicked.connect(self.batch_export_numeric)
        layout.addWidget(batch_btn)

        mascot_path = self.assets_dir / "pixel_mascot.png"
        if mascot_path.exists():
            mascot = QLabel()
            mascot.setObjectName("MascotCard")
            mascot.setAlignment(Qt.AlignCenter)
            pix = QPixmap(str(mascot_path)).scaled(190, 190, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            mascot.setPixmap(pix)
            layout.addWidget(mascot)
        layout.addStretch(1)
        return panel

    def _build_workspace(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        content_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(content_splitter, 1)

        preview_block = QWidget()
        preview_block_layout = QVBoxLayout(preview_block)
        preview_block_layout.setContentsMargins(0, 0, 0, 0)
        preview_block_layout.setSpacing(8)

        preview_header = QHBoxLayout()
        preview_title_box = QVBoxLayout()
        preview_title = QLabel("图像预览")
        preview_title.setStyleSheet("font-size: 16px; font-weight: 800;")
        self.preview_status = QLabel("尚未绘图。导入数据后，请点击“按参数绘制”或在下方让数据助手生成图表。")
        self.preview_status.setObjectName("Subtle")
        self.preview_status.setWordWrap(True)
        preview_title_box.addWidget(preview_title)
        preview_title_box.addWidget(self.preview_status)
        preview_header.addLayout(preview_title_box)
        preview_header.addStretch(1)
        self.preview_meta = QLabel("")
        self.preview_meta.setObjectName("Subtle")
        preview_header.addWidget(self.preview_meta)
        preview_block_layout.addLayout(preview_header)

        self.tabs = QTabWidget()
        preview_block_layout.addWidget(self.tabs, 1)

        fig_page = QWidget()
        fig_layout = QVBoxLayout(fig_page)
        fig_layout.setContentsMargins(8, 8, 8, 8)
        fig_layout.setSpacing(8)

        preview_card = QFrame()
        preview_card.setObjectName("Card")
        preview_card_layout = QVBoxLayout(preview_card)
        preview_card_layout.setContentsMargins(10, 10, 10, 10)
        preview_card_layout.setSpacing(8)

        self.figure = Figure(figsize=(7.2, 4.8), dpi=160, constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(760, 500)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.preview_scroll = QScrollArea()
        self.preview_scroll.setWidgetResizable(True)
        self.preview_scroll.setAlignment(Qt.AlignCenter)
        self.preview_scroll.setFrameShape(QFrame.NoFrame)
        self.preview_canvas_host = QWidget()
        self.preview_canvas_layout = QVBoxLayout(self.preview_canvas_host)
        self.preview_canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_canvas_layout.setSpacing(0)
        self.preview_canvas_layout.addWidget(self.canvas, 0, Qt.AlignCenter)
        self.preview_scroll.setWidget(self.preview_canvas_host)

        preview_card_layout.addWidget(self.toolbar)
        preview_card_layout.addWidget(self.preview_scroll, 1)
        fig_layout.addWidget(preview_card, 1)
        self.tabs.addTab(fig_page, "图像预览")

        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        table_layout.setContentsMargins(10, 10, 10, 10)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_view)
        self.tabs.addTab(table_page, "数据预览")

        code_page = QWidget()
        code_layout = QVBoxLayout(code_page)
        code_layout.setContentsMargins(10, 10, 10, 10)
        self.code_view = QPlainTextEdit()
        self.code_view.setReadOnly(False)
        code_layout.addWidget(self.code_view)
        copy_btn = QPushButton("复制复现代码")
        copy_btn.setObjectName("Secondary")
        copy_btn.clicked.connect(self.copy_code)
        code_layout.addWidget(copy_btn)
        self.tabs.addTab(code_page, "复现代码")

        chat_area = QFrame()
        chat_area.setObjectName("Card")
        chat_layout = QVBoxLayout(chat_area)
        chat_layout.setContentsMargins(12, 12, 12, 12)
        chat_label = QLabel("数据助手 / 生成图表")
        chat_label.setStyleSheet("font-weight: 800;")
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMinimumHeight(170)
        self.chat_log.setMaximumHeight(210)
        self.prompt_input = ChatInput()
        self.prompt_input.setPlaceholderText("可以咨询数据，也可以生成图表。例如：绘制特征之间的热力图；画二维散点图；画 X/Y/Z 的三维散点图；当前数据适合画什么？Enter 发送，Shift+Enter 换行。")
        self.prompt_input.setMaximumHeight(86)
        self.prompt_input.send_requested.connect(self.run_ai_plot)
        send_btn = QPushButton("发送 / 生成图表")
        send_btn.clicked.connect(self.run_ai_plot)
        chat_layout.addWidget(chat_label)
        chat_layout.addWidget(self.chat_log)
        chat_layout.addWidget(self.prompt_input)
        chat_layout.addWidget(send_btn)

        content_splitter.addWidget(preview_block)
        content_splitter.addWidget(chat_area)
        content_splitter.setSizes([760, 210])
        return box

    def _build_inspector(self) -> QWidget:
        panel = QFrame()
        panel.setObjectName("Inspector")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("图表参数")
        title.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        self.chart_type_box = QComboBox(); self.chart_type_box.addItems(CHART_TYPES)
        self.chart_type_box.setVisible(False)
        self.theme_box = QComboBox(); self.theme_box.addItems(list(THEMES.keys()))
        self.language_box = QComboBox(); self.language_box.addItems(LANGUAGES)
        self.x_box = QComboBox(); self.y_box = QComboBox(); self.z_box = QComboBox()
        self.title_edit = QLineEdit()
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        self.zlabel_edit = QLineEdit()
        self.width_spin = QDoubleSpinBox(); self.width_spin.setRange(2.0, 20.0); self.width_spin.setSingleStep(0.2); self.width_spin.setValue(7.2)
        self.height_spin = QDoubleSpinBox(); self.height_spin.setRange(2.0, 20.0); self.height_spin.setSingleStep(0.2); self.height_spin.setValue(4.8)
        self.dpi_spin = QSpinBox(); self.dpi_spin.setRange(120, 1200); self.dpi_spin.setValue(180)
        self.grid_check = QCheckBox("显示网格"); self.grid_check.setChecked(True)
        self.legend_check = QCheckBox("显示图例"); self.legend_check.setChecked(True)

        self.chart_example_btn = QPushButton(f"通过例图选择图表类型：{self.chart_type_box.currentText()}")
        self.chart_example_btn.setObjectName("Secondary")
        self.chart_example_btn.clicked.connect(self.open_chart_type_selector)

        for label, widget in [
            ("", self.chart_example_btn),
            ("主题", self.theme_box),
            ("图表语言", self.language_box),
            ("X 数据列（可选）", self.x_box),
            ("Y 数据列（可选）", self.y_box),
            ("Z 数据列（可选，三维图）", self.z_box),
            ("标题", self.title_edit),
            ("X 标题", self.xlabel_edit),
            ("Y 标题", self.ylabel_edit),
            ("Z 标题（三维图）", self.zlabel_edit),
            ("宽度", self.width_spin),
            ("高度", self.height_spin),
            ("DPI", self.dpi_spin),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)

        axis_hint = QLabel("X/Y/Z 字段不是必填项。保持“默认”时，系统会根据当前图表类型和数据结构自动选择更合适的字段。")
        axis_hint.setWordWrap(True)
        axis_hint.setObjectName("Subtle")
        layout.addWidget(axis_hint)

        layout.addWidget(self.grid_check)
        layout.addWidget(self.legend_check)

        self.style_btn = QPushButton("打开样式设计器")
        self.style_btn.setObjectName("Secondary")
        self.style_btn.clicked.connect(self.open_style_editor)
        layout.addWidget(self.style_btn)
        self.chart_type_box.currentTextChanged.connect(self._update_style_button_state)

        manual_btn = QPushButton("按参数绘制")
        manual_btn.clicked.connect(self.run_manual_plot)
        export_btn = QPushButton("导出 PNG/SVG/PDF/TIFF")
        export_btn.setObjectName("Secondary")
        export_btn.clicked.connect(self.export_figure)
        reset_btn = QPushButton("重置画布")
        reset_btn.setObjectName("Danger")
        reset_btn.clicked.connect(self.reset_canvas)
        layout.addWidget(manual_btn)
        layout.addWidget(export_btn)
        layout.addWidget(reset_btn)
        layout.addStretch(1)
        return panel

    def _update_style_button_state(self) -> None:
        chart_type = self.chart_type_box.currentText()
        self.style_btn.setEnabled(chart_type in STYLEABLE_CHARTS)
        self.style_btn.setText("打开样式设计器" if chart_type in STYLEABLE_CHARTS else "当前图表无需样式设计器")
        if hasattr(self, "chart_example_btn"):
            self.chart_example_btn.setText(f"通过例图选择图表类型：{chart_type}")


    def open_chart_type_selector(self) -> None:
        dialog = ChartTypeDialog(self.assets_dir, self.chart_type_box.currentText(), self)
        if dialog.exec_() == dialog.Accepted and dialog.selected_chart_type:
            self.chart_type_box.setCurrentText(dialog.selected_chart_type)
            self._append_chat("系统", f"已选择图表类型：{dialog.selected_chart_type}")

    def open_model_config(self) -> None:
        dialog = LLMConfigDialog(self.config, self)
        if dialog.exec_() == dialog.Accepted and dialog.saved_config is not None:
            self.config = load_config()
            self.assistant.update_config(self.config)
            self.model_label.setText(f"模型：{self.config.model if self.config.api_key else '本地规则模式'}")
            self._append_chat("系统", "大模型配置已保存并生效。")

    def open_style_editor(self) -> None:
        chart_type = self.chart_type_box.currentText()
        if chart_type not in STYLEABLE_CHARTS:
            QMessageBox.information(self, "样式设计器", "当前图表类型没有开放样式编辑。请通过例图选择支持的图表类型。")
            return
        base_spec = self._spec_from_controls()
        dialog = StyleEditorDialog(base_spec, self)
        if dialog.exec_() == dialog.Accepted and dialog.saved_spec is not None:
            self.current_spec = dialog.saved_spec
            self.run_manual_plot()

    def open_manual_data(self) -> None:
        dialog = ManualDataDialog(self)
        if dialog.exec_() == dialog.Accepted and dialog.df is not None:
            try:
                df = self.project.load_dataframe(dialog.df, name="手动输入数据")
                self._on_data_loaded(df)
            except Exception as exc:
                self._show_error("手动数据导入失败", str(exc))


    def open_feature_selection(self) -> None:
        if not self._require_data():
            return
        dialog = FeatureSelectionDialog(self.project.df, self)
        if dialog.exec_() == dialog.Accepted:
            try:
                updated = self.current_spec.to_dict()
                updated.update({
                    "feature_cols": dialog.selected_features,
                    "x": dialog.selected_x,
                    "y": dialog.selected_y,
                    "z": dialog.selected_z,
                    "normalization": dialog.normalization,
                    "sample_limit": dialog.sample_limit,
                    "sample_mode": dialog.sample_mode,
                })
                self.current_spec = ChartSpec(**updated)
                self._sync_controls_from_spec(self.current_spec)

                details = []
                if dialog.selected_features:
                    details.append(f"特征列：{', '.join(dialog.selected_features)}")
                else:
                    details.append("特征列：默认")
                if dialog.selected_label:
                    details.append(f"标签列：{dialog.selected_label}")
                if dialog.selected_x:
                    details.append(f"X：{dialog.selected_x}")
                if dialog.selected_y:
                    details.append(f"Y：{dialog.selected_y}")
                if dialog.selected_z:
                    details.append(f"Z：{dialog.selected_z}")
                if dialog.normalization != "无":
                    details.append(f"归一化：{dialog.normalization}")
                if dialog.sample_mode != "全部":
                    details.append(f"样本：{dialog.sample_mode} {dialog.sample_limit} 行")
                else:
                    details.append("样本：全部")
                self._append_chat("系统", "已更新绘图选择：" + "；".join(details) + "。原始数据列仍全部保留。")
            except Exception as exc:
                self._show_error("数据选择失败", str(exc))

    def open_data(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择数据文件",
            "",
            "Data files (*.csv *.txt *.xlsx *.xls *.parquet *.json);;All files (*.*)",
        )
        if not path:
            return
        try:
            df = self.project.load(path)
            self._on_data_loaded(df)
        except Exception as exc:
            self._show_error("导入失败", str(exc))

    def load_clipboard(self) -> None:
        try:
            df = self.project.load_clipboard()
            self._on_data_loaded(df)
        except Exception as exc:
            self._show_error("剪贴板读取失败", str(exc))

    def _on_data_loaded(self, df: pd.DataFrame) -> None:
        self.table_model.set_dataframe(df)
        self._refresh_profile()
        self._refresh_column_boxes()
        self.dataset_label.setText(f"当前数据：{self.project.name}")
        self.tabs.setCurrentIndex(1)
        spec = ChartEngine.smart_default_spec(df, language=self.language_box.currentText() if hasattr(self, "language_box") else "纯科研英语")
        self.current_spec = spec
        self._sync_controls_from_spec(spec)
        self._update_code()
        self._update_preview_info(None)
        self._append_chat("系统", f"已加载 {self.project.name}，共 {len(df)} 行、{len(df.columns)} 列。系统已完成字段分析，但不会自动画图；你可以点击“按参数绘制”，或在下方让数据助手生成图表。")

    def _refresh_profile(self) -> None:
        profile = self.project.profile()
        self.metric_rows.set_value(str(profile.rows))
        self.metric_cols.set_value(str(profile.columns))
        self.metric_missing.set_value(f"{profile.missing_ratio:.1%}")
        self.metric_dup.set_value(str(profile.duplicate_rows))
        self.profile_text.setMarkdown(profile.to_markdown())

    def _refresh_column_boxes(self) -> None:
        cols = ["默认"] + (list(self.project.df.columns) if self.project.df is not None else [])
        for pseudo_col in ["样本序号", "样本数量", "SampleIndex"]:
            if pseudo_col not in cols:
                cols.append(pseudo_col)
        for box in [self.x_box, self.y_box, self.z_box]:
            current = box.currentText()
            box.blockSignals(True)
            box.clear()
            box.addItems(cols)
            if current in cols:
                box.setCurrentText(current)
            else:
                box.setCurrentText("默认")
            box.blockSignals(False)


    def _spec_from_controls(self) -> ChartSpec:
        def val(box: QComboBox) -> str | None:
            text = box.currentText().strip()
            return None if not text or text == "默认" else text

        selected_chart_type = self.chart_type_box.currentText()
        base = self.current_spec.to_dict()
        base.update({
            "chart_type": selected_chart_type,
            "x": val(self.x_box),
            "y": val(self.y_box),
            "z": val(self.z_box),
            "title": self.title_edit.text().strip(),
            "xlabel": self.xlabel_edit.text().strip(),
            "ylabel": self.ylabel_edit.text().strip(),
            "zlabel": self.zlabel_edit.text().strip(),
            "theme": self.theme_box.currentText(),
            "language": self.language_box.currentText(),
            "width": float(self.width_spin.value()),
            "height": float(self.height_spin.value()),
            "dpi": int(self.dpi_spin.value()),
            "grid": self.grid_check.isChecked(),
            "legend": self.legend_check.isChecked(),
            "log_x": False,
            "log_y": False,
            "sort_x": False,
            "error_col": None,
        })
        return ChartSpec(**base)

    def _sync_controls_from_spec(self, spec: ChartSpec) -> None:
        def set_combo(box: QComboBox, value: str | None) -> None:
            target = value or "默认"
            idx = box.findText(target)
            if idx >= 0:
                box.setCurrentIndex(idx)
        set_combo(self.chart_type_box, spec.chart_type)
        if hasattr(self, "chart_example_btn"):
            self.chart_example_btn.setText(f"通过例图选择图表类型：{self.chart_type_box.currentText()}")
        set_combo(self.theme_box, spec.theme)
        set_combo(self.language_box, spec.language)
        set_combo(self.x_box, spec.x)
        set_combo(self.y_box, spec.y)
        set_combo(self.z_box, spec.z)
        self.title_edit.setText(spec.title)
        self.xlabel_edit.setText(spec.xlabel)
        self.ylabel_edit.setText(spec.ylabel)
        self.zlabel_edit.setText(spec.zlabel)
        self.width_spin.setValue(spec.width)
        self.height_spin.setValue(spec.height)
        self.dpi_spin.setValue(spec.dpi)
        self.grid_check.setChecked(spec.grid)
        self.legend_check.setChecked(spec.legend)
        self._update_style_button_state()

    def run_ai_plot(self) -> None:
        if not self._require_data():
            return
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            self._append_chat("系统", "请输入数据咨询或绘图需求后再发送。")
            return
        self.prompt_input.clear()
        self._append_chat("你", prompt)
        self._set_busy(True)
        self.worker = AIPlotWorker(self.project.df, prompt, self.language_box.currentText(), self.assistant, self.engine)
        self.worker.finished_ok.connect(self._on_ai_plot_ready)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def run_manual_plot(self) -> None:
        if not self._require_data():
            return
        spec = self._spec_from_controls()
        self._set_busy(True)
        self.worker = PlotWorker(self.project.df, spec, self.engine)
        self.worker.finished_ok.connect(self._on_manual_plot_ready)
        self.worker.failed.connect(self._on_worker_failed)
        self.worker.start()

    def _on_ai_plot_ready(self, result, fig: Figure, spec: ChartSpec) -> None:
        self._set_busy(False)
        source = "大模型" if result.used_llm else "本地规则"

        # 普通数据咨询：只在对话区回答，不改画布。
        if getattr(result, "kind", "plot") == "answer" or fig is None or spec is None:
            self._append_chat("数据助手", f"{result.message}<br><b>来源：</b>{source}")
            return

        self._replace_figure(fig)
        self.current_spec = spec
        self._sync_controls_from_spec(spec)
        self._update_code()
        self._update_preview_info(spec)
        self.tabs.setCurrentIndex(0)
        self._append_chat("生成器", f"{result.message}<br><b>方案来源：</b>{source}<br><b>图表：</b>{spec.chart_type}<br><b>语言：</b>{spec.language}")

    def _on_manual_plot_ready(self, fig: Figure, spec: ChartSpec) -> None:
        self._set_busy(False)
        self._replace_figure(fig)
        self.current_spec = spec
        self._sync_controls_from_spec(spec)
        self._update_code()
        self._update_preview_info(spec)
        self.tabs.setCurrentIndex(0)

    def _on_worker_failed(self, detail: str) -> None:
        self._set_busy(False)
        # 优先给用户展示最后一行清晰错误，完整堆栈仍保留在弹窗详情中。
        lines = [line.strip() for line in detail.strip().splitlines() if line.strip()]
        short = lines[-1] if lines else detail
        self._append_chat("错误", f"{short}<br>当前数据可能不适合这种图表，或字段类型不满足绘图要求。")
        self._show_error("无法绘制", short)

    def _replace_figure(self, fig: Figure) -> None:
        plt.close(self.figure)
        self.figure = fig
        old_canvas = self.canvas
        old_toolbar = self.toolbar
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setMinimumSize(760, 500)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.preview_canvas_layout.replaceWidget(old_canvas, self.canvas)
        self.preview_canvas_layout.setAlignment(self.canvas, Qt.AlignCenter)
        self.preview_scroll.widget().adjustSize()
        card_layout = old_toolbar.parentWidget().layout() if old_toolbar.parentWidget() else None
        if card_layout is not None:
            card_layout.replaceWidget(old_toolbar, self.toolbar)
        old_toolbar.deleteLater()
        old_canvas.deleteLater()
        self.canvas.draw_idle()

    def _update_preview_info(self, spec: ChartSpec | None) -> None:
        if spec is None or self.engine.last_figure is None:
            self.preview_status.setText("尚未绘图。导入数据后，请点击“按参数绘制”或在下方让数据助手生成图表。")
            self.preview_meta.setText("")
            return

        dims = f"{spec.width:.1f} × {spec.height:.1f} in · {spec.dpi} DPI"
        axes = [f"X={spec.x}" if spec.x else None, f"Y={spec.y}" if spec.y else None, f"Z={spec.z}" if spec.z else None]
        axes_text = " · ".join([a for a in axes if a]) or "字段默认匹配"
        legend_text = "显示图例" if spec.legend else "不显示图例"
        self.preview_status.setText(f"当前预览：{spec.chart_type}，可继续在右侧微调参数或打开样式设计器。")
        self.preview_meta.setText(f"{axes_text} · {legend_text} · {dims}")

    def _update_code(self) -> None:
        data_path = str(self.project.path) if self.project.path else None
        self.code_view.setPlainText(generate_reproducible_code(self.current_spec, data_path))

    def export_figure(self) -> None:
        if self.engine.last_figure is None:
            self._show_error("无法导出", "当前没有可导出的图像。")
            return
        path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "导出图像",
            "figure.png",
            "PNG (*.png);;SVG (*.svg);;PDF (*.pdf);;TIFF (*.tiff)",
        )
        if not path:
            return
        suffix = Path(path).suffix.lower()
        if not suffix:
            ext = {"PNG": ".png", "SVG": ".svg", "PDF": ".pdf", "TIFF": ".tiff"}
            for key, value in ext.items():
                if key in selected_filter:
                    path += value
                    break
        try:
            self.engine.last_figure.savefig(path, dpi=self.config.export_dpi, bbox_inches="tight")
            self._append_chat("系统", f"已导出：{path}")
        except Exception as exc:
            self._show_error("导出失败", str(exc))

    def batch_export_numeric(self) -> None:
        if not self._require_data():
            return
        df = self.project.df
        numeric_cols = list(df.select_dtypes("number").columns)
        if not numeric_cols:
            self._show_error("批量导出失败", "当前数据没有数值列。")
            return
        folder = QFileDialog.getExistingDirectory(self, "选择批量导出目录")
        if not folder:
            return
        folder_path = Path(folder)
        x_col = self.current_spec.x or None
        try:
            for y_col in numeric_cols:
                if x_col == y_col:
                    continue
                spec = ChartSpec(
                    chart_type="折线图" if x_col else "直方图",
                    x=x_col or y_col,
                    y=y_col if x_col else None,
                    title=y_col,
                    theme=self.theme_box.currentText(),
                    language=self.language_box.currentText(),
                    palette=self.current_spec.palette,
                    line_style=self.current_spec.line_style,
                    marker_style=self.current_spec.marker_style,
                    background_style=self.current_spec.background_style,
                )
                fig = self.engine.render(df, spec)
                safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in y_col)
                fig.savefig(folder_path / f"{safe_name}.png", dpi=self.config.export_dpi, bbox_inches="tight")
                plt.close(fig)
            self._append_chat("系统", f"已批量导出 {len(numeric_cols)} 张图到：{folder}")
        except Exception as exc:
            self._show_error("批量导出失败", str(exc))

    def copy_code(self) -> None:
        QGuiApplication.clipboard().setText(self.code_view.toPlainText())
        self._append_chat("系统", "复现代码已复制到剪贴板。")

    def reset_canvas(self) -> None:
        self.figure.clear()
        self.canvas.draw_idle()
        self.engine.last_figure = None
        self._update_preview_info(None)
        self._append_chat("系统", "画布已重置。")

    def _require_data(self) -> bool:
        if not self.project.loaded:
            self._show_error("未加载数据", "请先导入 CSV、Excel、Parquet、JSON，或使用左侧“手动输入数据”。")
            return False
        return True

    def _set_busy(self, busy: bool) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor) if busy else QApplication.restoreOverrideCursor()
        self.statusBar().showMessage("正在生成图表..." if busy else "就绪")

    def _append_chat(self, who: str, text: str) -> None:
        self.chat_log.append(f"<p><b>{who}：</b>{text}</p>")

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)
