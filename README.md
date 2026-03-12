# TimeLoop: The Unspeakable Midnight

A Lovecraftian time-loop interactive text adventure powered by LLM, built for COMP5423 Natural Language Processing.

## Quick Start

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your API key:

```env
# SiliconFlow (硅基流动) -- default
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
```

Supports any OpenAI-compatible provider (SiliconFlow, OpenAI, DeepSeek, etc.) -- just change the `OPENAI_BASE_URL`.

```bash
python main.py
```

Then open http://localhost:7860 in your browser.

## Architecture

- **NLU + NLG**: Single LLM API call (GPT-4o-mini) with structured JSON output handles intent recognition, narrative generation, and state update suggestions simultaneously.
- **State Engine**: Structured `GameState` (per-loop) + `LoopMemory` (persistent across loops) + `SanitySystem` (maps sanity value to narrative style).
- **Consistency Checker**: Hard rules (deterministic Python checks) + soft check (sentence-transformers semantic similarity).
- **UI**: Gradio with narrative panel, status bar, choice buttons, and collapsible debug panel.

## Project Structure

```
config/          -- Settings, prompt templates, NPC profiles
data/            -- World data, NPC data, plot graph, consistency rules
src/llm/         -- LLM API client, prompt builder, output parser
src/state/       -- Game state, loop memory, sanity system
src/consistency/  -- Hard rules checker, semantic soft checker
src/game/        -- Game engine, loop manager
src/ui/          -- Gradio application
logs/            -- Game trajectory logs (auto-generated)
```
