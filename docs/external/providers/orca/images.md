> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# Images

> Generate and edit images via /v1/images/generations and /v1/images/edits, or via chat completions with imagine-capable models.

OrcaRouter exposes image generation through two paths, depending on
which model you pick:

1. **`/v1/images/generations`** — OpenAI image API shape. Best for
   dedicated image-generation models (DALL-E replacement family,
   Imagen, Grok Imagine).
2. **`/v1/chat/completions`** — chat-style image generation. Best when
   you want a model that returns text **and** an image in one turn
   (Gemini's nano-banana / "imagine" family).

## Path 1: dedicated image API

`/v1/images/generations` follows the OpenAI image API shape. Model
families that serve this endpoint:

* OpenAI: `openai/gpt-image-1`, `openai/gpt-image-1-mini`,
  `openai/gpt-image-1.5`
* Google Imagen: `google/imagen-4.0-fast-generate-001`,
  `google/imagen-4.0-generate-001`,
  `google/imagen-4.0-ultra-generate-001`
* xAI: `grok/grok-imagine-image`, `grok/grok-imagine-image-pro`

```bash theme={null}
curl https://api.orcarouter.ai/v1/images/generations \
  -H "Authorization: Bearer sk-orca-..." \
  -H "Content-Type: application/json" \
  -d '{
    "model": "openai/gpt-image-1",
    "prompt": "A cat astronaut on Mars, photorealistic",
    "size": "1024x1024"
  }'
```

### Editing images

`/v1/images/edits` takes an existing image plus a prompt and returns an
edited image. Send it as `multipart/form-data`. Served by OpenAI
`gpt-image-2`.

```bash theme={null}
curl https://api.orcarouter.ai/v1/images/edits \
  -H "Authorization: Bearer sk-orca-..." \
  -F model="openai/gpt-image-2" \
  -F image="@input.png" \
  -F prompt="Make the sky a starry night" \
  -F size="1024x1024"
```

Pass an optional `mask` (a PNG whose transparent region marks the area
to repaint) for inpainting, or repeat `image[]` to combine multiple
reference images:

```bash theme={null}
curl https://api.orcarouter.ai/v1/images/edits \
  -H "Authorization: Bearer sk-orca-..." \
  -F model="openai/gpt-image-2" \
  -F 'image[]=@subject.png' \
  -F 'image[]=@scene.png' \
  -F prompt="Place the subject into the scene"
```

## Path 2: image generation via chat completions

Some Gemini models can return an image as part of a normal chat
completion turn. When you pick one of these models, OrcaRouter
automatically tells the upstream to emit both text and an image in
the response:

* `google/gemini-2.5-flash-image`
* `google/gemini-3-pro-image-preview`
* `google/gemini-3.1-flash-image-preview`

### Example

```python theme={null}
from openai import OpenAI

client = OpenAI(base_url="https://api.orcarouter.ai/v1", api_key="sk-orca-...")

resp = client.chat.completions.create(
    model="google/gemini-2.5-flash-image",
    messages=[{"role": "user", "content": "Draw a watercolour of a foggy harbor at dawn."}],
)

# resp.choices[0].message.content carries text + an image data URL or
# inline_data block, depending on the SDK's serialization. Inspect the
# raw response if your SDK doesn't surface the image directly.
```

These models are not callable via `/v1/images/generations` — use
chat completions for them.

## See also

* [API Reference / Images](/api-reference/images/create-an-image) — full schema with try-it
* [Operations / Billing & Usage](/operations/billing-and-usage)
