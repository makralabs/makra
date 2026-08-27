import {
  ExtractOptions,
  Makra,
  ProxyRegion,
  SchemaOptions,
  type ExtractResponse,
  type ExtractRequestOptions,
  type HealthResponse,
  type ResponseBody,
  type RunResult,
} from "./src/index.js";

const client = new Makra();
const extractOptions: ExtractRequestOptions = {
  urls: ["https://example.com"],
  schema: { title: "string" },
  config: new ExtractOptions({ proxyRegion: ProxyRegion.country("DE") }),
};
const schemaOptions = new SchemaOptions({ postReadyWaitMs: 0 });

const health: Promise<HealthResponse | ResponseBody> = client.ping();
const extract: Promise<ExtractResponse | ResponseBody> = client.extract(extractOptions);
const result: Promise<RunResult | ResponseBody> = client.getRunResult("run-1");
void schemaOptions;
void health;
void extract;
void result;
