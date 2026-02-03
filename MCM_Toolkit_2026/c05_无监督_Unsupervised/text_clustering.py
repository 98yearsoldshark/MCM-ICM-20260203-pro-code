# -*- coding: utf-8 -*-
# 文本聚类：TF-IDF + KMeans（可选 jieba）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.optional_deps import is_installed, require_package  # noqa: E402


def _prepare_texts(texts: List[str], tokenization: str) -> Dict[str, Any]:
    tokenization = tokenization.lower()
    if tokenization == "auto":
        tokenization = "jieba" if is_installed("jieba") else "char"

    if tokenization == "jieba":
        jieba = require_package("jieba", pip_name="jieba")
        seg = [" ".join(jieba.lcut(t)) for t in texts]
        return {"texts": seg, "analyzer": "word", "token_pattern": r"(?u)\b\w+\b"}
    if tokenization == "char":
        return {"texts": texts, "analyzer": "char", "token_pattern": None}
    if tokenization == "whitespace":
        return {"texts": texts, "analyzer": "word", "token_pattern": r"(?u)\b\w+\b"}
    raise ValueError("tokenization 必须为 auto/jieba/char/whitespace 之一。")


def top_terms_per_cluster(model: KMeans, vectorizer: TfidfVectorizer, top_n: int = 10) -> List[List[str]]:
    """返回每个簇的 top terms（按中心权重排序）。"""
    terms = vectorizer.get_feature_names_out()
    centers = model.cluster_centers_
    out: List[List[str]] = []
    for i in range(centers.shape[0]):
        idx = np.argsort(centers[i])[::-1][: int(top_n)]
        out.append([str(terms[j]) for j in idx])
    return out


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：文本聚类（TF-IDF + KMeans）。

    Args:
        data: 支持：
            - list[str]
            - DataFrame（默认取 'text' 列；可用 params.text_col 指定）
            - dict {'texts': list[str]}
        params: 参数：
            - text_col: str（DataFrame 时默认 'text'）
            - tokenization: {"auto","jieba","char","whitespace"}（默认 auto）
            - n_clusters: int（默认 5）
            - random_state: int（默认 42）
            - max_features: int | None
            - ngram_range: tuple(int,int)（默认：char (2,4)，word (1,2)）
            - top_terms: int（默认 10）

    Returns:
        dict:
            - labels
            - model
            - vectorizer
            - top_terms_per_cluster
    """
    params = params or {}

    if isinstance(data, dict):
        texts = data.get("texts")
        if texts is None:
            raise ValueError("dict 输入需要包含 texts。")
        texts = [str(t) for t in texts]
    elif isinstance(data, pd.DataFrame):
        text_col = params.get("text_col", "text")
        if text_col not in data.columns:
            raise ValueError(f"DataFrame 缺少列：{text_col}")
        texts = data[text_col].astype(str).tolist()
    elif isinstance(data, list):
        texts = [str(t) for t in data]
    else:
        raise TypeError("data 必须为 list[str] / DataFrame / dict。")

    prepared = _prepare_texts(texts, str(params.get("tokenization", "auto")))
    analyzer = prepared["analyzer"]
    token_pattern = prepared["token_pattern"]

    if "ngram_range" in params and params["ngram_range"] is not None:
        ngram_range = tuple(params["ngram_range"])
    else:
        ngram_range = (2, 4) if analyzer == "char" else (1, 2)

    vectorizer = TfidfVectorizer(
        analyzer=analyzer,
        token_pattern=token_pattern,
        ngram_range=ngram_range,
        max_features=params.get("max_features"),
    )
    X = vectorizer.fit_transform(prepared["texts"])

    n_clusters = int(params.get("n_clusters", 5))
    random_state = int(params.get("random_state", 42))
    model = KMeans(n_clusters=n_clusters, random_state=random_state)
    labels = model.fit_predict(X)

    top_n = int(params.get("top_terms", 10))
    top = top_terms_per_cluster(model, vectorizer, top_n=top_n)

    return {"labels": labels, "model": model, "vectorizer": vectorizer, "top_terms_per_cluster": top}


if __name__ == "__main__":
    # Mock Data：两类文本
    texts = [
        "苹果手机 屏幕 清晰 拍照 好",
        "手机 外观 漂亮 性能 强",
        "股票 下跌 风险 增大",
        "市场 波动 回撤 风险 控制",
        "电影 推荐 剧情 感人",
        "观影 体验 很棒 推荐",
    ]
    out = solve(texts, params={"tokenization": "char", "n_clusters": 3, "top_terms": 8})
    print(out["top_terms_per_cluster"])

