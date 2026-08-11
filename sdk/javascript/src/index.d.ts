export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[];
export interface JsonObject {
  [key: string]: JsonValue;
}

export interface MakraOptions {
  apiKey?: string;
  baseUrl?: string;
  apiVersion?: string;
  timeout?: number;
}

export interface ExtractOptions {
  urls: string[];
  outputSchema: JsonObject | JsonValue[];
  actions?: string[];
  config?: JsonObject;
}

export interface PreprocessOptions {
  urls: string[];
  options?: JsonObject;
}

export interface PageSchemaOptions {
  urls: string[];
  outputType?: "json" | "text";
  debugMode?: boolean;
  debugOutputType?: string;
}

export declare class MakraError extends Error {}

export declare class MakraAPIError extends MakraError {
  readonly statusCode: number;
  readonly body: unknown;
  readonly method: string;
  readonly path: string;
  readonly requestId?: string;
}

export declare class MakraConnectionError extends MakraError {
  readonly method?: string;
  readonly path?: string;
  readonly cause?: Error;
}

export declare class Makra {
  readonly apiKey: string;
  readonly baseUrl: string;
  readonly apiVersion: string;
  readonly timeout: number;

  constructor(options?: MakraOptions);
  ping(): Promise<unknown>;
  extract(options: ExtractOptions): Promise<unknown>;
  preprocess(options: PreprocessOptions): Promise<unknown>;
  pageSchema(options: PageSchemaOptions): Promise<unknown>;
  formatMarkdown(url: string): Promise<string>;
}

export declare const PRODUCTION_BASE_URL = "https://api.makralabs.org";
export declare const DEVELOPMENT_BASE_URL = "http://localhost:6900";
export declare const DUMMY_API_KEY = "makra-development-key";
