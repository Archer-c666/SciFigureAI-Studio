from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import requests

from .charting import CHART_TYPES, LANGUAGES, THEMES, ChartEngine, ChartSpec
from .config import AppConfig


@dataclass
class AIResult:
    spec: ChartSpec | None
    message: str
    raw: str = ""
    used_llm: bool = False
    kind: str = "plot"  # plot / answer


class LLMChartAssistant:
    """Data assistant + safe plotting planner.

    It can answer data questions or return a safe ChartSpec JSON. The model never
    executes Python code; plotting is always handled by ChartEngine.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def update_config(self, config: AppConfig) -> None:
        self.config = config

    def handle_request(self, df: pd.DataFrame, request: str, language: str = "纯科研英语") -> AIResult:
        request = request.strip()
        if language not in LANGUAGES:
            language = "纯科研英语"

        if not request:
            spec = ChartEngine.smart_default_spec(df, language=language)
            return AIResult(spec=spec, message="已根据数据结构自动推荐图表。", kind="plot")

        local_wants_plot = ChartEngine.request_is_plot(request)

        if not self.config.api_key:
            if local_wants_plot:
                spec = ChartEngine.smart_default_spec(df, request, language=language)
                return AIResult(
                    spec=spec,
                    message="未配置 API Key，已使用本地规则生成图表。可点击“大模型配置”填写 API Key 后调用模型。",
                    used_llm=False,
                    kind="plot",
                )
            return AIResult(
                spec=None,
                message=self._local_answer(df, request, language),
                used_llm=False,
                kind="answer",
            )

        prompt = self._build_prompt(df, request, language)
        try:
            raw = self._chat(prompt)
            payload = self._extract_json(raw)
            result_type = str(payload.get("type", "plot")).lower().strip()
            if result_type == "answer":
                answer = str(payload.get("answer", "我已阅读当前数据，但没有生成图表。"))
                if not local_wants_plot:
                    return AIResult(
                        spec=None,
                        message=answer,
                        raw=raw,
                        used_llm=True,
                        kind="answer",
                    )
                spec = ChartEngine.smart_default_spec(df, request, language=language)
                return AIResult(
                    spec=spec,
                    message=f"模型给出了文字回答，已根据你的绘图需求自动选择图表。模型说明：{answer}",
                    raw=raw,
                    used_llm=True,
                    kind="plot",
                )
            spec = self._spec_from_payload(payload, df, language)
            message = str(payload.get("reason", "已由大模型生成绘图方案。"))
            return AIResult(spec=spec, message=message, raw=raw, used_llm=True, kind="plot")
        except Exception as exc:
            if local_wants_plot:
                spec = ChartEngine.smart_default_spec(df, request, language=language)
                return AIResult(
                    spec=spec,
                    message=f"大模型解析失败，已回退到本地推荐：{exc}",
                    raw="",
                    used_llm=False,
                    kind="plot",
                )
            return AIResult(
                spec=None,
                message=f"大模型解析失败，已回退到本地数据咨询：{self._local_answer(df, request, language)}",
                raw="",
                used_llm=False,
                kind="answer",
            )

    # Backward-compatible method name used by older workers.
    def create_spec(self, df: pd.DataFrame, request: str, language: str = "纯科研英语") -> AIResult:
        return self.handle_request(df, request, language)

    def _build_prompt(self, df: pd.DataFrame, request: str, language: str) -> str:
        sample = df.head(8).to_dict(orient="records")
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        numeric_cols = list(df.select_dtypes("number").columns)
        categorical_cols = []
        for col in df.columns:
            if col not in numeric_cols:
                categorical_cols.append(col)
            elif df[col].nunique(dropna=True) <= 12:
                categorical_cols.append(col)

        missing = {col: float(df[col].isna().mean()) for col in df.columns}
        nunique = {col: int(df[col].nunique(dropna=True)) for col in df.columns}
        target_language = "中文，标题、坐标轴、说明使用中文" if language == "中文" else "English only, concise scientific journal style"

        schema = {
            "columns": list(df.columns),
            "virtual_columns": ["样本序号", "样本数量", "SampleIndex"],
            "dtypes": dtypes,
            "rows": len(df),
            "numeric_columns": numeric_cols,
            "categorical_or_low_cardinality_columns": categorical_cols,
            "missing_ratio_by_column": missing,
            "nunique_by_column": nunique,
            "sample": sample,
            "available_chart_types": CHART_TYPES,
            "available_themes": list(THEMES.keys()),
            "target_language": target_language,
        }

        return f"""
