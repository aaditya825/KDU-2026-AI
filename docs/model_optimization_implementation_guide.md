# Model Optimization Exercise: Implementation Guide

## Purpose

This guide breaks the exercise into concrete implementation tasks. It explains:

- what to build in each phase
- what the expected inputs and outputs look like
- what code files to create
- how each part contributes to the final deliverables

The goal is not to train the best model possible. The goal is to show correct workflow, correct formatting, low-cost fine-tuning, and clear understanding of LoRA and reinforcement fine-tuning concepts.

This document is the primary working reference for the implementation. Each phase should be built by following this guide, and the guide may be updated during implementation if clearer structure, assumptions, or execution details are needed.

## Working Assumptions

- We will use OpenAI API keys where an API-backed LLM step is needed during development, evaluation, or comparison.
- OpenRouter may still be discussed as an alternative provider in the report because it is mentioned in the exercise, but the implementation baseline for this project is OpenAI API access.
- The LoRA fine-tuning workflow itself still targets a lightweight open model and Unsloth-based training, because the exercise is about adapting and deploying a small model rather than fine-tuning an OpenAI-hosted model.
- Cost should still be kept low even when OpenAI API keys are available. Avoid unnecessary calls, retries, and oversized prompts.

## What You Need to Submit

You need to produce these deliverables:

1. `unsloth_train.py`
   LoRA fine-tuning script using Unsloth.

2. `json_grader.py`
   Programmable grader that rewards valid JSON outputs.

3. A short report
   This should explain:
   - formatting issues and how they were fixed
   - why `<|eot_id|>` matters
   - how reward logic works in RFT
   - LoRA trade-offs such as rank changes
   - how to merge and deploy the model with GGUF and Ollama

4. Training dataset
   A `JSONL` file with around 50 examples.

## Recommended Project Output Structure

You can organize the exercise like this:

```text
docs/
  model_optimization_implementation_guide.md
  report.md

data/
  company_syntax_train.jsonl

phase1/
  prepare_phase1_dataset.py

phase2/
  unsloth_train.py

phase3/
  json_grader.py

outputs/
  lora_adapter/
  merged_model/
  gguf/
```

This is only a suggested structure. The exercise does not force exact filenames, but using a clean layout makes the deliverables easier to review.

## Recommended Implementation Style

For this project, the preferred implementation style is:

1. Keep final deliverables in Python scripts and Markdown documents
2. Optionally use a notebook or Colab only for experimentation
3. Move final working logic back into the repo as scripts

That means the expected implementation baseline is:

- `phase1/`, `phase2/`, and `phase3/` for runnable code
- `data/` for dataset files
- `docs/` for working notes and the final report

This guide should be treated as the execution checklist while building each phase.

## Phase 1: Dataset Preparation and Formatting

### Objective

Teach a small model proprietary company syntax and structured outputs using a small, well-formatted supervised fine-tuning dataset.

### What You Need to Implement

Create a dataset of 50 examples in `JSONL` format. Each example should represent:

- a user question or task
- company-specific acronyms or internal syntax
- the exact structured response the model should produce

The main focus is not dataset size. The main focus is formatting the training examples correctly for instruction tuning.

### What the Input Should Look Like

You need examples such as:

- input question using company language
- desired answer in strict JSON

Simple conceptual example:

```text
User asks: "Convert ticket ABC into company incident format"
Expected answer: JSON with required company fields
```

### Recommended Dataset Content

Your 50 examples should cover:

- acronym expansion
- company-specific field naming
- structured JSON outputs
- a few slightly varied prompts for the same output format
- both simple and slightly complex cases

Example types:

1. Acronym interpretation
2. Structured ticket conversion
3. Internal command translation
4. Compliance-style formatted response
5. Strict schema output

### Expected Output Format

Each line in the dataset should be one training example.

If using chat-style formatting, each example should preserve conversation structure and end-of-turn boundaries.

Conceptual ChatML-style example:

```json
{
  "messages": [
    {"role": "system", "content": "You are a model that outputs strict company JSON."},
    {"role": "user", "content": "Translate HDO request into company format."},
    {"role": "assistant", "content": "{\"request_type\":\"handover\",\"code\":\"HDO\"}<|eot_id|>"}
  ]
}
```

If using Llama 3 instruction format, the same idea applies: preserve the exact special tokens and conversation boundaries required by the model template.

### Key Requirement: `<|eot_id|>`

This token marks the end of a response turn.

If it is missing during training, the model may learn bad response boundaries. At inference time this can cause:

- responses that keep generating too long
- two answer patterns blending together
- invalid JSON caused by extra trailing text
- poor separation between prompt and answer behavior

This is one of the main things the exercise expects you to understand and explain.

### What to Implement for Phase 1

1. Create `data/company_syntax_train.jsonl`
2. Ensure every example follows one chat template consistently
3. Ensure assistant outputs are in the final format you want to teach
4. Ensure end-of-turn handling is correct for the chosen model template
5. Load the dataset using Hugging Face `datasets`

