from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import matplotlib
try:
    matplotlib.use("Qt5Agg")
except Exception:
    matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure


CHART_TYPES = ["柱状图", "折线图", "散点图", "热力图", "饼图", "三维散点图", "曲面图"]
LANGUAGES = ["纯科研英语", "中文"]

PALETTE_NAMES = ["海洋蓝", "极光紫", "日落橙", "森林绿", "珊瑚红", "单色灰"]
LINE_STYLES = ["实线", "虚线", "点划线", "点线"]
MARKER_STYLES = ["圆点", "方块", "三角形", "菱形"]
BACKGROUND_STYLES = ["柔和浅色", "论文白", "薄荷绿", "深夜蓝"]
CORRELATION_METHODS = ["自动", "Spearman", "Pearson", "Kendall"]
NORMALIZATION_METHODS = ["无", "Min-Max", "Z-score"]
STYLEABLE_CHARTS = set(CHART_TYPES)

PALETTE_ALIASES = {"Ocean": "海洋蓝", "Aurora": "极光紫", "Sunset": "日落橙", "Forest": "森林绿", "Coral": "珊瑚红", "Mono": "单色灰"}
LINE_STYLE_ALIASES = {"solid": "实线", "dashed": "虚线", "dashdot": "点划线", "dotted": "点线"}
MARKER_STYLE_ALIASES = {"circle": "圆点", "square": "方块", "triangle": "三角形", "diamond": "菱形", "none": "圆点"}
BACKGROUND_ALIASES = {"soft": "柔和浅色", "paper": "论文白", "mint": "薄荷绿", "midnight": "深夜蓝"}

