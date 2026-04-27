from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import pandas as pd
import requests

from .charting import CHART_TYPES, LANGUAGES, THEMES, ChartEngine, ChartSpec
from .config import AppConfig


@dataclass
class AIResult:
    spec: ChartSpec
    message: str
    raw: str = ""
    used_llm: bool = False


class LLMChartAssistant:
    """Convert natural-language plotting intent into a safe ChartSpec JSON.

    The model never executes Python code. It only returns a JSON spec that is
    validated and rendered by the trusted local ChartEngine.
    """

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def update_config(self, config: AppConfig) -> None:
        self.config = config

    def create_spec(self, df: pd.DataFrame, request: str, language: str = "纯科研英语") -> AIResult:
        if language not in LANGUAGES:
            language = "纯科研英语"
        if not request.strip():
            spec = ChartEngine.smart_default_spec(df, language=language)
            return AIResult(spec=spec, message="已根据数据结构自动推荐图表。")
        if not self.config.api_key:
            spec = ChartEngine.smart_default_spec(df, request, language=language)
            return AIResult(
                spec=spec,
                message="未配置 API Key，已使用本地规则生成图表。可点击“大模型配置”填写 API Key 后调用模型。",
                used_llm=False,
            )

        prompt = self._build_prompt(df, request, language)
        try:
            raw = self._chat(prompt)
            payload = self._extract_json(raw)
            spec = self._spec_from_payload(payload, df, language)
            message = str(payload.get("reason", "已由大模型生成绘图方案。"))
            return AIResult(spec=spec, message=message, raw=raw, used_llm=True)
        except Exception as exc:
            spec = ChartEngine.smart_default_spec(df, request, language=language)
            return AIResult(
                spec=spec,
                message=f"大模型解析失败，已回退到本地推荐：{exc}",
                raw="",
                used_llm=False,
            )

    def _build_prompt(self, df: pd.DataFrame, request: str, language: str) -> str:
        sample = df.head(8).to_dict(orient="records")
        dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}
        target_language = "中文，标题、坐标轴、图例说明尽量使用中文" if language == "中文" else "English only, concise scientific journal style; do not mix Chinese in title/xlabel/ylabel"
        schema = {
            "columns": list(df.columns),
            "dtypes": dtypes,
            "rows": len(df),
            "sample": sample,
            "available_chart_types": CHART_TYPES[1:],
            "available_themes": list(THEMES.keys()),
            "target_language": target_language,
        }
        return f"""
你是一个科研绘图软件的绘图规划器。请把用户需求转换成严格 JSON，不要输出 Markdown。
只能使用给定列名和给定图表类型。不要生成 Python 代码，不要臆造列名。
语言要求：{target_language}。

JSON 格式：
{{
  "chart_type": "散点图/折线图/柱状图/水平柱状图/直方图/箱线图/小提琴图/相关矩阵/热力图/回归图/误差棒/双Y轴/面积图/饼图/KDE 密度图",
  "x": "列名或null",
  "y": "列名或null",
  "y2": "列名或null",
  "hue": "列名或null",
  "title": "图标题，必须符合语言要求",
  "xlabel": "x轴标题，必须符合语言要求",
  "ylabel": "y轴标题，必须符合语言要求",
  "theme": "Nature/Science/IEEE/Modern/Dark/Minimal",
  "aggregate": "none/mean/median/sum/count",
  "reason": "一句话说明为什么这样画"
}}

数据结构：{json.dumps(schema, ensure_ascii=False, default=str)}
用户需求：{request}
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
                {"role": "system", "content": "You return only valid JSON for a scientific plotting app."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        resp = requests.post(url, headers=headers, json=body, timeout=self.config.timeout)
        if not resp.ok:
            # Show the provider's actual error instead of a generic 400/401 message.
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
        valid_cols = set(df.columns)

        def col(value: Any) -> str | None:
            if value in {None, "", "null", "None"}:
                return None
            value = str(value)
            return value if value in valid_cols else None

        chart_type = str(payload.get("chart_type") or "散点图")
        if chart_type == "AI 智能识别":
            chart_type = "智能识别"
        if chart_type not in CHART_TYPES:
            chart_type = "散点图"
        theme = str(payload.get("theme") or "Nature")
        if theme not in THEMES:
            theme = "Nature"
        aggregate = str(payload.get("aggregate") or "none")
        if aggregate not in {"none", "mean", "median", "sum", "count"}:
            aggregate = "none"
        return ChartSpec(
            chart_type=chart_type,
            x=col(payload.get("x")),
            y=col(payload.get("y")),
            y2=col(payload.get("y2")),
            hue=col(payload.get("hue")),
            title=str(payload.get("title") or ""),
            xlabel=str(payload.get("xlabel") or ""),
            ylabel=str(payload.get("ylabel") or ""),
            theme=theme,
            language=language,
            aggregate=aggregate,
        )
