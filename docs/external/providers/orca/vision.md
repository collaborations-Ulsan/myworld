> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Vision (image input)

> Send images to vision-capable models via image_url content parts.

Send an image as a content part with `type: "image_url"`. Pass a
publicly-reachable `https://` URL — this is the most universally
supported form.

`data:image/...;base64,...` inline URIs work for OpenAI and Gemini
targets. For Anthropic and xAI Grok models, prefer hosting the image
behind an `https://` URL or use the provider's native HTTP shape
(see [Native Formats](/native-formats/anthropic)) when sending base64.

```python theme={null}
resp = client.chat.completions.create(
    model="openai/gpt-4o-mini",
    messages=[{
        "role": "user",
        "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": {"url": "https://example.com/cat.jpg"}},
        ],
    }],
)
```

## Vision-capable model families

Vision works against any upstream model that accepts image input.
Examples:

* OpenAI `gpt-4o*` and `gpt-4.1*` family
* Anthropic Claude 4 family (all current models)
* Google Gemini multimodal (`gemini-{2.5,3,3.1}-{flash,pro}`)
* xAI Grok 4 family (vision is built into general Grok 4 chat models)

## Size limits

Each upstream provider enforces its own per-image size cap (typically
in the single-digit-MB range for inline base64 and higher for hosted
URLs). OrcaRouter respects the upstream's limit, so exceeding it
surfaces as a 400 from the provider. Check the upstream's current
vision documentation for the exact number.