THEMES = {
    "Nature": {"style": "whitegrid", "context": "paper", "palette": "deep", "rc": {"axes.spines.top": False, "axes.spines.right": False}},
    "Science": {"style": "ticks", "context": "paper", "palette": "colorblind", "rc": {"axes.linewidth": 1.1, "font.family": "serif"}},
    "IEEE": {"style": "ticks", "context": "paper", "palette": "gray", "rc": {"axes.linewidth": 1.0, "font.family": "serif", "legend.frameon": False}},
    "Modern": {"style": "whitegrid", "context": "notebook", "palette": "muted", "rc": {"axes.spines.top": False, "axes.spines.right": False}},
    "Dark": {
        "style": "darkgrid",
        "context": "notebook",
        "palette": "bright",
        "rc": {
            "axes.facecolor": "#111827", "figure.facecolor": "#111827",
            "text.color": "#F9FAFB", "axes.labelcolor": "#F9FAFB",
            "xtick.color": "#F9FAFB", "ytick.color": "#F9FAFB",
        },
    },
    "Minimal": {"style": "white", "context": "paper", "palette": "deep", "rc": {"axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False}},
}

PALETTES = {
    "海洋蓝": ["#2563EB", "#06B6D4", "#14B8A6", "#38BDF8", "#0EA5E9", "#22C55E", "#F59E0B", "#F97316"],
    "极光紫": ["#7C3AED", "#A855F7", "#3B82F6", "#06B6D4", "#2DD4BF", "#F472B6", "#FB7185", "#F59E0B"],
    "日落橙": ["#F97316", "#FB7185", "#F43F5E", "#F59E0B", "#EAB308", "#FCA5A5", "#FDBA74", "#FECACA"],
    "森林绿": ["#166534", "#15803D", "#22C55E", "#65A30D", "#84CC16", "#0F766E", "#14B8A6", "#86EFAC"],
    "珊瑚红": ["#EF4444", "#FB7185", "#F97316", "#F59E0B", "#06B6D4", "#8B5CF6", "#14B8A6", "#F43F5E"],
    "单色灰": ["#0F172A", "#334155", "#475569", "#64748B", "#94A3B8", "#CBD5E1", "#E2E8F0", "#F8FAFC"],
}

BACKGROUND_PRESETS = {
    "柔和浅色": {"figure": "#F8FBFF", "axes": "#FFFFFF", "grid": "#D8E4F2", "spine": "#B8C7DA", "text": "#172033"},
    "论文白": {"figure": "#FFFFFF", "axes": "#FFFFFF", "grid": "#E5E7EB", "spine": "#CBD5E1", "text": "#0F172A"},
    "薄荷绿": {"figure": "#F1FBF8", "axes": "#FCFFFE", "grid": "#CDEEE4", "spine": "#9BCFC0", "text": "#134E4A"},
    "深夜蓝": {"figure": "#0F172A", "axes": "#111827", "grid": "#334155", "spine": "#475569", "text": "#E5F0FF"},
}


@dataclass
class ChartSpec:
    chart_type: str = "散点图"
    x: str | None = None
    y: str | None = None
    z: str | None = None
    y2: str | None = None
    hue: str | None = None
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    zlabel: str = ""
    theme: str = "Nature"
    language: str = "纯科研英语"
    width: float = 7.2
    height: float = 4.8
    dpi: int = 180
    grid: bool = True
    legend: bool = True
    log_x: bool = False
    log_y: bool = False
    aggregate: str = "mean"
    sort_x: bool = False
    error_col: str | None = None
    palette: str = "海洋蓝"
    line_style: str = "实线"
    marker_style: str = "圆点"
    background_style: str = "柔和浅色"
    show_value_labels: bool = True

    line_width: float = 2.4
    show_line_markers: bool = False
    point_size: int = 72
    bar_top_n: int = 20
    pie_top_n: int = 10
    donut: bool = True
    corr_method: str = "自动"
    heatmap_max_features: int = 18
    heatmap_annotate: bool = True
    heatmap_decimals: int = 4
    normalization: str = "无"
    surface_alpha: float = 0.92

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ChartEngine:
    def __init__(self) -> None:
        self.last_spec: ChartSpec | None = None
        self.last_figure: Figure | None = None

    @staticmethod
    def _title(cn: str, en: str, language: str) -> str:
        return cn if language == "中文" else en

    @staticmethod
    def _numeric_cols(df: pd.DataFrame) -> list[str]:
        return list(df.select_dtypes(include=np.number).columns)

    @staticmethod
    def _categorical_cols(df: pd.DataFrame, max_unique: int = 50) -> list[str]:
        cols: list[str] = []
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                unique = df[col].nunique(dropna=True)
                if 2 <= unique <= 12:
                    cols.append(col)
            elif not pd.api.types.is_datetime64_any_dtype(df[col]):
                unique = df[col].nunique(dropna=True)
                if 1 <= unique <= max_unique:
                    cols.append(col)
        return cols

    @staticmethod
    def _time_like_col(df: pd.DataFrame) -> str | None:
        for col in df.columns:
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                return col
        for col in df.columns:
            name = str(col).lower()
            if any(k in name for k in ["date", "time", "year", "month", "day", "step", "epoch", "iter", "日期", "时间", "年份", "月份", "轮次", "步"]):
                return col
        return None

    @staticmethod
    def _mentioned_columns(df: pd.DataFrame, request_l: str, cols: list[str]) -> list[str]:
        return [c for c in cols if str(c).lower() in request_l]

    @staticmethod
    def request_is_plot(request: str) -> bool:
        text = request.lower().strip()
        consult_words = ["适合", "建议", "能不能", "可以画什么", "该画什么", "怎么画", "解释", "分析一下", "总结", "概览", "有哪些", "多少", "字段", "缺失", "重复", "为什么", "recommend", "suggest", "what chart", "which chart", "explain", "summary", "overview"]
        explicit_chart_words = ["柱状图", "条形图", "折线图", "散点图", "热力图", "饼图", "三维", "3d", "曲面", "bar chart", "line chart", "scatter", "heatmap", "pie chart", "surface"]
        explicit_action_words = ["绘制", "生成图", "生成一张", "画图", "画一个", "画一张", "画出", "作图", "出图", "可视化", "plot", "draw", "visualize"]
        has_consult = any(w in text for w in consult_words)
        has_explicit = any(w in text for w in explicit_chart_words) or any(w in text for w in explicit_action_words)
        if ("适合画什么" in text or "可以画什么" in text or "该画什么" in text) and not any(w in text for w in ["绘制", "画出", "生成"]):
            return False
        return has_explicit and not (has_consult and not has_explicit)

    @staticmethod
    def smart_default_spec(df: pd.DataFrame, request: str = "", language: str = "纯科研英语") -> ChartSpec:
        request_l = request.lower()
        numeric = ChartEngine._numeric_cols(df)
        categorical = ChartEngine._categorical_cols(df)
        all_cols = list(df.columns)
        mentioned_numeric = ChartEngine._mentioned_columns(df, request_l, numeric)
        mentioned_categorical = ChartEngine._mentioned_columns(df, request_l, categorical)
        t = lambda cn, en: ChartEngine._title(cn, en, language)

        if any(k in request_l for k in ["曲面", "surface"]):
            x = mentioned_numeric[0] if len(mentioned_numeric) >= 1 else (numeric[0] if numeric else None)
            y = mentioned_numeric[1] if len(mentioned_numeric) >= 2 else (numeric[1] if len(numeric) > 1 else None)
            z = mentioned_numeric[2] if len(mentioned_numeric) >= 3 else (numeric[2] if len(numeric) > 2 else None)
            return ChartSpec(chart_type="曲面图", x=x, y=y, z=z, title=t("三维曲面", "3D surface"), language=language)
        if any(k in request_l for k in ["三维", "3d", "xyz", "三维散点"]):
            x = mentioned_numeric[0] if len(mentioned_numeric) >= 1 else (numeric[0] if numeric else None)
            y = mentioned_numeric[1] if len(mentioned_numeric) >= 2 else (numeric[1] if len(numeric) > 1 else None)
            z = mentioned_numeric[2] if len(mentioned_numeric) >= 3 else (numeric[2] if len(numeric) > 2 else None)
            return ChartSpec(chart_type="三维散点图", x=x, y=y, z=z, title=t("三维变量关系", "3D variable relationship"), language=language)
        if any(k in request_l for k in ["热力", "heatmap", "相关", "corr", "correlation", "spearman"]):
            return ChartSpec(chart_type="热力图", title=t("特征 Spearman 相关性热力图", "Feature Spearman correlation heatmap"), language=language, corr_method="Spearman")
        if any(k in request_l for k in ["饼", "pie", "占比", "比例", "composition"]):
            return ChartSpec(chart_type="饼图", x=(mentioned_categorical[0] if mentioned_categorical else (categorical[0] if categorical else (all_cols[0] if all_cols else None))), y=(mentioned_numeric[0] if mentioned_numeric else (numeric[0] if numeric else None)), title=t("组成比例", "Composition"), language=language)
        if any(k in request_l for k in ["柱", "bar", "条形", "对比", "compare"]):
            return ChartSpec(chart_type="柱状图", x=(mentioned_categorical[0] if mentioned_categorical else (categorical[0] if categorical else (all_cols[0] if all_cols else None))), y=(mentioned_numeric[0] if mentioned_numeric else (numeric[0] if numeric else None)), title=t("组间比较", "Group comparison"), language=language)
        if any(k in request_l for k in ["折线", "line", "趋势", "trend", "变化"]):
            x = ChartEngine._time_like_col(df) or (all_cols[0] if all_cols else None)
            y = (mentioned_numeric[0] if mentioned_numeric and mentioned_numeric[0] != x else next((c for c in numeric if c != x), (numeric[0] if numeric else None)))
            return ChartSpec(chart_type="折线图", x=x, y=y, title=t("趋势分析", "Trend analysis"), language=language, show_line_markers=False)
        if any(k in request_l for k in ["散点", "scatter", "关系", "relationship"]):
            x = mentioned_numeric[0] if len(mentioned_numeric) >= 1 else (numeric[0] if numeric else None)
            y = mentioned_numeric[1] if len(mentioned_numeric) >= 2 else (next((c for c in numeric if c != x), None))
            return ChartSpec(chart_type="散点图", x=x, y=y, title=t("变量关系", "Variable relationship"), language=language)
        if len(numeric) >= 3:
            return ChartSpec(chart_type="三维散点图", x=numeric[0], y=numeric[1], z=numeric[2], title=t("三维变量关系", "3D variable relationship"), language=language)
        if len(numeric) >= 2:
            return ChartSpec(chart_type="散点图", x=numeric[0], y=numeric[1], title=t("变量关系", "Variable relationship"), language=language)
        if numeric and categorical:
            return ChartSpec(chart_type="柱状图", x=categorical[0], y=numeric[0], title=t("组间比较", "Group comparison"), language=language)
        return ChartSpec(chart_type="柱状图", x=(all_cols[0] if all_cols else None), y=(numeric[0] if numeric else None), title=t("数据概览", "Data overview"), language=language)

    def render(self, df: pd.DataFrame, spec: ChartSpec) -> Figure:
        if df.empty:
            raise ValueError("数据为空，无法绘图。请先导入有效数据。")

        spec = self._repair_spec(df, spec)
        spec = self._validate_and_complete_spec(df, spec)
        plot_df = self._normalized_copy(df, spec)
        self._apply_theme(spec.theme)

        fig_width = spec.width
        fig_height = spec.height
        if spec.chart_type == "热力图":
            numeric_count = len(self._numeric_cols(plot_df))
            shown_count = min(numeric_count, max(2, spec.heatmap_max_features))
            fig_width = max(spec.width, min(24.0, 2.8 + shown_count * 0.72))
            fig_height = max(spec.height, min(22.0, 2.6 + shown_count * 0.62))

        is_3d = spec.chart_type in {"三维散点图", "曲面图"}
        fig = plt.figure(figsize=(fig_width, fig_height), dpi=spec.dpi, constrained_layout=True)
        ax = fig.add_subplot(111, projection="3d") if is_3d else fig.add_subplot(111)
        self._apply_background(fig, ax, spec)

        colors = self._palette_colors(spec.palette, 64)
        line_style = self._line_style(spec.line_style)
        marker = self._marker(spec.marker_style)
        text_color = self._background(spec.background_style)["text"]

        if spec.chart_type == "散点图":
            data = plot_df[[spec.x, spec.y]].dropna()
            if data.empty:
                raise ValueError("散点图在移除缺失值后没有可用数据。")
            ax.scatter(data[spec.x], data[spec.y], s=spec.point_size, c=colors[0], alpha=0.88, edgecolors="white", linewidths=0.8, marker=marker)
            if len(data) >= 3:
                x_num = pd.to_numeric(data[spec.x], errors="coerce")
                y_num = pd.to_numeric(data[spec.y], errors="coerce")
                mask = x_num.notna() & y_num.notna()
                if mask.sum() >= 3:
                    zfit = np.polyfit(x_num[mask], y_num[mask], 1)
                    xs = np.linspace(x_num[mask].min(), x_num[mask].max(), 100)
                    ax.plot(xs, np.poly1d(zfit)(xs), color=colors[2], linestyle="--", linewidth=1.8, alpha=0.72)

        elif spec.chart_type == "折线图":
            data = plot_df[[spec.x, spec.y]].dropna().copy()
            if data.empty:
                raise ValueError("折线图在移除缺失值后没有可用数据。")
            if pd.api.types.is_numeric_dtype(data[spec.x]) or pd.api.types.is_datetime64_any_dtype(data[spec.x]):
                data = data.sort_values(spec.x)
            ax.plot(data[spec.x], data[spec.y], color=colors[0], linewidth=spec.line_width, linestyle=line_style, marker=(marker if spec.show_line_markers else None), markersize=5.5, markerfacecolor=colors[1], markeredgecolor="white", markeredgewidth=0.8)
            try:
                y_num = pd.to_numeric(data[spec.y], errors="coerce")
                ax.fill_between(data[spec.x], y_num, alpha=0.11, color=colors[0])
            except Exception:
                pass
            self._annotate_line(ax, data, spec, text_color)

        elif spec.chart_type == "柱状图":
            data = self._prepare_bar_or_pie_data(plot_df, spec, max_categories=max(1, spec.bar_top_n))
            bars = ax.bar(data[spec.x].astype(str), data[spec.y], color=self._palette_colors(spec.palette, len(data)), edgecolor="white", linewidth=1.0)
            if spec.show_value_labels:
                ax.bar_label(bars, padding=3, fontsize=8)
            if len(data) >= 8:
                for label in ax.get_xticklabels():
                    label.set_rotation(35)
                    label.set_horizontalalignment("right")

        elif spec.chart_type == "饼图":
            data = self._prepare_bar_or_pie_data(plot_df, spec, max_categories=max(1, spec.pie_top_n))
            wedgeprops = {"edgecolor": "white", "linewidth": 1.5}
            if spec.donut:
                wedgeprops["width"] = 0.46
            wedges, texts, autotexts = ax.pie(data[spec.y], labels=data[spec.x].astype(str), autopct="%1.1f%%" if spec.show_value_labels else None, startangle=90, colors=self._palette_colors(spec.palette, len(data)), pctdistance=0.78, wedgeprops=wedgeprops)
            for txt in list(texts) + list(autotexts or []):
                txt.set_fontsize(9)
            ax.axis("equal")
            ax.set_xlabel("")
            ax.set_ylabel("")

        elif spec.chart_type == "热力图":
            numeric_df = plot_df[self._numeric_cols(plot_df)].dropna(axis=1, how="all")
            if numeric_df.shape[1] < 2:
                raise ValueError("热力图需要至少 2 个数值列，当前数据不适合绘制相关性热力图。")
            numeric_df = numeric_df.apply(pd.to_numeric, errors="coerce").dropna(axis=1, how="all")
            max_features = max(2, int(spec.heatmap_max_features))
            if numeric_df.shape[1] > max_features:
                variances = numeric_df.var(numeric_only=True).fillna(0).sort_values(ascending=False)
                numeric_df = numeric_df[list(variances.head(max_features).index)]
            method = self._corr_method(spec.corr_method, numeric_df)
            corr = numeric_df.corr(method=method)
            decimals = max(2, min(6, int(spec.heatmap_decimals)))
            show_values = bool(spec.heatmap_annotate and corr.shape[0] <= 22)
            label_font_size = 9 if corr.shape[0] <= 14 else 7
            annot_font_size = 8 if corr.shape[0] <= 12 else 6
            sns.heatmap(corr, annot=show_values, annot_kws={"size": annot_font_size}, fmt=f".{decimals}f", cmap="vlag", center=0, square=False, ax=ax, linewidths=0.6, linecolor="#FFFFFF", cbar_kws={"shrink": 0.84, "label": f"{method.capitalize()} correlation"}, xticklabels=True, yticklabels=True)
            ax.tick_params(axis="x", labelrotation=45, labelsize=label_font_size)
            ax.tick_params(axis="y", labelrotation=0, labelsize=label_font_size)
            for label in ax.get_xticklabels():
                label.set_horizontalalignment("right")
            if not spec.title:
                spec.title = self._title("特征相关性热力图", "Feature correlation heatmap", spec.language)

        elif spec.chart_type == "三维散点图":
            data = plot_df[[spec.x, spec.y, spec.z]].dropna()
            if data.empty:
                raise ValueError("三维散点图在移除缺失值后没有可用数据。")
            sc = ax.scatter(data[spec.x], data[spec.y], data[spec.z], c=data[spec.z], cmap="viridis", s=spec.point_size, alpha=0.86, edgecolors="white", linewidths=0.45, marker=marker)
            fig.colorbar(sc, ax=ax, shrink=0.72, pad=0.08, label=spec.z)

        elif spec.chart_type == "曲面图":
            data = plot_df[[spec.x, spec.y, spec.z]].dropna()
            if len(data) < 3:
                raise ValueError("曲面图至少需要 3 个有效样本点。")
            surf = ax.plot_trisurf(data[spec.x], data[spec.y], data[spec.z], cmap="viridis", linewidth=0.15, antialiased=True, alpha=spec.surface_alpha)
            ax.scatter(data[spec.x], data[spec.y], data[spec.z], color=colors[0], s=max(16, spec.point_size // 3), alpha=0.55)
            fig.colorbar(surf, ax=ax, shrink=0.72, pad=0.08, label=spec.z)

        else:
            raise ValueError(f"当前版本只支持：{', '.join(CHART_TYPES)}。")

        self._polish_axes(ax, spec)
        self.last_spec = spec
        self.last_figure = fig
        return fig

    def _normalized_copy(self, df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        if spec.normalization == "无":
            return df.copy()
        out = df.copy()
        numeric_cols = self._numeric_cols(out)
        for col in numeric_cols:
            values = pd.to_numeric(out[col], errors="coerce")
            if spec.normalization == "Min-Max":
                vmin, vmax = values.min(), values.max()
                out[col] = 0.0 if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin else (values - vmin) / (vmax - vmin)
            elif spec.normalization == "Z-score":
                mean, std = values.mean(), values.std(ddof=0)
                out[col] = 0.0 if pd.isna(std) or std == 0 else (values - mean) / std
        return out

    @staticmethod
    def _corr_method(method_name: str, numeric_df: pd.DataFrame) -> str:
        method = (method_name or "自动").lower()
        if "pearson" in method:
            return "pearson"
        if "kendall" in method:
            return "kendall"
        if "spearman" in method:
            return "spearman"
        return "spearman"

    def _validate_and_complete_spec(self, df: pd.DataFrame, spec: ChartSpec) -> ChartSpec:
        numeric = self._numeric_cols(df)
        categorical = self._categorical_cols(df)
        all_cols = list(df.columns)

        def valid(col: str | None) -> bool:
            return col in df.columns if col else False

        def choose_numeric(exclude: set[str] | None = None) -> str | None:
            exclude = exclude or set()
            return next((c for c in numeric if c not in exclude), None)

        if spec.chart_type not in CHART_TYPES:
            raise ValueError(f"当前版本只支持：{', '.join(CHART_TYPES)}。请换一种图表类型。")

        if spec.chart_type == "散点图":
            if len(numeric) < 2:
                raise ValueError("散点图需要至少 2 个数值列；当前数据数值列不足，不适合绘制散点图。")
            if not valid(spec.x) or not pd.api.types.is_numeric_dtype(df[spec.x]):
                spec.x = numeric[0]
            if not valid(spec.y) or not pd.api.types.is_numeric_dtype(df[spec.y]) or spec.y == spec.x:
                spec.y = choose_numeric({spec.x})
            if spec.y is None:
                raise ValueError("散点图需要两个不同的数值列。")

        elif spec.chart_type == "折线图":
            if not numeric:
                raise ValueError("折线图需要至少 1 个数值列作为 Y；当前数据不适合绘制折线图。")
            candidate_x = spec.x if valid(spec.x) else None
            if candidate_x is None:
                candidate_x = self._time_like_col(df) or (all_cols[0] if all_cols else None)
            if not valid(spec.y) or not pd.api.types.is_numeric_dtype(df[spec.y]) or spec.y == candidate_x:
                spec.y = next((c for c in numeric if c != candidate_x), numeric[0])
            if candidate_x == spec.y:
                candidate_x = next((c for c in all_cols if c != spec.y), None)
            spec.x = candidate_x
            if spec.x is None:
                raise ValueError("折线图需要 X 列和数值 Y 列。")

        elif spec.chart_type == "柱状图":
            if not numeric:
                raise ValueError("柱状图需要至少 1 个数值列作为 Y；当前数据不适合绘制柱状图。")
            if not categorical:
                raise ValueError("柱状图需要一个分类列或低基数分组列；当前数据没有合适的分类字段，直接绘制会非常混乱。")
            if not valid(spec.x) or spec.x not in categorical:
                spec.x = categorical[0]
            if not valid(spec.y) or not pd.api.types.is_numeric_dtype(df[spec.y]) or spec.y == spec.x:
                spec.y = next((c for c in numeric if c != spec.x), numeric[0])

        elif spec.chart_type == "饼图":
            if not numeric:
                raise ValueError("饼图需要 1 个数值列表示占比大小；当前数据不适合绘制饼图。")
            if not categorical:
                raise ValueError("饼图需要一个分类列；当前数据没有合适的分类字段。")
            if not valid(spec.x) or spec.x not in categorical:
                spec.x = categorical[0]
            if not valid(spec.y) or not pd.api.types.is_numeric_dtype(df[spec.y]) or spec.y == spec.x:
                spec.y = next((c for c in numeric if c != spec.x), numeric[0])
            values = pd.to_numeric(df[spec.y], errors="coerce").dropna()
            if values.empty or (values < 0).any():
                raise ValueError("饼图的数值列必须是非负数，并且不能全为空。")

        elif spec.chart_type == "热力图":
            if len(numeric) < 2:
                raise ValueError("热力图需要至少 2 个数值列；当前数据不适合绘制相关性热力图。")
            spec.x = None
            spec.y = None
            spec.z = None

        elif spec.chart_type in {"三维散点图", "曲面图"}:
            if len(numeric) < 3:
                raise ValueError(f"{spec.chart_type} 需要至少 3 个数值列作为 X、Y、Z。")
            if not valid(spec.x) or not pd.api.types.is_numeric_dtype(df[spec.x]):
                spec.x = numeric[0]
            if not valid(spec.y) or not pd.api.types.is_numeric_dtype(df[spec.y]) or spec.y == spec.x:
                spec.y = choose_numeric({spec.x})
            if not valid(spec.z) or not pd.api.types.is_numeric_dtype(df[spec.z]) or spec.z in {spec.x, spec.y}:
                spec.z = choose_numeric({spec.x, spec.y})
            if not spec.x or not spec.y or not spec.z:
                raise ValueError(f"{spec.chart_type} 需要 3 个不同的数值列。")

        if not spec.title:
            spec.title = self._default_title(spec)
        return spec

    @staticmethod
    def _default_title(spec: ChartSpec) -> str:
        if spec.language == "中文":
            return {"柱状图": "组间比较", "折线图": "趋势分析", "散点图": "变量关系", "热力图": "特征相关性热力图", "饼图": "组成比例", "三维散点图": "三维变量关系", "曲面图": "三维曲面"}.get(spec.chart_type, spec.chart_type)
        return {"柱状图": "Group comparison", "折线图": "Trend analysis", "散点图": "Variable relationship", "热力图": "Feature correlation heatmap", "饼图": "Composition", "三维散点图": "3D variable relationship", "曲面图": "3D surface"}.get(spec.chart_type, spec.chart_type)

    @staticmethod
    def _prepare_bar_or_pie_data(df: pd.DataFrame, spec: ChartSpec, max_categories: int) -> pd.DataFrame:
        if not spec.x or not spec.y:
            raise ValueError(f"{spec.chart_type} 需要分类列和数值列。")
        data = df[[spec.x, spec.y]].dropna().copy()
        if data.empty:
            raise ValueError(f"{spec.chart_type} 在移除缺失值后没有可用数据。")
        data[spec.y] = pd.to_numeric(data[spec.y], errors="coerce")
        data = data.dropna(subset=[spec.y])
        if data.empty:
            raise ValueError(f"{spec.chart_type} 的 Y 列不是有效数值。")
        grouped = data.groupby(spec.x, dropna=False, as_index=False)[spec.y].mean()
        grouped = grouped.sort_values(spec.y, ascending=False)
        if len(grouped) > max_categories:
            grouped = grouped.head(max_categories)
        if grouped.empty:
            raise ValueError(f"{spec.chart_type} 没有可绘制的聚合结果。")
        return grouped

    @staticmethod
    def _apply_theme(theme: str) -> None:
        cfg = THEMES.get(theme, THEMES["Nature"])
        sns.set_theme(style=cfg["style"], context=cfg["context"], palette=cfg["palette"], rc=cfg["rc"])
        plt.rcParams.update({
            "figure.dpi": 180, "savefig.dpi": 600,
            "axes.titleweight": "bold", "axes.titlesize": 13, "axes.labelsize": 11,
            "legend.fontsize": 9, "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
        })

    @staticmethod
    def _repair_spec(df: pd.DataFrame, spec: ChartSpec) -> ChartSpec:
        fixed = ChartSpec(**{**ChartSpec().to_dict(), **spec.to_dict()})
        fixed.palette = PALETTE_ALIASES.get(fixed.palette, fixed.palette)
        fixed.line_style = LINE_STYLE_ALIASES.get(fixed.line_style, fixed.line_style)
        fixed.marker_style = MARKER_STYLE_ALIASES.get(fixed.marker_style, fixed.marker_style)
        fixed.background_style = BACKGROUND_ALIASES.get(fixed.background_style, fixed.background_style)

        if fixed.palette not in PALETTE_NAMES:
            fixed.palette = "海洋蓝"
        if fixed.line_style not in LINE_STYLES:
            fixed.line_style = "实线"
        if fixed.marker_style not in MARKER_STYLES:
            fixed.marker_style = "圆点"
        if fixed.background_style not in BACKGROUND_STYLES:
            fixed.background_style = "柔和浅色"
        if fixed.language not in LANGUAGES:
            fixed.language = "纯科研英语"
        if fixed.theme not in THEMES:
            fixed.theme = "Nature"
        if fixed.corr_method not in CORRELATION_METHODS:
            fixed.corr_method = "自动"
        if fixed.normalization not in NORMALIZATION_METHODS:
            fixed.normalization = "无"

        fixed.heatmap_max_features = max(2, min(120, int(fixed.heatmap_max_features)))
        fixed.heatmap_decimals = max(2, min(6, int(fixed.heatmap_decimals)))
        fixed.dpi = max(120, min(1200, int(fixed.dpi)))
        fixed.point_size = max(8, min(500, int(fixed.point_size)))
        fixed.bar_top_n = max(3, min(80, int(fixed.bar_top_n)))
        fixed.pie_top_n = max(3, min(30, int(fixed.pie_top_n)))
        fixed.surface_alpha = max(0.1, min(1.0, float(fixed.surface_alpha)))

        def valid(col: str | None) -> str | None:
            return col if col in df.columns else None

        fixed.x = valid(fixed.x)
        fixed.y = valid(fixed.y)
        fixed.z = valid(fixed.z)
        fixed.y2 = None
        fixed.hue = None
        fixed.error_col = valid(fixed.error_col)
        return fixed

    @staticmethod
    def _palette_colors(name: str, n: int = 8) -> list[str]:
        name = PALETTE_ALIASES.get(name, name)
        colors = PALETTES.get(name, PALETTES["海洋蓝"])
        return [colors[i % len(colors)] for i in range(max(1, n))]

    @staticmethod
    def _marker(marker_style: str) -> str:
        marker_style = MARKER_STYLE_ALIASES.get(marker_style, marker_style)
        return {"圆点": "o", "方块": "s", "三角形": "^", "菱形": "D"}.get(marker_style, "o")

    @staticmethod
    def _line_style(style: str) -> str:
        style = LINE_STYLE_ALIASES.get(style, style)
        return {"实线": "-", "虚线": "--", "点划线": "-.", "点线": ":"}.get(style, "-")

    @staticmethod
    def _background(name: str) -> dict[str, str]:
        name = BACKGROUND_ALIASES.get(name, name)
        return BACKGROUND_PRESETS.get(name, BACKGROUND_PRESETS["柔和浅色"])

    def _apply_background(self, fig: Figure, ax, spec: ChartSpec) -> None:
        bg = self._background(spec.background_style)
        fig.patch.set_facecolor(bg["figure"])
        try:
            ax.set_facecolor(bg["axes"])
        except Exception:
            pass
        ax.tick_params(colors=bg["text"])
        ax.xaxis.label.set_color(bg["text"])
        ax.yaxis.label.set_color(bg["text"])
        ax.title.set_color(bg["text"])
        if hasattr(ax, "zaxis"):
            ax.zaxis.label.set_color(bg["text"])
        for spine in getattr(ax, "spines", {}).values():
            spine.set_color(bg["spine"])
        ax.grid(spec.grid, color=bg["grid"], alpha=0.65, linewidth=0.8)

    @staticmethod
    def _annotate_line(ax, plot_df: pd.DataFrame, spec: ChartSpec, text_color: str) -> None:
        if not spec.show_value_labels or not spec.x or not spec.y or len(plot_df) > 12:
            return
        for x, y in zip(plot_df[spec.x], plot_df[spec.y]):
            try:
                ax.annotate(f"{float(y):.2f}", (x, y), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=text_color)
            except Exception:
                continue

    @staticmethod
    def _polish_axes(ax, spec: ChartSpec) -> None:
        if spec.title:
            ax.set_title(spec.title, pad=14)
        if spec.chart_type != "饼图":
            ax.set_xlabel(spec.xlabel or (spec.x or ""))
            ax.set_ylabel(spec.ylabel or (spec.y or ""))
            if hasattr(ax, "set_zlabel"):
                ax.set_zlabel(spec.zlabel or (spec.z or ""))
        if spec.chart_type not in {"饼图", "热力图", "三维散点图", "曲面图"}:
            for label in ax.get_xticklabels():
                label.set_rotation(25)
                label.set_horizontalalignment("right")
        if not spec.legend:
            leg = ax.get_legend()
            if leg:
                leg.remove()
