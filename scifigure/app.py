from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QGuiApplication
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
    QSplitter,
    QSpinBox,
    QTableView,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from matplotlib.figure import Figure

from .charting import CHART_TYPES, LANGUAGES, THEMES, ChartEngine, ChartSpec
from .codegen import generate_reproducible_code
from .config import load_config
from .data_model import DataProject, PandasTableModel
from .dialogs import LLMConfigDialog, ManualDataDialog
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

        self.setWindowTitle("SciFigure AI Studio - 科研绘图工作台")
        self.resize(1520, 920)
        self.setStyleSheet(APP_QSS)
        self._build_ui()
        self._build_menu()
        self._sync_controls_from_spec(self.current_spec)
        self._append_chat("系统", "欢迎使用重构版。导入文件、粘贴 Excel 表格或手动输入 X/Y 数据后，可以直接生成科研图，也可以在右侧精调参数。")

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
        subtitle = QLabel("大模型辅助 · 论文级绘图 · 手动录入 · 参数可控 · 代码可复现")
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
        splitter.setSizes([260, 880, 340])

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
        layout.addWidget(open_btn)
        layout.addWidget(paste_btn)
        layout.addWidget(manual_btn)

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
        self.profile_text.setMinimumHeight(170)
        layout.addWidget(self.profile_text)

        batch_btn = QPushButton("⚡ 批量导出数值列")
        batch_btn.setObjectName("Secondary")
        batch_btn.clicked.connect(self.batch_export_numeric)
        layout.addWidget(batch_btn)
        layout.addStretch(1)
        return panel

    def _build_workspace(self) -> QWidget:
        box = QWidget()
        layout = QVBoxLayout(box)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        fig_page = QWidget()
        fig_layout = QVBoxLayout(fig_page)
        fig_layout.setContentsMargins(10, 10, 10, 10)
        self.figure = Figure(figsize=(7.2, 4.8), dpi=140, constrained_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        fig_layout.addWidget(self.toolbar)
        fig_layout.addWidget(self.canvas, 1)
        self.tabs.addTab(fig_page, "图像预览")

        table_page = QWidget()
        table_layout = QVBoxLayout(table_page)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setAlternatingRowColors(True)
        table_layout.addWidget(self.table_view)
        self.tabs.addTab(table_page, "数据预览")

        code_page = QWidget()
        code_layout = QVBoxLayout(code_page)
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
        chat_label = QLabel("生成绘图指令")
        chat_label.setStyleSheet("font-weight: 800;")
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setMaximumHeight(150)
        self.prompt_input = ChatInput()
        self.prompt_input.setPlaceholderText("例如：画测试集 R2 与模型名称的柱状图，按打印方向分组，论文风格，显示误差棒。Enter 发送，Shift+Enter 换行。")
        self.prompt_input.setMaximumHeight(86)
        self.prompt_input.send_requested.connect(self.run_ai_plot)
        send_btn = QPushButton("✨ 生成图表")
        send_btn.clicked.connect(self.run_ai_plot)
        chat_layout.addWidget(chat_label)
        chat_layout.addWidget(self.chat_log)
        chat_layout.addWidget(self.prompt_input)
        chat_layout.addWidget(send_btn)
        layout.addWidget(chat_area)
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
        self.theme_box = QComboBox(); self.theme_box.addItems(list(THEMES.keys()))
        self.language_box = QComboBox(); self.language_box.addItems(LANGUAGES)
        self.x_box = QComboBox(); self.y_box = QComboBox(); self.y2_box = QComboBox(); self.hue_box = QComboBox(); self.error_box = QComboBox()
        self.agg_box = QComboBox(); self.agg_box.addItems(["none", "mean", "median", "sum", "count"])
        self.title_edit = QLineEdit()
        self.xlabel_edit = QLineEdit()
        self.ylabel_edit = QLineEdit()
        self.width_spin = QDoubleSpinBox(); self.width_spin.setRange(2.0, 20.0); self.width_spin.setSingleStep(0.2); self.width_spin.setValue(7.2)
        self.height_spin = QDoubleSpinBox(); self.height_spin.setRange(2.0, 20.0); self.height_spin.setSingleStep(0.2); self.height_spin.setValue(4.8)
        self.dpi_spin = QSpinBox(); self.dpi_spin.setRange(72, 1200); self.dpi_spin.setValue(140)
        self.grid_check = QCheckBox("显示网格"); self.grid_check.setChecked(True)
        self.legend_check = QCheckBox("显示图例"); self.legend_check.setChecked(True)
        self.logx_check = QCheckBox("X 对数")
        self.logy_check = QCheckBox("Y 对数")
        self.sort_check = QCheckBox("按 X 排序")

        for label, widget in [
            ("图表类型", self.chart_type_box),
            ("主题", self.theme_box),
            ("图表语言", self.language_box),
            ("X / 标签", self.x_box),
            ("Y", self.y_box),
            ("Y2", self.y2_box),
            ("分组 Hue", self.hue_box),
            ("误差列", self.error_box),
            ("聚合", self.agg_box),
            ("标题", self.title_edit),
            ("X 标题", self.xlabel_edit),
            ("Y 标题", self.ylabel_edit),
            ("宽度", self.width_spin),
            ("高度", self.height_spin),
            ("DPI", self.dpi_spin),
        ]:
            form.addRow(label, widget)
        layout.addLayout(form)
        layout.addWidget(self.grid_check)
        layout.addWidget(self.legend_check)
        layout.addWidget(self.logx_check)
        layout.addWidget(self.logy_check)
        layout.addWidget(self.sort_check)

        manual_btn = QPushButton("🎨 按参数绘制")
        manual_btn.clicked.connect(self.run_manual_plot)
        export_btn = QPushButton("💾 导出 PNG/SVG/PDF/TIFF")
        export_btn.setObjectName("Secondary")
        export_btn.clicked.connect(self.export_figure)
        reset_btn = QPushButton("🧹 重置画布")
        reset_btn.setObjectName("Danger")
        reset_btn.clicked.connect(self.reset_canvas)
        layout.addWidget(manual_btn)
        layout.addWidget(export_btn)
        layout.addWidget(reset_btn)
        layout.addStretch(1)
        return panel

    def open_model_config(self) -> None:
        dialog = LLMConfigDialog(self.config, self)
        if dialog.exec_() == dialog.Accepted and dialog.saved_config is not None:
            self.config = load_config()
            self.assistant.update_config(self.config)
            self.model_label.setText(f"模型：{self.config.model if self.config.api_key else '本地规则模式'}")
            self._append_chat("系统", "大模型配置已保存并生效。")

    def open_manual_data(self) -> None:
        dialog = ManualDataDialog(self)
        if dialog.exec_() == dialog.Accepted and dialog.df is not None:
            try:
                df = self.project.load_dataframe(dialog.df, name="手动输入数据")
                self._on_data_loaded(df)
            except Exception as exc:
                self._show_error("手动数据导入失败", str(exc))

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
        self._append_chat("系统", f"已加载 {self.project.name}，共 {len(df)} 行、{len(df.columns)} 列。")
        spec = ChartEngine.smart_default_spec(df, language=self.language_box.currentText() if hasattr(self, "language_box") else "纯科研英语")
        self._sync_controls_from_spec(spec)
        self.run_manual_plot()

    def _refresh_profile(self) -> None:
        profile = self.project.profile()
        self.metric_rows.set_value(str(profile.rows))
        self.metric_cols.set_value(str(profile.columns))
        self.metric_missing.set_value(f"{profile.missing_ratio:.1%}")
        self.metric_dup.set_value(str(profile.duplicate_rows))
        self.profile_text.setMarkdown(profile.to_markdown())

    def _refresh_column_boxes(self) -> None:
        cols = [""] + (list(self.project.df.columns) if self.project.df is not None else [])
        for box in [self.x_box, self.y_box, self.y2_box, self.hue_box, self.error_box]:
            current = box.currentText()
            box.blockSignals(True)
            box.clear()
            box.addItems(cols)
            if current in cols:
                box.setCurrentText(current)
            box.blockSignals(False)

    def _spec_from_controls(self) -> ChartSpec:
        def val(box: QComboBox) -> str | None:
            text = box.currentText().strip()
            return text or None
        return ChartSpec(
            chart_type=self.chart_type_box.currentText(),
            x=val(self.x_box),
            y=val(self.y_box),
            y2=val(self.y2_box),
            hue=val(self.hue_box),
            title=self.title_edit.text().strip(),
            xlabel=self.xlabel_edit.text().strip(),
            ylabel=self.ylabel_edit.text().strip(),
            theme=self.theme_box.currentText(),
            language=self.language_box.currentText(),
            width=float(self.width_spin.value()),
            height=float(self.height_spin.value()),
            dpi=int(self.dpi_spin.value()),
            grid=self.grid_check.isChecked(),
            legend=self.legend_check.isChecked(),
            log_x=self.logx_check.isChecked(),
            log_y=self.logy_check.isChecked(),
            aggregate=self.agg_box.currentText(),
            sort_x=self.sort_check.isChecked(),
            error_col=val(self.error_box),
        )

    def _sync_controls_from_spec(self, spec: ChartSpec) -> None:
        def set_combo(box: QComboBox, value: str | None) -> None:
            if value is None:
                value = ""
            idx = box.findText(value)
            if idx >= 0:
                box.setCurrentIndex(idx)
        set_combo(self.chart_type_box, spec.chart_type)
        set_combo(self.theme_box, spec.theme)
        set_combo(self.language_box, spec.language)
        set_combo(self.x_box, spec.x)
        set_combo(self.y_box, spec.y)
        set_combo(self.y2_box, spec.y2)
        set_combo(self.hue_box, spec.hue)
        set_combo(self.error_box, spec.error_col)
        set_combo(self.agg_box, spec.aggregate)
        self.title_edit.setText(spec.title)
        self.xlabel_edit.setText(spec.xlabel)
        self.ylabel_edit.setText(spec.ylabel)
        self.width_spin.setValue(spec.width)
        self.height_spin.setValue(spec.height)
        self.dpi_spin.setValue(spec.dpi)
        self.grid_check.setChecked(spec.grid)
        self.legend_check.setChecked(spec.legend)
        self.logx_check.setChecked(spec.log_x)
        self.logy_check.setChecked(spec.log_y)
        self.sort_check.setChecked(spec.sort_x)

    def run_ai_plot(self) -> None:
        if not self._require_data():
            return
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            prompt = "请根据数据结构推荐最合适的科研图。"
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
        self._replace_figure(fig)
        self.current_spec = spec
        self._sync_controls_from_spec(spec)
        self._update_code()
        self.tabs.setCurrentIndex(0)
        source = "大模型" if result.used_llm else "本地规则"
        self._append_chat("生成器", f"{result.message}<br><b>方案来源：</b>{source}<br><b>图表：</b>{spec.chart_type}<br><b>语言：</b>{spec.language}")

    def _on_manual_plot_ready(self, fig: Figure, spec: ChartSpec) -> None:
        self._set_busy(False)
        self._replace_figure(fig)
        self.current_spec = spec
        self._update_code()
        self.tabs.setCurrentIndex(0)

    def _on_worker_failed(self, detail: str) -> None:
        self._set_busy(False)
        self._append_chat("错误", "绘图失败，已在弹窗中显示详细信息。")
        self._show_error("绘图失败", detail)

    def _replace_figure(self, fig: Figure) -> None:
        plt.close(self.figure)
        self.figure = fig
        old_canvas = self.canvas
        old_toolbar = self.toolbar
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        fig_page = self.tabs.widget(0)
        layout = fig_page.layout()
        layout.replaceWidget(old_toolbar, self.toolbar)
        layout.replaceWidget(old_canvas, self.canvas)
        old_toolbar.deleteLater()
        old_canvas.deleteLater()
        self.canvas.draw_idle()

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
        x_col = self.x_box.currentText().strip() or None
        try:
            for y_col in numeric_cols:
                if x_col == y_col:
                    continue
                spec = ChartSpec(chart_type="折线图" if x_col else "直方图", x=x_col or y_col, y=y_col if x_col else None, title=y_col, theme=self.theme_box.currentText())
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
