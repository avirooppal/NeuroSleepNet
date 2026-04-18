# Semantic Versioning Stability Contract

**Effective from:** v1.0.0  
**Maintained by:** NeuroSleepNet Core Team

---

## Our Promise

NeuroSleepNet follows [Semantic Versioning 2.0.0](https://semver.org/). This document is a **written promise** about what we will and will not break across releases.

---

## What is Stable (never breaks in 1.x)

These are the public-facing surfaces we guarantee stability on within a major version:

| Surface | Guaranteed Stable |
|---|---|
| `nsn.init(api_key, ...)` signature | ✅ New optional params only. Existing params never removed. |
| `nsn.wrap(agent, ...)` return contract | ✅ Always returns an object passing `isinstance(wrapped, OriginalClass)` |
| `nsn.remember()`, `nsn.recall()`, `nsn.forget()` | ✅ Signatures stable. New optional params only. |
| `nsn.snapshot()` / `nsn.restore()` JSON format | ✅ New keys may be added; existing keys never removed or renamed. |
| `nsn.status()` (terminal output format) | ⚠️ Content only. Exact string formatting may change. |
| REST API v1 endpoints (`/v1/memories`, `/v1/search`) | ✅ Additive only. No field removals or renames. |
| `MemoryCreate` / `MemorySearchResult` schemas | ✅ New optional fields only. |
| Error types (`NSNInitError`) | ✅ Types will not be renamed or moved. |

---

## What Can Change in Minor Releases (1.x → 1.y)

- **New optional parameters** on any existing function
- **New endpoints** on the REST API
- **New fields** in API response schemas (always optional)
- **New adapters** registered in `AdapterRegistry`
- **Default value changes** for new optional parameters only — never for existing ones
- **Internal implementation changes** that don't affect the public contract above

---

## What Requires a Major Version Bump (1.x → 2.0)

- Removing or renaming any **stable** parameter listed in the table above
- Changing the **type** of any existing parameter
- Changing the **return type** of any stable function
- Removing any **REST endpoint** listed as stable
- Removing any **field** from a stable API response schema
- Breaking the `isinstance()` guarantee from `TransparentProxy`
- Changing the SQLite offline cache file format in a way that discards data

---

## Deprecation Policy

Before removing anything:
1. Mark it deprecated in the next minor release with a `DeprecationWarning`
2. Keep it working for **at least one full minor release** (3 months minimum)
3. Remove it only in the next major version

Example:
```python
# v1.3 — deprecated, still works
def old_param(foo: str, bar: str = None):
    if bar:
        import warnings
        warnings.warn("'bar' is deprecated and will be removed in v2.0. Use 'baz' instead.", DeprecationWarning, stacklevel=2)
```

---

## Pre-1.0 Notice

Before `v1.0.0`, anything can change between minor versions. We will mark the stable release explicitly in the changelog and this document.

---

## How to Get Notified of Breaking Changes

- Watch the [GitHub releases](https://github.com/your-org/neurosleepnet/releases) page
- Breaking changes are always listed at the **top** of the release notes in a `## ⚠️ Breaking Changes` section
- Subscribe to our changelog at `https://neurosleepnet.ai/changelog`