你是一个科研绘图软件里的数据助手。你已经能看到用户导入的 Excel/CSV 数据结构、字段类型、缺失率和样例。
你需要判断用户是在“请求绘图”还是“咨询数据/咨询绘图建议”。

必须只返回严格 JSON，不要输出 Markdown。

如果用户是在咨询数据、字段、缺失值、适合画什么、如何解释等，但没有明确要求立即绘图：
{{
  "type": "answer",
  "answer": "基于当前数据的中文/英文回答"
}}

如果用户要求绘图：
{{
  "type": "plot",
  "chart_type": "柱状图/水平柱状图/折线图/散点图/箱线图/热力图/饼图/三维散点图/曲面图",
  "x": "列名或null",
  "y": "列名或null",
  "z": "列名或null，三维散点图和曲面图必须给出",
  "title": "图标题",
  "xlabel": "x轴标题",
  "ylabel": "y轴标题",
  "zlabel": "z轴标题，非三维图可为空",
  "theme": "Nature/Science/IEEE/Modern/Dark/Minimal",
  "corr_method": "自动/Spearman/Pearson/Kendall",
  "reason": "说明为什么这样选图和字段"
}}

绘图规则：
1. 只能选择五种图：柱状图、折线图、散点图、热力图、饼图。
2. “绘制特征之间的热力图/相关性热力图/变量关系热力图”应选择热力图，x/y 设为 null，corr_method 通常选 Spearman；软件会读取所有数值列并计算相关系数。
3. 散点图必须使用两个不同数值列。
4. 折线图 y 必须是数值列；x 优先用时间、序号、实验步数、epoch、iter 或第一列。折线图默认只画线，不画散点。
5. 柱状图 x 应为分类列或低基数分组列，y 为数值列；软件会自动聚合并限制类别数量避免混乱。
6. 饼图 x 应为分类列，y 为非负数值列；软件会自动聚合并限制类别数量。
7. 不要臆造列名，只能使用 columns 中真实存在的列名。
8. 如果用户请求的图不适合当前数据，优先选择更合理的五图之一；如果确实不适合，reason 中说明，软件本地校验还会弹窗。

