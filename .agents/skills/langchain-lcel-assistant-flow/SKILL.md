---
name: "langchain-lcel-assistant-flow"
description: "Use when implementing or evolving the LangChain execution flow for this assistant, including prompts, chat models, LCEL composition, structured outputs, and later routing, tools, memory, or multimodal message construction."
---

# LangChain LCEL Assistant Flow

Use this skill for LangChain-specific implementation work in this repository.

## Read first
- [AGENTS.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\AGENTS.md)
- [04_hybrid_service_lcel_mvp.md](C:\Users\Dell\Desktop\Phase3-AI\06_langchain\docs\mvp_approaches\04_hybrid_service_lcel_mvp.md)

## Current phase
Start with the smallest useful LCEL path:

- `ChatPromptTemplate`
- one chat model
- LCEL pipe composition
- `.invoke()`

Only add the next primitive when the corresponding feature is requested.

## Use this skill when
- implementing the first text-only chain
- adding structured outputs
- introducing routing
- adding tools
- adding memory
- later adding multimodal input handling

## Recommended progression

### Phase 1: text-only
- `ChatPromptTemplate`
- provider-backed chat model
- `prompt | model`

### Phase 2: stable typed responses
- `.with_structured_output()`
- Pydantic response model

### Phase 3: multiple routes
- `RouteResolver` first
- then `RunnableBranch` once more than one route is real

### Phase 4: tools
- define tool functions with `@tool`
- attach tools with `.bind_tools()`
- keep tools outside the orchestrator

### Phase 5: memory
- wrap the selected chain with `RunnableWithMessageHistory`
- keep history storage outside use-case logic

### Phase 6: multimodal
- use multimodal content blocks inside `HumanMessage`
- do not rely on a separate `ImageContent` abstraction

## Guardrails

- do not overbuild the LangChain graph before a second real branch exists
- keep prompt construction separate from model selection
- keep chain assembly readable and local
- prefer explicit LCEL composition over hidden helper magic

## Output expectations
When using this skill, prefer:

- small chain builders
- typed schemas
- explicit prompt variables
- clear upgrade path for the next feature phase
