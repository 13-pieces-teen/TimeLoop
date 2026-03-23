# Reproducibility — Environment & Settings

## Software Environment

| Component | Version |
|-----------|---------|
| Python | 3.14.x |
| OS | Windows 10/11 |
| gradio | 6.9.0 |
| PyYAML | (see requirements.txt) |
| sentence-transformers | (see requirements.txt) |

## LLM Configuration

| Setting | Value | Source |
|---------|-------|--------|
| Model | Qwen/Qwen2.5-7B-Instruct | `config/settings.yaml` |
| Provider | SiliconFlow API | `.env` |
| Temperature | 0.7 | `config/settings.yaml` |
| Max tokens | 1024 | `config/settings.yaml` |
| Response format | `{"type": "json_object"}` | `src/game/processors/llm_call.py` |
| Max retries | 1 | `config/settings.yaml` |

## Game Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Starting sanity | 100 | `config/settings.yaml` |
| Sanity cap | 100 | `config/settings.yaml` |
| Time per turn | 15 min | `config/settings.yaml` |
| Game start | 8:00 PM | `config/settings.yaml` |
| Midnight (loop reset) | 12:00 AM | `config/settings.yaml` |
| Sanity decay per loop | 12 | `src/game/engine.py` |
| Time decay per loop | 15 min | `src/game/engine.py` |
| Trust carry ratio | 0.35 | `src/game/engine.py` |
| Trust base cap | 30 | `src/state/game_state.py` |
| Trust per-fact bonus | 10 | `src/state/game_state.py` |

## Consistency Settings

| Setting | Value |
|---------|-------|
| Embedding model | all-MiniLM-L6-v2 |
| Similarity threshold | 0.75 |
| Soft check enabled | false (dev-only) |
| Hard rules active | 5/10 |

## How to Reproduce

```bash
# 1. Clone and install
git clone <repo>
pip install -r requirements.txt

# 2. Configure API key
cp .env.example .env
# Edit .env with your SiliconFlow API key

# 3. Run evaluation
python -m eval.run_eval           # all scenarios
python -m eval.ablation_runner    # ablation study

# 4. Results appear in eval/results/
```
