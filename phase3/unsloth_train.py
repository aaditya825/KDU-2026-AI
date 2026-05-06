"""Train a LoRA adapter, with optional merge and GGUF export."""

from __future__ import annotations

import argparse
from pathlib import Path

DATASET_PATH = Path("data/company_syntax_train.jsonl")
OUTPUT_DIR = Path("outputs/lora_adapter")
MERGED_DIR = Path("outputs/merged_model")
GGUF_DIR = Path("outputs/gguf_model")
DEFAULT_MODEL_NAME = "unsloth/Llama-3.2-1B-Instruct-bnb-4bit"
DEFAULT_MAX_SEQ_LENGTH = 2048

SYSTEM_PROMPT = (
    "You are the company syntax normalizer. Return strict JSON only using the "
    "approved schema keys. Do not add markdown, prose, or comments."
)


def load_dataset_file(dataset_path: Path):
    """Load the Phase 1 dataset and require the training text column."""
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit("Missing dependency: datasets. Run: pip install datasets") from exc

    dataset = load_dataset("json", data_files=str(dataset_path), split="train")
    if "text" not in dataset.column_names:
        raise ValueError(
            f"Dataset at {dataset_path} is missing the required 'text' column."
        )
    return dataset


def load_model(model_name: str, max_seq_length: int, lora_rank: int):
    """Load the base model and attach LoRA adapters."""
    try:
        from unsloth import FastLanguageModel
    except ImportError as exc:
        raise SystemExit("Missing dependency: unsloth. Install via: pip install unsloth") from exc

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=None,
        load_in_4bit=True,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=lora_rank,
        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],
        lora_alpha=lora_rank,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
        max_seq_length=max_seq_length,
        use_rslora=False,
        loftq_config=None,
    )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer


def build_trainer(
    model,
    tokenizer,
    dataset,
    output_dir: Path,
    max_seq_length: int,
    batch_size: int,
    gradient_accumulation_steps: int,
    max_steps: int,
    learning_rate: float,
):
    """Build the Unsloth/TRL SFT trainer."""
    try:
        from transformers import TrainingArguments
        from trl import SFTTrainer
        from unsloth import is_bfloat16_supported
    except ImportError as exc:
        raise SystemExit(
            "Missing dependencies: transformers, trl, or unsloth."
        ) from exc

    training_args = TrainingArguments(
        per_device_train_batch_size=batch_size,
        gradient_accumulation_steps=gradient_accumulation_steps,
        warmup_steps=5,
        max_steps=max_steps,
        learning_rate=learning_rate,
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        logging_steps=1,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=3407,
        output_dir=str(output_dir),
        report_to="none",
        save_strategy="steps",
        save_steps=max(1, max_steps),
    )

    return SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_length,
        dataset_num_proc=1,
        packing=False,  # keep examples separate to avoid mixing short records
        args=training_args,
    )


def merge_adapter(model, tokenizer, merged_dir: Path, save_method: str = "merged_16bit") -> None:
    """Merge the trained adapter into the base model weights."""
    merged_dir.mkdir(parents=True, exist_ok=True)
    print(f"Merging adapter into base model ({save_method}) -> {merged_dir}")
    model.save_pretrained_merged(str(merged_dir), tokenizer, save_method=save_method)


def export_gguf(model, tokenizer, gguf_dir: Path, quantization: str = "q4_k_m") -> None:
    """Export the model as GGUF for llama.cpp or Ollama."""
    gguf_dir.mkdir(parents=True, exist_ok=True)
    print(f"Exporting GGUF ({quantization}) -> {gguf_dir}")
    model.save_pretrained_gguf(str(gguf_dir), tokenizer, quantization_method=quantization)


def generate_ollama_modelfile(gguf_dir: Path, quantization: str = "q4_k_m") -> None:
    """Write a basic Ollama Modelfile next to the GGUF output."""
    gguf_filename = f"model-{quantization.upper()}.gguf"
    modelfile_content = f"""\
FROM ./{gguf_filename}

SYSTEM \"\"\"{SYSTEM_PROMPT}\"\"\"

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER stop "<|eot_id|>"
"""
    modelfile_path = gguf_dir / "Modelfile"
    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"Ollama Modelfile written to {modelfile_path}")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Train a LoRA adapter with Unsloth, then optionally merge and export.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH, help="Path to the Phase 1 JSONL training file.")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR, help="Directory for the LoRA adapter.")
    parser.add_argument("--merged-dir", type=Path, default=MERGED_DIR, help="Directory for the merged model.")
    parser.add_argument("--gguf-dir", type=Path, default=GGUF_DIR, help="Directory for the GGUF export.")
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME, help="Base model name.")
    parser.add_argument("--max-seq-length", type=int, default=DEFAULT_MAX_SEQ_LENGTH, help="Maximum token length per example.")
    parser.add_argument("--lora-rank", type=int, default=8, help="LoRA rank. Higher rank costs more VRAM.")
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4, help="Effective batch = batch size x this value.")
    parser.add_argument("--max-steps", type=int, default=60)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--merge", action="store_true", help="Merge the LoRA adapter into the base model.")
    parser.add_argument("--merge-method", default="merged_16bit", choices=["merged_16bit", "merged_4bit"], help="How to save the merged model.")
    parser.add_argument("--export-gguf", action="store_true", help="Export a GGUF and write an Ollama Modelfile.")
    parser.add_argument("--gguf-quant", default="q4_k_m", choices=["q4_0", "q4_k_m", "q5_k_m", "q8_0"], help="GGUF quantization method.")
    parser.add_argument("--preview-only", action="store_true", help="Load and preview the dataset without training.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.export_gguf:
        args.merge = True

    dataset = load_dataset_file(args.dataset)
    print(f"Loaded {len(dataset)} rows from {args.dataset}")
    print(f"Columns: {dataset.column_names}")

    if args.preview_only:
        print(f"Sample training text:\n{dataset[0]['text'][:300]}...")
        return

    args.output_dir.mkdir(parents=True, exist_ok=True)

    model, tokenizer = load_model(
        model_name=args.model_name,
        max_seq_length=args.max_seq_length,
        lora_rank=args.lora_rank,
    )

    trainer = build_trainer(
        model=model,
        tokenizer=tokenizer,
        dataset=dataset,
        output_dir=args.output_dir,
        max_seq_length=args.max_seq_length,
        batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        max_steps=args.max_steps,
        learning_rate=args.learning_rate,
    )

    print(
        f"Starting training - steps={args.max_steps}, "
        f"lr={args.learning_rate}, lora_rank={args.lora_rank}"
    )
    trainer.train()

    model.save_pretrained(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    print(f"LoRA adapter saved to {args.output_dir}")

    if args.merge:
        merge_adapter(model, tokenizer, args.merged_dir, save_method=args.merge_method)

    if args.export_gguf:
        export_gguf(model, tokenizer, args.gguf_dir, quantization=args.gguf_quant)
        generate_ollama_modelfile(args.gguf_dir, quantization=args.gguf_quant)


if __name__ == "__main__":
    main()
