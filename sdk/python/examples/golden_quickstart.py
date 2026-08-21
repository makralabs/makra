from makra import Makra

urls = ["https://shop.example/products/atlas-lamp"]
schema = {
    "name": "The main product name",
    "price": "The current selling price as displayed on the page",
}

with Makra() as client:
    response = client.extract(urls, schema)

if not isinstance(response, dict):
    raise RuntimeError("Expected a JSON object response")

if response.get("status") not in {"succeeded", "partial"}:
    raise RuntimeError(response.get("message", "Extraction failed"))

data = response.get("data", {})
product = data.get(urls[0])
print(product)
