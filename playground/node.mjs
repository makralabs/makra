import {
  DEVELOPMENT_BASE_URL,
  DUMMY_API_KEY,
  Makra,
} from "../sdk/javascript/src/index.js";

const client = new Makra({
  apiKey: process.env.MAKRA_API_KEY || DUMMY_API_KEY,
  baseUrl: process.env.MAKRA_BASE_URL || DEVELOPMENT_BASE_URL,
});

console.log("ping:", JSON.stringify(await client.ping(), null, 2));

const url = process.argv[2];
if (url) {
  const result = await client.extract({
    urls: [url],
    schema: {
      title: "The page title",
      description: "A short description of the page",
    },
    config: {
      validation_mode: "repair",
    },
  });
  console.log("extract:", JSON.stringify(result, null, 2));
}
