from typing import Dict

import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from interfaces import ISemanticRouter
from models import RouteContext, RouteLabel, SemanticRouteResult


class EmbeddingSemanticRouter(ISemanticRouter):
    def __init__(self, embed_model_name: str, route_context: RouteContext):
        self._tokenizer = AutoTokenizer.from_pretrained(embed_model_name)
        self._model = AutoModel.from_pretrained(embed_model_name)
        self._route_context = route_context
        self._centroids = self._build_centroids()

    def _build_centroids(self) -> Dict[RouteLabel, np.ndarray]:
        centroids: Dict[RouteLabel, np.ndarray] = {}

        for label, phrases in self._route_context.prototypes.items():
            embeddings = self._encode_texts(phrases)
            centroid = np.mean(embeddings, axis=0)
            centroid = centroid / np.linalg.norm(centroid)
            centroids[label] = centroid

        return centroids

    def predict(self, query: str) -> SemanticRouteResult:
        query_embedding = self._encode_texts([query])[0]

        scored = []
        for label, centroid in self._centroids.items():
            score = self._cosine_similarity(query_embedding, centroid)
            scored.append((label, score))

        scored.sort(key=lambda item: item[1], reverse=True)

        top_label, top_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 0.0
        confidence = top_score - second_score

        all_scores = {label.value: round(score, 4) for label, score in scored}

        return SemanticRouteResult(
            predicted_label=top_label,
            confidence=round(confidence, 4),
            top_score=round(top_score, 4),
            second_score=round(second_score, 4),
            all_scores=all_scores,
        )

    def _encode_texts(self, texts: list[str]) -> np.ndarray:
        encoded_input = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            return_tensors="pt"
        )

        with torch.no_grad():
            model_output = self._model(**encoded_input)

        embeddings = self._mean_pooling(
            model_output.last_hidden_state,
            encoded_input["attention_mask"]
        )

        normalized_embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        return normalized_embeddings.cpu().numpy()

    @staticmethod
    def _mean_pooling(token_embeddings: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        summed = torch.sum(token_embeddings * input_mask_expanded, dim=1)
        counts = torch.clamp(input_mask_expanded.sum(dim=1), min=1e-9)
        return summed / counts

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)
