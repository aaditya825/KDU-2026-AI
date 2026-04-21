# Hands-on Exercise 2: Self-Hosting a Quantized Model

## 1. Chosen Framework

I used **LM Studio** as the local model hosting framework.

## 2. Model Used

* **Model:** Qwen2.5-Coder-7B-Instruct
* **Format:** GGUF
* **Quantization:** Q4_K_M
* **Model Size:** 4.68 GB

This is a **quantized local model**, which means it has been compressed to reduce memory usage and make it practical to run on local hardware.

---

## 3. Working Local Model Setup

I successfully set up and ran the model locally using LM Studio.

### Setup Summary

1. Installed **LM Studio**
2. Downloaded a quantized GGUF model:

   * **Qwen2.5-Coder-7B-Instruct**
   * **Q4_K_M** quantization
3. Loaded the model inside LM Studio
4. Ran inference directly through the local chat interface

The screenshot confirms that the model was loaded and was able to generate a response locally.

---

## 4. Why I Chose This Framework

### Ease of Use

LM Studio is very easy to use because it provides:

* a simple graphical interface
* direct model download and loading
* local inference without complex setup
* quick testing through the chat UI

This made it a practical choice for completing the exercise quickly and clearly.

### Performance

The model performed well for local inference.
Since the model is quantized, it is smaller and more efficient than a full-precision version, which improves local usability.

### Hardware Constraints

I selected a **Q4_K_M quantized model** because quantization reduces:

* memory usage
* storage requirements
* computational cost

This makes it easier to run a 7B model on a normal local machine without requiring a very powerful GPU.

---

## 5. What Quantization Means

Quantization is the process of reducing model precision so that the model uses fewer computational resources.

In practical terms, quantization helps:

* reduce RAM/VRAM usage
* reduce model size
* improve local deployment feasibility
* speed up inference in many local setups

The trade-off is that a quantized model may lose a small amount of accuracy compared to a full-precision model, but it is much easier to run locally.

---

## 6. Demonstration of Inference Using the Model

### Input Prompt

**"Explain what quantization means in LLM deployment"**

### Model Output Summary

The model explained that quantization in LLM deployment means reducing the numerical precision of model weights and activations so that the model requires less memory and fewer compute resources. It also stated that this makes deployment easier on devices with limited hardware resources.

### Observation

The model generated a coherent and relevant answer locally, which demonstrates that:

* the model was successfully loaded
* inference worked correctly
* the local deployment was functional

---

## 7. Conclusion

This exercise demonstrated successful **local deployment of a quantized language model**.

I used **LM Studio** with the **Qwen2.5-Coder-7B-Instruct** quantized model in **GGUF Q4_K_M** format. The setup worked successfully, and I verified this by running a prompt locally and receiving a meaningful response. This approach was chosen because it is easy to set up, works well for local inference, and is suitable for machines with limited hardware resources.
