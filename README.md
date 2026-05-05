# KDU-2026-AI Model Optimization Exercise

This repository contains a hands-on LLM model optimization exercise focused on:

- Phase 1: building a correctly formatted training dataset
- Phase 2: implementing a programmable JSON validity grader
- Phase 3: training and exporting a LoRA-adapted model with Unsloth

The exercise goal is to teach a lightweight Llama-family model proprietary company syntax and strict structured JSON outputs using low-cost fine-tuning and reinforcement-style reward logic.

## Project Structure
- `phase1/`: dataset generation and formatting script
- `phase2/`: programmable JSON grader
- `phase3/`: Unsloth LoRA training and export script
- `data/`: generated JSONL dataset
- `docs/`: exercise prompt and implementation guide
- `outputs/`: saved adapters, merged models, and exported artifacts

## Current Deliverables
- `phase1/prepare_phase1_dataset.py`
- `phase2/json_grader.py`
- `phase3/unsloth_train.py`
- `data/company_syntax_train.jsonl`
- `docs/model_optimization_implementation_guide.md`

## Exercise Context
- Reference prompt: `docs/question.txt`
- Training approach: LoRA with Unsloth
- Reward logic: valid JSON = `1.0`, invalid JSON = `-1.0`
- Deployment target: merged adapter, 4-bit GGUF, Ollama compatibility

## Notes
- OpenAI API keys may be used for helper or evaluation steps when needed.
- The actual fine-tuning target remains a lightweight open model, not an OpenAI-hosted fine-tune.
- Phase 3 training is intended for a GPU-capable environment such as Colab or Linux, especially for 8B-class models.
