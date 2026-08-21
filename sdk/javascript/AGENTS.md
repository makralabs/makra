# JavaScript SDK

Package `makra`, ESM, Node 18+, no runtime dependencies. Public documentation
and examples are Python-only until this package is covered again.

## Commands

From `sdk/javascript`:

```bash
npm test
npm run typecheck
npm run pack:check
```

`npm test` runs `node --test`. There is no separate lint script; keep the
source consistent with the existing modules in `src/`.

## Notes

Method names are camelCase (`extractStream`, `submitExtract`). Wire paths stay
`/workflows/extract` and `/workflows/schema`. Do not add JavaScript snippets to
the current v0.0.3 docs.
