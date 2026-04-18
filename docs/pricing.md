# Pricing

NeuroSleepNet is open-source software. You pay for hosted infrastructure, not behaviour.

---

## Plans

| | **Free** | **Pro** | **Enterprise** |
|---|---|---|---|
| **Memories** | 10,000 / project | 500,000 / project | Unlimited |
| **Projects** | 1 | Unlimited | Unlimited |
| **Retrieval calls** | 1,000 / day | 50,000 / day | Unlimited |
| **Batch write API** | ✅ | ✅ | ✅ |
| **Webhook events** | — | ✅ | ✅ |
| **Audit log retention** | 7 days | 90 days | Unlimited |
| **Support** | Community | Email | Dedicated SLA |
| **Self-hosted** | ✅ Free forever | ✅ Free forever | ✅ + Helm charts |
| **Price** | **Free** | **$29/mo** | **Contact us** |

---

## Free Tier — What's included

- **10,000 memories** per project (no credit card required)
- **1 project** namespace
- Full API access including `batch`, `dry_run`, and `snapshot/restore`
- Local offline cache always works — even on free tier
- Benchmark CLI (`nsn-bench`) is free and open-source

> No feature is locked behind a paywall. The free tier is intentionally generous enough to run a personal assistant, a research project, or a production prototype.

---

## Self-Hosted — Always Free

Running NeuroSleepNet on your own infrastructure is **free forever** regardless of scale. See the [self-hosted deployment guide](./self-hosted.md).

---

## nsn-bench — Standalone Open Source

The `nsn-bench` benchmark suite is a **separately installable, open-source** package:

```bash
pip install nsn-bench
```

Source: [github.com/neurosleepnet/nsn-bench](https://github.com/neurosleepnet/nsn-bench)

Run benchmarks without any NSN account:
```bash
nsn-bench run --model "your-model" --scenarios all --offline
```
