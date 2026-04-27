from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import matplotlib
try:
    matplotlib.use("Qt5Agg")
except Exception:  # Allows headless code-generation tests without Qt installed.
    matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure


CHART_TYPES = [
    "智能识别",
    "散点图",
    "折线图",
    "柱状图",
    "水平柱状图",
    "直方图",
    "箱线图",
    "小提琴图",
    "相关矩阵",
    "热力图",
    "回归图",
    "误差棒",
    "双Y轴",
    "面积图",
    "饼图",
    "KDE 密度图",
]

LANGUAGES = ["纯科研英语", "中文"]

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
            "axes.facecolor": "#111827",
            "figure.facecolor": "#111827",
            "text.color": "#F9FAFB",
            "axes.labelcolor": "#F9FAFB",
            "xtick.color": "#F9FAFB",
            "ytick.color": "#F9FAFB",
        },
    },
    "Minimal": {"style": "white", "context": "paper", "palette": "deep", "rc": {"axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False}},
}


@dataclass
class ChartSpec:
    chart_type: str = "散点图"
    x: str | None = None
    y: str | None = None
    y2: str | None = None
    hue: str | None = None
    title: str = ""
    xlabel: str = ""
    ylabel: str = ""
    theme: str = "Nature"
    language: str = "纯科研英语"
    width: float = 7.2
    height: float = 4.8
    dpi: int = 140
    grid: bool = True
    legend: bool = True
    log_x: bool = False
    log_y: bool = False
    aggregate: str = "none"  # none, mean, median, sum, count
    sort_x: bool = False
    error_col: str | None = None

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
    def smart_default_spec(df: pd.DataFrame, request: str = "", language: str = "纯科研英语") -> ChartSpec:
        request_l = request.lower()
        num_cols = list(df.select_dtypes(include=np.number).columns)
        cat_cols = list(df.select_dtypes(include=["object", "category", "bool"]).columns)
        date_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
        all_cols = list(df.columns)
        t = lambda cn, en: ChartEngine._title(cn, en, language)

        def first(seq: list[str], default: str | None = None) -> str | None:
            return seq[0] if seq else default

        if any(k in request_l for k in ["相关", "corr", "correlation", "热力", "heatmap"]):
            return ChartSpec(chart_type="相关矩阵", title=t("相关性矩阵", "Correlation matrix"), language=language)
        if any(k in request_l for k in ["回归", "regression", "拟合", "fit"]):
            return ChartSpec(chart_type="回归图", x=first(num_cols), y=num_cols[1] if len(num_cols) > 1 else first(num_cols), title=t("回归拟合", "Regression fit"), language=language)
        if any(k in request_l for k in ["箱", "box"]):
            return ChartSpec(chart_type="箱线图", x=first(cat_cols), y=first(num_cols), title=t("箱线图", "Box plot"), language=language)
        if any(k in request_l for k in ["小提琴", "violin"]):
            return ChartSpec(chart_type="小提琴图", x=first(cat_cols), y=first(num_cols), title=t("小提琴图", "Violin plot"), language=language)
        if any(k in request_l for k in ["直方", "hist", "分布", "distribution"]):
            return ChartSpec(chart_type="直方图", x=first(num_cols), title=t("分布", "Distribution"), language=language)
        if any(k in request_l for k in ["折线", "line", "趋势", "trend"]):
            return ChartSpec(chart_type="折线图", x=first(date_cols, first(all_cols)), y=first(num_cols), title=t("趋势", "Trend"), language=language)
        if any(k in request_l for k in ["柱状", "bar", "对比", "compare"]):
            return ChartSpec(chart_type="柱状图", x=first(cat_cols, first(all_cols)), y=first(num_cols), aggregate="mean", title=t("组间比较", "Group comparison"), language=language)
        if any(k in request_l for k in ["饼", "pie", "占比", "比例"]):
            return ChartSpec(chart_type="饼图", x=first(cat_cols, first(all_cols)), y=first(num_cols), aggregate="sum", title=t("组成比例", "Composition"), language=language)
        if len(num_cols) >= 2:
            return ChartSpec(chart_type="散点图", x=num_cols[0], y=num_cols[1], title=t("散点图", "Scatter plot"), language=language)
        if len(num_cols) == 1 and cat_cols:
            return ChartSpec(chart_type="柱状图", x=cat_cols[0], y=num_cols[0], aggregate="mean", title=t("组间比较", "Group comparison"), language=language)
        if num_cols:
            return ChartSpec(chart_type="直方图", x=num_cols[0], title=t("分布", "Distribution"), language=language)
        return ChartSpec(chart_type="热力图", x=first(all_cols), title=t("数据概览", "Data overview"), language=language)

    def render(self, df: pd.DataFrame, spec: ChartSpec) -> Figure:
        if df.empty:
            raise ValueError("数据为空，无法绘图")

        spec = self._repair_spec(df, spec)
        self._apply_theme(spec.theme)
        fig, ax = plt.subplots(figsize=(spec.width, spec.height), dpi=spec.dpi, constrained_layout=True)
        plot_df = self._prepare_data(df, spec)
        chart_type = spec.chart_type

        if chart_type in {"智能识别", "AI 智能识别"}:
            default_spec = self.smart_default_spec(df, language=spec.language)
            chart_type = default_spec.chart_type
            spec.x = spec.x or default_spec.x
            spec.y = spec.y or default_spec.y
            spec.y2 = spec.y2 or default_spec.y2
            spec.hue = spec.hue or default_spec.hue
            spec.title = spec.title or default_spec.title
            spec.aggregate = spec.aggregate if spec.aggregate != "none" else default_spec.aggregate

        if chart_type == "散点图":
            sns.scatterplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, ax=ax, s=56, edgecolor="white", linewidth=0.4)
        elif chart_type == "折线图":
            sns.lineplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, marker="o", ax=ax)
        elif chart_type == "柱状图":
            sns.barplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, ax=ax, errorbar="sd")
        elif chart_type == "水平柱状图":
            sns.barplot(data=plot_df, y=spec.x, x=spec.y, hue=spec.hue, ax=ax, errorbar="sd")
        elif chart_type == "直方图":
            sns.histplot(data=plot_df, x=spec.x, hue=spec.hue, kde=True, ax=ax)
        elif chart_type == "箱线图":
            sns.boxplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, ax=ax)
        elif chart_type == "小提琴图":
            sns.violinplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, ax=ax, inner="quartile")
        elif chart_type == "相关矩阵":
            numeric = plot_df.select_dtypes(include=np.number)
            if numeric.shape[1] < 2:
                raise ValueError("相关矩阵至少需要 2 个数值列")
            corr = numeric.corr()
            sns.heatmap(corr, annot=True, fmt=".2f", cmap="vlag", center=0, square=True, ax=ax, cbar_kws={"shrink": 0.8})
        elif chart_type == "热力图":
            numeric = plot_df.select_dtypes(include=np.number)
            if numeric.empty:
                raise ValueError("热力图需要数值列")
            sns.heatmap(numeric, cmap="viridis", ax=ax, cbar_kws={"shrink": 0.8})
        elif chart_type == "回归图":
            sns.regplot(data=plot_df, x=spec.x, y=spec.y, ax=ax, scatter_kws={"s": 46, "alpha": 0.85}, line_kws={"linewidth": 2.2})
            if spec.hue:
                sns.scatterplot(data=plot_df, x=spec.x, y=spec.y, hue=spec.hue, ax=ax, s=42)
        elif chart_type == "误差棒":
            if not spec.x or not spec.y:
                raise ValueError("误差棒需要 X 和 Y 列")
            yerr = plot_df[spec.error_col].to_numpy() if spec.error_col else None
            ax.errorbar(plot_df[spec.x], plot_df[spec.y], yerr=yerr, fmt="o-", capsize=4, linewidth=1.8)
        elif chart_type == "双Y轴":
            if not spec.x or not spec.y or not spec.y2:
                raise ValueError("双Y轴需要 X、Y1、Y2 三列")
            ax.plot(plot_df[spec.x], plot_df[spec.y], marker="o", label=spec.y)
            ax2 = ax.twinx()
            ax2.plot(plot_df[spec.x], plot_df[spec.y2], marker="s", linestyle="--", label=spec.y2)
            ax2.set_ylabel(spec.y2)
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            if spec.legend:
                ax.legend(lines + lines2, labels + labels2, loc="best")
        elif chart_type == "面积图":
            if not spec.x or not spec.y:
                raise ValueError("面积图需要 X 和 Y 列")
            ax.fill_between(plot_df[spec.x], plot_df[spec.y], alpha=0.35)
            ax.plot(plot_df[spec.x], plot_df[spec.y], linewidth=2)
        elif chart_type == "饼图":
            if not spec.x or not spec.y:
                raise ValueError("饼图需要标签列和数值列")
            pie_df = plot_df[[spec.x, spec.y]].dropna().copy()
            if len(pie_df) > 12:
                pie_df = pie_df.sort_values(spec.y, ascending=False).head(12)
            ax.pie(pie_df[spec.y], labels=pie_df[spec.x].astype(str), autopct="%1.1f%%", startangle=90)
            ax.axis("equal")
        elif chart_type == "KDE 密度图":
            sns.kdeplot(data=plot_df, x=spec.x, hue=spec.hue, fill=True, ax=ax)
        else:
            raise ValueError(f"未知图表类型：{chart_type}")

        self._polish_axes(ax, spec)
        self.last_spec = spec
        self.last_figure = fig
        return fig

    @staticmethod
    def _apply_theme(theme: str) -> None:
        cfg = THEMES.get(theme, THEMES["Nature"])
        sns.set_theme(style=cfg["style"], context=cfg["context"], palette=cfg["palette"], rc=cfg["rc"])
        plt.rcParams.update({
            "figure.dpi": 140,
            "savefig.dpi": 600,
            "axes.titleweight": "bold",
            "axes.titlesize": 13,
            "axes.labelsize": 11,
            "legend.fontsize": 9,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
            "axes.unicode_minus": False,
            "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
        })

    @staticmethod
    def _repair_spec(df: pd.DataFrame, spec: ChartSpec) -> ChartSpec:
        spec = ChartSpec(**{**ChartSpec().to_dict(), **spec.to_dict()})
        if spec.chart_type == "AI 智能识别":
            spec.chart_type = "智能识别"
        numeric = list(df.select_dtypes(include=np.number).columns)
        non_numeric = list(df.select_dtypes(exclude=np.number).columns)
        all_cols = list(df.columns)

        def valid(col: str | None) -> str | None:
            return col if col in df.columns else None

        spec.x = valid(spec.x)
        spec.y = valid(spec.y)
        spec.y2 = valid(spec.y2)
        spec.hue = valid(spec.hue)
        spec.error_col = valid(spec.error_col)

        if spec.chart_type in {"智能识别", "散点图", "回归图", "双Y轴"}:
            if not spec.x:
                spec.x = numeric[0] if numeric else (all_cols[0] if all_cols else None)
            if not spec.y and spec.chart_type != "智能识别":
                spec.y = numeric[1] if len(numeric) > 1 else (numeric[0] if numeric else None)
        elif spec.chart_type in {"柱状图", "水平柱状图", "箱线图", "小提琴图", "饼图"}:
            if not spec.x:
                spec.x = non_numeric[0] if non_numeric else (all_cols[0] if all_cols else None)
            if not spec.y:
                spec.y = numeric[0] if numeric else None
        elif spec.chart_type in {"折线图", "面积图", "误差棒"}:
            if not spec.x:
                spec.x = all_cols[0] if all_cols else None
            if not spec.y:
                spec.y = numeric[0] if numeric else None
        elif spec.chart_type in {"直方图", "KDE 密度图"}:
            if not spec.x:
                spec.x = numeric[0] if numeric else None
        if spec.chart_type == "双Y轴" and not spec.y2:
            spec.y2 = numeric[2] if len(numeric) > 2 else (numeric[1] if len(numeric) > 1 else None)
        if spec.language not in LANGUAGES:
            spec.language = "纯科研英语"
        return spec

    @staticmethod
    def _prepare_data(df: pd.DataFrame, spec: ChartSpec) -> pd.DataFrame:
        plot_df = df.copy()
        if spec.aggregate != "none" and spec.x and spec.y and spec.x in plot_df.columns and spec.y in plot_df.columns:
            if spec.aggregate == "count":
                plot_df = plot_df.groupby(spec.x, dropna=False).size().reset_index(name=spec.y)
            else:
                agg = {"mean": "mean", "median": "median", "sum": "sum"}.get(spec.aggregate, "mean")
                plot_df = plot_df.groupby(spec.x, dropna=False, as_index=False)[spec.y].agg(agg)
        if spec.sort_x and spec.x and spec.x in plot_df.columns:
            plot_df = plot_df.sort_values(spec.x)
        return plot_df

    @staticmethod
    def _polish_axes(ax, spec: ChartSpec) -> None:
        if spec.title:
            ax.set_title(spec.title, pad=12)
        if spec.xlabel:
            ax.set_xlabel(spec.xlabel)
        elif spec.x:
            ax.set_xlabel(spec.x)
        if spec.ylabel:
            ax.set_ylabel(spec.ylabel)
        elif spec.y:
            ax.set_ylabel(spec.y)
        if spec.log_x:
            ax.set_xscale("log")
        if spec.log_y:
            ax.set_yscale("log")
        ax.grid(spec.grid, alpha=0.25)
        if not spec.legend:
            leg = ax.get_legend()
            if leg:
                leg.remove()
        for label in ax.get_xticklabels():
            label.set_rotation(25)
            label.set_horizontalalignment("right")
