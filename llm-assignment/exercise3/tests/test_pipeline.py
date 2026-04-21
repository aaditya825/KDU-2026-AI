from __future__ import annotations

import unittest

from tri_model_assistant.core.config import AppConfig, SummaryLength
from tri_model_assistant.models.pipeline import TriModelModelGateway
from tri_model_assistant.processing.text_processing import refinement_word_bounds, word_count


class _FakeTokenizer:
    def __init__(self, responses: dict[int, str]) -> None:
        self._responses = responses

    def __call__(self, _prompt: str, return_tensors: str, max_length: int, truncation: bool):
        return {"input_ids": [[1, 2, 3]], "attention_mask": [[1, 1, 1]]}

    def decode(self, _ids, skip_special_tokens: bool) -> str:
        return self._responses[_ids[0]]


class _FakeModel:
    def __init__(self) -> None:
        self.calls: list[dict[str, int | bool]] = []

    def generate(self, input_ids, attention_mask, max_new_tokens, min_new_tokens, do_sample, num_beams):
        self.calls.append(
            {
                "max_new_tokens": max_new_tokens,
                "min_new_tokens": min_new_tokens,
                "do_sample": do_sample,
                "num_beams": num_beams,
            }
        )
        return [[len(self.calls) - 1]]


class PipelineRefinementTests(unittest.TestCase):
    def test_refinement_uses_length_specific_minimums(self) -> None:
        config = AppConfig()
        gateway = TriModelModelGateway(config)
        fake_model = _FakeModel()
        fake_tokenizer = _FakeTokenizer(
            {
                0: " ".join(["short"] * 20),
                1: " ".join(["medium"] * 45),
                2: " ".join(["long"] * 85),
            }
        )
        gateway._load_refiner = lambda: {"model": fake_model, "tokenizer": fake_tokenizer}  # type: ignore[method-assign]

        gateway.refine_summary("Draft summary text.", SummaryLength.SHORT)
        gateway.refine_summary("Draft summary text.", SummaryLength.MEDIUM)
        gateway.refine_summary("Draft summary text.", SummaryLength.LONG)

        self.assertEqual(fake_model.calls[0]["min_new_tokens"], config.refinement_min_new_tokens_short)
        self.assertEqual(fake_model.calls[1]["min_new_tokens"], config.refinement_min_new_tokens_medium)
        self.assertEqual(fake_model.calls[2]["min_new_tokens"], config.refinement_min_new_tokens_long)
        self.assertLess(fake_model.calls[0]["min_new_tokens"], fake_model.calls[1]["min_new_tokens"])
        self.assertLess(fake_model.calls[1]["min_new_tokens"], fake_model.calls[2]["min_new_tokens"])

    def test_refinement_retries_then_falls_back_to_bounded_summary(self) -> None:
        config = AppConfig()
        gateway = TriModelModelGateway(config)
        fake_model = _FakeModel()
        fake_tokenizer = _FakeTokenizer(
            {
                0: "too short",
                1: "still short",
            }
        )
        gateway._load_refiner = lambda: {"model": fake_model, "tokenizer": fake_tokenizer}  # type: ignore[method-assign]
        draft_summary = " ".join(f"detail{i}" for i in range(1, 121))

        refined = gateway.refine_summary(draft_summary, SummaryLength.MEDIUM)
        min_words, max_words = refinement_word_bounds(SummaryLength.MEDIUM)

        self.assertEqual(len(fake_model.calls), 2)
        self.assertGreaterEqual(word_count(refined), min_words)
        self.assertLessEqual(word_count(refined), max_words)


if __name__ == "__main__":
    unittest.main()
