> ## Documentation Index
> Fetch the complete documentation index at: https://docs.orcarouter.ai/llms.txt
> Use this file to discover all available pages before exploring further.

# MiniMax Video (H3)

> Async video generation via /v1/video/generations — text-to-video, image-to-video, and multimodal reference (image/video/audio) on MiniMax-H3, with native stereo audio.

OrcaRouter speaks MiniMax-H3 on the same submit-and-poll endpoint as Kling
and Seedance. You send `model: minimax/minimax-h3`, OrcaRouter routes the
request to the upstream MiniMax `/v2/video_generation` API, and you poll
the same task ID back through OrcaRouter once it's done (typically 1 to 5
minutes depending on duration and resolution).

<Note>
  The submit endpoint `POST /v1/video/generations` and the fetch endpoint
  `GET /v1/video/generations/{task_id}` are shared with
  [Kling](/kling-video/overview) and [Seedance](/seedance-video/overview).
  What changes is the request body: MiniMax-H3 uses `prompt + duration +
    size + metadata.{ratio, first_frame_image, last_frame_image, video_urls,
    audio_urls, ...}`. The prefix on `model` selects which schema is honored.
</Note>

## Model

| Model                | T2V | I2V (first) | I2V (first+last) | Reference video¹ | Reference audio¹ | Native audio² | Duration            | Resolution |
| -------------------- | :-: | :---------: | :--------------: | :--------------: | :--------------: | :-----------: | ------------------- | ---------- |
| `minimax/minimax-h3` |  ✓  |      ✓      |         ✓        |   up to 3 clips  |   up to 3 clips  |   always on   | 4 – 15 s (integers) | 768P, 2K   |

¹ Reference clips guide the generation. Up to 3 video clips and 3 audio
clips, each kind totalling 15 seconds or less; up to 9 reference images
(plus one first frame and one last frame).

² H3 generates stereo audio natively alongside the visuals — there is no
toggle; every video ships with sound.

## Submit a task

```bash theme={null}
curl https://api.orcarouter.ai/v1/video/generations \
  -H "Authorization: Bearer $ORCAROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "minimax/minimax-h3",
    "prompt": "An orca surfacing in calm water at sunrise, cinematic",
    "duration": 6,
    "size": "768P"
  }'
```

Response:

```json theme={null}
{ "id": "task_xxxx", "status": "queued", "model": "minimax/minimax-h3" }
```

### Body fields

| Field                        | Type           | Notes                                                                                                                                           |
| ---------------------------- | -------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `model`                      | string         | Required. `minimax/minimax-h3`.                                                                                                                 |
| `prompt`                     | string         | Required, up to 7000 characters.                                                                                                                |
| `duration`                   | integer        | 4 – 15 (integers only). Also accepted as the OpenAI-style string field `seconds`. Defaults to 6.                                                |
| `size`                       | string         | `768P` (default) or `2K`. WxH forms whose height is 768 / 1440 / 2048 normalize; anything else is rejected.                                     |
| `image` / `images`           | string / array | Reference image URL(s) — public URL or base64 data URI. Up to 9.                                                                                |
| `metadata.first_frame_image` | string         | Pin the first frame to this image.                                                                                                              |
| `metadata.last_frame_image`  | string         | Pin the last frame to this image.                                                                                                               |
| `metadata.video_urls`        | array          | Up to 3 reference video clips (MP4/MOV, total ≤ 15 s). Singular `metadata.video_url` also accepted.                                             |
| `metadata.audio_urls`        | array          | Up to 3 reference audio clips (WAV/MP3, total ≤ 15 s). Singular `metadata.audio_url` also accepted.                                             |
| `metadata.ratio`             | string         | `16:9`, `4:3`, `1:1`, `3:4`, `9:16`, `21:9`. Text-only requests default to `16:9`; requests with visual inputs adapt to the input when omitted. |
| `metadata.callback_url`      | string         | Optional webhook for status changes.                                                                                                            |

Invalid inputs (unsupported size, duration outside 4–15, malformed
`seconds`, blank reference entries, more than 3 clips per kind) are
rejected with a `400` before anything is billed or sent upstream.

## Poll for results

```bash theme={null}
curl https://api.orcarouter.ai/v1/video/generations/task_xxxx \
  -H "Authorization: Bearer $ORCAROUTER_API_KEY"
```

Response shape is wrapped (same as Kling / Seedance):

```json theme={null}
{
  "code": "success",
  "message": "",
  "data": {
    "task_id": "task_xxxx",
    "status": "SUCCESS",
    "progress": "100%",
    "result_url": "https://video-product.cdn.minimax.io/.../output.mp4"
  }
}
```

Prefer the OpenAI shape? The symmetric aliases `POST /v1/videos` +
`GET /v1/videos/{task_id}` accept the same body and return the OpenAI
video object instead — `status` moves `queued → in_progress → completed`,
and the completed object carries `seconds` and the download URL in
`metadata.url`.

## Billing

H3 bills **per second of generated video**, scaled by resolution — a 2K
second costs more than a 768P second. Reference inputs are metered on
top: a reference video adds its own duration at the output-resolution
rate, images beyond the first five add a flat per-image fee, and
reference audio is free. OrcaRouter pre-holds the declared duration
(plus a cap-sized hold when a reference video is present) and settles to
the upstream-reported usage when the task completes — over-holds are
refunded, and failed tasks are refunded in full. Live rates are on the
[model page](https://www.orcarouter.ai/models/minimax/minimax-h3).

## See also

* [Kling Video](/kling-video/overview) — same endpoint, Kling body shape
* [Seedance Video](/seedance-video/overview) — same endpoint, Seedance body shape
* [Models catalog](/getting-started/models) — the live model list
