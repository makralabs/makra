# Makra JavaScript SDK

The official JavaScript client for the Makra web extraction API.

## Install

```bash
npm install makra
```

## Use

```js
import { Makra } from "makra";

const client = new Makra({ apiKey: "your-api-key" });
const result = await client.extract({
  urls: ["https://example.com"],
  outputSchema: { title: "The page title" },
});
console.log(result);
```

The production API defaults to `https://api.makralabs.org`. To use the local
server:

```js
import { DEVELOPMENT_BASE_URL, Makra } from "makra";

const client = new Makra({
  apiKey: "development-key",
  baseUrl: DEVELOPMENT_BASE_URL,
});
```

Configuration may also be supplied through `MAKRA_API_KEY` and
`MAKRA_BASE_URL`. See [`../SPEC.md`](../SPEC.md) for the complete contract.
