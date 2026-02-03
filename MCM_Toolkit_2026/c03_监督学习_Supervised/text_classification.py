# -*- coding: utf-8 -*-
# 文本分类（NLP）：中文分词（可选 jieba）+ 向量化（Count/Tf-idf）+ 分类器（LR/NB 等）

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB

# 允许直接运行本文件：把项目根目录加入 sys.path，避免导入失败
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from MCM_Toolkit_2026.utils.optional_deps import is_installed, require_package  # noqa: E402


def _prepare_texts(texts: List[str], tokenization: str) -> Dict[str, Any]:
    """
    将原始文本转换为可供 sklearn 向量化使用的形式。

    Args:
        texts: 文本列表。
        tokenization: {"auto","jieba","char","whitespace"}。

    Returns:
        dict:
            - texts: 处理后的文本列表（当 analyzer != 'char' 时使用）
            - analyzer: 'word' 或 'char'
            - token_pattern: regex（仅 word analyzer 有意义）
    """
    tokenization = tokenization.lower()
    if tokenization == "auto":
        tokenization = "jieba" if is_installed("jieba") else "char"

    if tokenization == "jieba":
        jieba = require_package("jieba", pip_name="jieba", extra_hint="中文分词可改用 tokenization='char' 跳过分词。")
        seg = [" ".join(jieba.lcut(t)) for t in texts]
        return {"texts": seg, "analyzer": "word", "token_pattern": r"(?u)\b\w+\b"}

    if tokenization == "whitespace":
        # 假定已用空格分好词
        return {"texts": texts, "analyzer": "word", "token_pattern": r"(?u)\b\w+\b"}

    if tokenization == "char":
        # 交给 vectorizer 的 analyzer='char'，不需要预处理
        return {"texts": texts, "analyzer": "char", "token_pattern": None}

    raise ValueError("tokenization 必须为 auto/jieba/char/whitespace 之一。")


def solve(data: Any, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    统一接口：文本分类训练与评估。

    Args:
        data: 支持：
            - DataFrame（包含文本列与标签列）
            - dict {'texts': list[str], 'labels': list/int/ndarray}
        params: 参数：
            - text_col: str（DataFrame 时默认 'text'）
            - target_col: str（DataFrame 时默认 'label'）
            - tokenization: {"auto","jieba","char","whitespace"}（默认 auto）
            - vectorizer: {"count","tfidf"}（默认 tfidf）
            - ngram_range: tuple(int,int)（默认：word 模式 (1,2)，char 模式 (2,4)）
            - max_features: int | None（默认 None）
            - model: {"logreg","nb"}（默认 logreg）
            - model_params: dict（传给具体模型）
            - test_size: float（默认 0.2）
            - random_state: int（默认 42）

    Returns:
        dict:
            - vectorizer
            - model
            - metrics: dict
            - y_pred
    """
    params = params or {}

    if isinstance(data, pd.DataFrame):
        text_col = params.get("text_col", "text")
        target_col = params.get("target_col", "label")
        if text_col not in data.columns or target_col not in data.columns:
            raise ValueError(f"DataFrame 需要包含列：{text_col}, {target_col}")
        texts = data[text_col].astype(str).tolist()
        labels = data[target_col].to_numpy()
    elif isinstance(data, dict):
        texts = data.get("texts")
        labels = data.get("labels")
        if texts is None or labels is None:
            raise ValueError("dict 输入需要包含 keys: texts, labels")
        texts = [str(t) for t in texts]
        labels = np.asarray(labels)
    else:
        raise TypeError("data 必须为 DataFrame 或 dict。")

    tokenization = str(params.get("tokenization", "auto"))
    prepared = _prepare_texts(texts, tokenization)

    analyzer = prepared["analyzer"]
    token_pattern = prepared["token_pattern"]

    max_features = params.get("max_features")

    # ngram 默认值：char 模式一般用 2~4，word 模式一般用 1~2
    if "ngram_range" in params and params["ngram_range"] is not None:
        ngram_range = tuple(params["ngram_range"])
    else:
        ngram_range = (2, 4) if analyzer == "char" else (1, 2)

    vectorizer_kind = str(params.get("vectorizer", "tfidf")).lower()
    vec_cls = TfidfVectorizer if vectorizer_kind == "tfidf" else CountVectorizer
    if vectorizer_kind not in {"tfidf", "count"}:
        raise ValueError("vectorizer 必须为 tfidf 或 count。")

    if analyzer == "char":
        vectorizer = vec_cls(analyzer="char", ngram_range=ngram_range, max_features=max_features)
        X = vectorizer.fit_transform(prepared["texts"])
    else:
        vectorizer = vec_cls(
            analyzer="word",
            token_pattern=token_pattern or r"(?u)\b\w+\b",
            ngram_range=ngram_range,
            max_features=max_features,
        )
        X = vectorizer.fit_transform(prepared["texts"])

    test_size = float(params.get("test_size", 0.2))
    random_state = int(params.get("random_state", 42))

    X_train, X_test, y_train, y_test = train_test_split(
        X, labels, test_size=test_size, random_state=random_state, stratify=labels if len(np.unique(labels)) > 1 else None
    )

    model_kind = str(params.get("model", "logreg")).lower()
    model_params = dict(params.get("model_params", {}) or {})
    if model_kind == "logreg":
        model = LogisticRegression(max_iter=1000, **model_params)
    elif model_kind == "nb":
        model = MultinomialNB(**model_params)
    else:
        raise ValueError("model 必须为 logreg 或 nb。")

    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, zero_division=0),
    }
    return {"vectorizer": vectorizer, "model": model, "metrics": metrics, "y_pred": y_pred}


if __name__ == "__main__":
    # Mock Data：简易情感分类（中文）
    df_demo = pd.DataFrame(
        {
            "text": [
                "手机 外观 漂亮",
                "屏幕 很 清晰",
                "物流 太 慢 了",
                "质量 很 差 不 推荐",
                "价格 合理 值得 购买",
                "体验 一般般",
            ],
            "label": [1, 1, 0, 0, 1, 0],
        }
    )
    out = solve(df_demo, params={"tokenization": "char", "vectorizer": "tfidf", "model": "logreg"})
    print(out["metrics"])