Implementation note:
For this project, Phase 1 will be implemented with a Python script named `phase1/prepare_phase1_dataset.py`. The generated dataset will keep:

- a readable `messages` field for inspection
- a training-ready `text` field formatted in Llama 3 instruction style

This makes `<|eot_id|>` placement explicit in the final training text while keeping the source conversation easy to read and validate.

### Code Expectation for Phase 1

Inside the training script, you should be able to:

- load the JSONL file
- inspect a sample row
- apply the correct prompt template if needed
- pass the dataset into Unsloth training

## Phase 2: LoRA Fine-Tuning with Unsloth

### Objective

Fine-tune a small model cheaply using LoRA instead of full fine-tuning.

### What You Need to Implement

Create an Unsloth training script that:

- loads a lightweight base model
- applies LoRA adapters
- trains on the 50-example dataset
- saves the trained adapter

If any helper generation is used while creating synthetic training examples or evaluating outputs, OpenAI API access may be used carefully, but the actual model being fine-tuned should remain a lightweight open model compatible with Unsloth.

### Expected Input

Inputs to the training script:

- base model name
- dataset path
- LoRA configuration
- training hyperparameters

Practical example:

```text
Base model: Llama 3 8B or another lightweight compatible model
Dataset: data/company_syntax_train.jsonl
LoRA rank: 8 to start
Precision/quantization: use settings suitable for free GPU
```

### Expected Output

Outputs from training:

- saved LoRA adapter weights
- tokenizer files if needed
- training logs

Typical output directory:

```text
outputs/lora_adapter/
```

### What the Script Should Contain

Your `phase2/unsloth_train.py` should include:

1. Base model loading with Unsloth
2. Tokenizer loading
3. LoRA adapter configuration
4. Dataset loading
5. Trainer setup
6. Training call
7. Save adapter output

### Minimum Things to Explain in the Report

- Why LoRA is used instead of full fine-tuning
- Why Unsloth is suitable for free or low-memory GPU setups
- Why a small rank like `r=8` is a good low-cost starting point

## Phase 3: Programmable JSON Grader

### Objective

Create a simple reward function that checks whether model output is valid JSON.

### What You Need to Implement

Write a Python function that:

- takes model output text
- runs `json.loads()`
- returns `1.0` if parsing succeeds
- returns `-1.0` if parsing fails

### Expected Input

Input to the grader:

```python
'{"request_type": "handover", "code": "HDO"}'
```

or invalid output:

```python
'{"request_type": "handover", "code": HDO}'
```

### Expected Output

For valid JSON:

```python
1.0
```

For invalid JSON:

```python
-1.0
```

### What the Script Should Contain

Your `phase3/json_grader.py` should include:

1. A grading function
2. A few sample test cases
3. Optional command-line usage for quick testing

If later phases use LLM-based comparison, repair, or evaluation helpers, those helper utilities may use OpenAI API keys. The JSON validity grader itself should remain deterministic and local.

### What You Must Explain

You also need to explain how this reward is used in reinforcement fine-tuning:

- In PPO, the reward score is used to push the model toward outputs that score better
- In DPO, preference learning uses better outputs versus worse outputs, even though the setup differs from direct scalar reward optimization

The important idea is:

- valid outputs are rewarded
- invalid outputs are penalized
- over time the model is optimized toward the desired behavior

You do not need to build a full PPO training pipeline unless your instructor explicitly requires it. For this exercise, showing the grader and correctly explaining how it connects to RFT is usually sufficient.

## Phase 4: LoRA Rank Analysis

### Objective

Explain what changes when LoRA rank increases from `8` to `16`.

### What Is Expected

You are expected to discuss trade-offs, not just define rank.

### Core Explanation

When `r` increases from `8` to `16`:

- the number of trainable adapter parameters increases
- VRAM usage increases
- training cost increases
- the adapter can capture more task-specific information
- quality may improve if the task is complex enough

### What to Mention in the Report

- `r=8` is cheaper and lighter
- `r=16` gives more adaptation capacity
- larger rank is not always worth the extra memory for a small dataset
- for 50 examples, very high rank may be unnecessary and may overfit

## Phase 5: Merge and Deploy

### Objective

Prepare the trained model for practical use after training.

### What You Need to Implement or Document

After training, describe or perform these steps:

1. Merge LoRA adapters into the base model
2. Export the merged model to a `GGUF` format
3. Quantize to 4-bit if the workflow supports it
4. Make it usable in Ollama

### Expected Input

Inputs for deployment:

- base model
- trained LoRA adapter
- export toolchain

### Expected Output

Deployment outputs:

- merged model files
- `GGUF` file
- Ollama-compatible model package or instructions

Example output locations:

```text
outputs/merged_model/
outputs/gguf/model-q4.gguf
```

### What to Explain in the Report

- why merging is useful for deployment
- why GGUF is useful for lightweight inference
- why 4-bit quantization reduces memory usage
- how Ollama can serve the exported model locally

