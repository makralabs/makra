# Makra SDK

Official clients for the hosted Makra API. Python is the documented public
language. JavaScript exists in this repository but is not part of the current
documentation release.

## Package map

| Path | Role |
| --- | --- |
| `sdk/python` | Published `makra` package (0.2.0), Python 3.9+ |
| `sdk/javascript` | `makra` package target (0.2.0), Node 18+ ESM |
| `sdk/SPEC.md` | Language-neutral SDK contract |
| `playground/` | Local scripts against `http://localhost:8080` |

The HTTP contract is owned by the backend: `GET /openapi.yaml`. Do not rename
wire identifiers such as `/workflows/extract`, `Feature`, or `submit_extract()`.

## Public examples

Python only until the JavaScript documentation returns. The copy-pasteable
quickstart is `sdk/python/examples/golden_quickstart.py`. It must stay identical
to the first Python fence in the v0.0.3 first-extraction page.

## Definition of done

- Python: lint, typecheck, and tests pass, including the golden local contract.
- JavaScript: tests and typecheck pass.
- New public examples are Python and runnable without credentials against the
  local mock used by `tests/test_golden_quickstart.py`.
