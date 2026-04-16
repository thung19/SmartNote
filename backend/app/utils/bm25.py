"""
Lightweight BM25 index for keyword-based retrieval.

Used alongside dense vector search for hybrid retrieval —
vectors catch semantic/paraphrase matches while BM25 catches
exact terms, acronyms, error codes, API names, and rare tokens.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Tuple

_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


class BM25Index:
    def __init__(self, k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self._docs: List[List[str]] = []
        self._doc_lens: List[int] = []
        self._avgdl: float = 0.0
        self._df: Counter = Counter()
        self._n: int = 0

    def clear(self) -> None:
        self._docs = []
        self._doc_lens = []
        self._avgdl = 0.0
        self._df = Counter()
        self._n = 0

    def index(self, texts: List[str]) -> None:
        self.clear()
        self._n = len(texts)

        for text in texts:
            tokens = tokenize(text)
            self._docs.append(tokens)
            self._doc_lens.append(len(tokens))
            for t in set(tokens):
                self._df[t] += 1

        self._avgdl = sum(self._doc_lens) / max(self._n, 1)

    def search(self, query: str, top_k: int = 0) -> List[Tuple[int, float]]:
        q_tokens = tokenize(query)
        if not q_tokens or not self._docs:
            return []

        scores: List[Tuple[int, float]] = []
        for idx in range(self._n):
            s = self._score_doc(q_tokens, self._docs[idx], self._doc_lens[idx])
            if s > 0:
                scores.append((idx, s))

        scores.sort(key=lambda x: x[1], reverse=True)
        if top_k > 0:
            scores = scores[:top_k]
        return scores

    def _score_doc(
        self, q_tokens: List[str], doc_tokens: List[str], doc_len: int
    ) -> float:
        tf = Counter(doc_tokens)
        score = 0.0
        for qt in q_tokens:
            f = tf.get(qt, 0)
            if f == 0:
                continue
            df = self._df.get(qt, 0)
            idf = math.log((self._n - df + 0.5) / (df + 0.5) + 1.0)
            numerator = f * (self.k1 + 1)
            denominator = f + self.k1 * (
                1 - self.b + self.b * doc_len / max(self._avgdl, 1)
            )
            score += idf * numerator / denominator
        return score