## Task-by-Task Execution Plan

### Task 1: Create the Dataset

Expectation:
Build 50 clean examples that map company-style prompts to strict JSON answers.

Input:
Raw business phrases, acronyms, response schema.

Output:
`data/company_syntax_train.jsonl`

Done when:
You have 50 rows and each row follows one consistent format.

### Task 2: Validate Dataset Formatting

Expectation:
Ensure the chosen chat template is correct and includes proper response boundaries.

Input:
Dataset rows.

Output:
Formatted examples ready for tokenization and training.

Done when:
Assistant responses are consistent and end-of-turn behavior is explicitly handled.

### Task 3: Build the Unsloth Training Script

Expectation:
Create a runnable LoRA fine-tuning script.

Input:
Base model name, dataset path, LoRA config, training config.

Output:
`phase2/unsloth_train.py`

Done when:
The script can load data, configure LoRA, train, and save adapters.

### Task 4: Build the JSON Grader

Expectation:
Create a minimal reward function for valid JSON.

Input:
Model output text.

Output:
`phase3/json_grader.py`

Done when:
It returns `1.0` for valid JSON and `-1.0` for invalid JSON.

### Task 5: Write the RFT Explanation

Expectation:
Explain how the grader reward would influence optimization in PPO or preference optimization workflows.

Input:
Grader output logic.

Output:
Section in `docs/report.md`

Done when:
The explanation clearly connects reward signal to model improvement.

### Task 6: Analyze LoRA Rank Trade-Offs

Expectation:
Explain what changes when rank increases from `8` to `16`.

Input:
LoRA configuration.

Output:
Section in `docs/report.md`

Done when:
The explanation covers parameter count, VRAM, cost, and capacity trade-offs.

### Task 7: Merge and Export

Expectation:
Document or implement the deployment workflow.

Input:
Base model plus trained adapter.

Output:
Merged model and GGUF export instructions or artifacts.

Done when:
You can clearly describe how the trained model reaches Ollama.

## Suggested Deliverable Mapping

### Deliverable 1: Unsloth Training Script

To achieve this:

- create the dataset first
- choose one prompt template
- implement LoRA setup in `phase2/unsloth_train.py`
- save adapters into `outputs/lora_adapter/`

### Deliverable 2: Programmable Grader Script

To achieve this:

- implement `json.loads()` validation
- return `1.0` or `-1.0`
- include a small self-test section

### Deliverable 3: Report

To achieve this, include these sections:

1. Problem overview
2. Dataset design
3. Formatting trap and `<|eot_id|>` explanation
4. JSON grader and reward logic
5. LoRA rank trade-offs
6. Merge, quantization, GGUF, and Ollama deployment

## Suggested Input and Output Examples

### Example Training Input

```json
{
  "messages": [
    {"role": "system", "content": "Return only strict JSON using company schema."},
    {"role": "user", "content": "Interpret HDO request for team OPS."},
    {"role": "assistant", "content": "{\"type\":\"handover\",\"team\":\"OPS\",\"code\":\"HDO\"}<|eot_id|>"}
  ]
}
```

### Example Inference Prompt

```text
Interpret P1 escalation for team NET using company schema.
```

### Example Desired Inference Output

```json
{
  "priority": "P1",
  "department": "NET",
  "request_type": "escalation"
}
```

### Example Grader Usage

```python
reward = grade_json_output('{"priority":"P1","department":"NET","request_type":"escalation"}')
# reward = 1.0
```

## Recommended Order of Work

1. Design the output schema
2. Write the 50 training examples
3. Validate formatting and end-of-turn handling
4. Build the Unsloth LoRA training script
5. Build the JSON grader
6. Train and save the adapter
7. Document reward logic for RFT
8. Document LoRA rank trade-offs
9. Merge and export for GGUF and Ollama
10. Finalize the report

## How This Guide Should Be Used During Implementation

When implementing the project:

1. Read the relevant phase section before writing code
2. Use the task expectation, input, and output notes as the acceptance criteria
3. Update this guide if implementation decisions become more specific
4. Keep the final scripts aligned with the structure described here

This keeps the implementation, deliverables, and report consistent with one source of truth.

## Final Quality Checklist

Before submission, verify:

- dataset has about 50 examples
- one formatting template is used consistently
- assistant targets are strict JSON
- end-of-turn token handling is correct
- LoRA script runs and saves adapter weights
- grader returns the correct reward values
- report covers PPO or DPO reward usage
- report explains rank `8` versus `16`
- deployment path to GGUF and Ollama is clearly described

## Bottom Line

This exercise expects a small but complete workflow:

- prepare correctly formatted training data
- fine-tune with LoRA using Unsloth
- build a JSON-validity reward function
- explain how that reward would be used in RFT
- analyze LoRA trade-offs
- describe or implement deployment to GGUF and Ollama

If all of those pieces are present and clearly explained, the deliverables should satisfy the exercise requirements.