语言要求：{target_language}
数据结构：{json.dumps(schema, ensure_ascii=False, default=str)}
用户输入：{request}
""".strip()

    def _chat(self, prompt: str) -> str:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": "You return only valid JSON for a scientific plotting/data assistant app."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.15,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=self.config.timeout)
        if not resp.ok:
            raise ValueError(f"HTTP {resp.status_code}: {resp.text[:1200]}")
        data = resp.json()
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _extract_json(text: str) -> dict[str, Any]:
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise ValueError("模型没有返回 JSON")
        return json.loads(match.group(0))

    @staticmethod
    def _spec_from_payload(payload: dict[str, Any], df: pd.DataFrame, language: str) -> ChartSpec:
        valid_cols = set(df.columns) | {"样本序号", "样本数量", "SampleIndex"}

        def col(value: Any) -> str | None:
            if value in {None, "", "null", "None"}:
                return None
            value = str(value)
            return value if value in valid_cols else None

        chart_type = str(payload.get("chart_type", "柱状图"))
        if chart_type not in CHART_TYPES:
            chart_type = ChartEngine.smart_default_spec(df, str(payload), language=language).chart_type

        theme = str(payload.get("theme", "Nature"))
        if theme not in THEMES:
            theme = "Nature"

        corr_method = str(payload.get("corr_method", "自动"))
        return ChartSpec(
            chart_type=chart_type,
            x=col(payload.get("x")),
            y=col(payload.get("y")),
            z=col(payload.get("z")),
            title=str(payload.get("title", "") or ""),
            xlabel=str(payload.get("xlabel", "") or ""),
            ylabel=str(payload.get("ylabel", "") or ""),
            zlabel=str(payload.get("zlabel", "") or ""),
            theme=theme,
            language=language,
            corr_method=corr_method,
            show_line_markers=False,
        )

    @staticmethod
    def _local_answer(df: pd.DataFrame, request: str, language: str) -> str:
        numeric_cols = list(df.select_dtypes("number").columns)
        cat_cols = list(df.select_dtypes(exclude="number").columns)
        missing = float(df.isna().mean().mean()) if len(df.columns) else 0.0
        duplicates = int(df.duplicated().sum())

        request_l = request.lower()
        if any(k in request_l for k in ["缺失", "missing", "空值", "nan"]):
            missing_by_col = df.isna().sum().sort_values(ascending=False)
            nonzero = missing_by_col[missing_by_col > 0]
            if language == "纯科研英语":
                if nonzero.empty:
                    return f"No missing values were found. The dataset has {len(df)} rows and {len(df.columns)} columns."
                detail = "; ".join(f"{col}: {int(val)}" for col, val in nonzero.items())
                return f"Missing values by column: {detail}."
            if nonzero.empty:
                return f"当前数据没有检测到缺失值。数据共有 {len(df)} 行、{len(df.columns)} 列。"
            detail = "；".join(f"{col}：{int(val)} 个" for col, val in nonzero.items())
            return f"检测到缺失值：{detail}。"

        chart_suggestions = []
        if len(numeric_cols) >= 3:
            chart_suggestions.append("三维散点图（指定 X/Y/Z 三个数值特征）")
            chart_suggestions.append("曲面图（适合连续采样或较密集的三维数据）")
        if len(numeric_cols) >= 2:
            chart_suggestions.append("热力图（数值特征之间的 Spearman 相关性）")
            chart_suggestions.append("散点图（两个数值特征之间的关系）")
            chart_suggestions.append("箱线图（多个数值特征分布对比）")
        if len(numeric_cols) >= 1:
            chart_suggestions.append("折线图/散点图（某个特征与样本数量或样本序号的关系）")
        if numeric_cols and cat_cols:
            chart_suggestions.append("柱状图或水平柱状图（分类字段与数值字段的均值比较）")
            chart_suggestions.append("饼图（分类字段与非负数值字段的组成比例）")
        if numeric_cols:
            chart_suggestions.append("折线图（如果存在时间、序号或实验步骤字段）")

        if language == "纯科研英语":
            return (
                f"Current dataset: {len(df)} rows and {len(df.columns)} columns. "
                f"Numeric columns: {', '.join(numeric_cols) or 'none'}. "
                f"Categorical/text columns: {', '.join(cat_cols) or 'none'}. "
                f"Overall missing ratio: {missing:.2%}; duplicated rows: {duplicates}. "
                f"Recommended charts: {'; '.join(chart_suggestions) if chart_suggestions else 'no suitable chart from the current five chart types'}."
            )

        return (
            f"当前数据共有 {len(df)} 行、{len(df.columns)} 列。"
            f"数值列：{', '.join(numeric_cols) or '无'}。"
            f"分类/文本列：{', '.join(cat_cols) or '无'}。"
            f"整体缺失率：{missing:.2%}；重复行：{duplicates}。"
            f"建议图表：{'；'.join(chart_suggestions) if chart_suggestions else '当前五种图表里暂时没有特别合适的类型'}。"
        )
