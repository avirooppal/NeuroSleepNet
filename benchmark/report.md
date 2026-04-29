# Benchmark Report: SLM Memory Performance

This report evaluates the performance of **Llama 3.2:1b** (Small Language Model) with and without the **NeuroSleepNet** memory layer.

## Methodology
- **Model**: Llama 3.2:1b (running via Ollama)
- **Scenarios**: Multi-session coding tasks (10 turns total across 2 users)
- **Metrics**: String-based recall accuracy of project names, coding preferences, and past bug fixes.

## Results Summary

| Mode | Avg Memory Score | Key Observation |
| :--- | :--- | :--- |
| **RAW** | 38.9% | Strong instruction following for current prompt, but 0% recall of past sessions. |
| **NSN** | 44.4% | Recalled specific bug fixes (100% on complex fix task vs 0% for RAW). |

## Deep Dive: The "Alice" Scenario (Turn 4)
In this turn, the user asked for tips on a `matrix_multiply` function based on a "previous fix" (using `numpy.complex128` for complex numbers).

- **RAW Model**: Failed completely (0% score). It provided generic matrix multiplication tips but had no knowledge of the complex number requirement.
- **NSN Model**: Succeeded perfectly (100% score). It retrieved the memory of the `complex128` fix and explicitly instructed the user to apply it to the new function.

## Conclusion
Even for a 1B parameter model, NeuroSleepNet provides a decisive advantage in **contextual continuity**. While the model sometimes ignores constraints in the prompt (e.g., the "no external dependencies" rule for Bob), the ability to inject the *exact* technical fix from a previous session allows the SLM to perform tasks that are impossible for a raw model without memory.

> [!TIP]
> This benchmark is reproducible via `uv run python benchmark/run.py`.
