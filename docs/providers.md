# Provider contracts and comparison limits

Documentation checked November 7, 2026. Adapter implementation and offline tests do not establish that a paid account or a live endpoint currently works. Run a small smoke test before a complete comparison and record its outcome separately.

## Model profiles

| Profile | Segmind slug | fal generation / editing | Google Vertex model |
| --- | --- | --- | --- |
| `nano-banana` | `nano-banana` | `fal-ai/nano-banana` / `fal-ai/nano-banana/edit` | `gemini-2.5-flash-image` |
| `nano-banana-pro` | `nano-banana-pro` | `fal-ai/nano-banana-pro` / `fal-ai/nano-banana-pro/edit` | `gemini-3-pro-image` |
| `nano-banana-2` | `nano-banana-2` | `fal-ai/nano-banana-2` / `fal-ai/nano-banana-2/edit` | `gemini-3.1-flash-image` |
| `nano-banana-2-lite` | `nano-banana-2-lite` | `google/nano-banana-2-lite` / `google/nano-banana-2-lite/edit` | `gemini-3.1-flash-lite-image` |
| `nano-banana-2.1` | `nano-banana-2.1` | `google/nano-banana-2.1` / `google/nano-banana-2.1/edit` | `gemini-nano-banana-2.1` |

All profiles use `1:1`. Pro, 2 and 2.1 explicitly request `1K`; the adapters
translate that choice to `output_resolution`, `resolution`, and
`generationConfig.imageConfig.imageSize` respectively. Lite only supports 1K:
Segmind and Google explicitly receive that size, while fal has no resolution
parameter and receives none. PNG is requested where format control is available.
The original Segmind profile does not assume support for newer fields. Existing
original and Pro profiles retain their settings for reproducibility.

`python3 benchmark.py models` discovers the checked-in profiles without credentials
or network calls. Use `--model <id>` for `plan` and `run`; legacy `--profile <id>`
is equivalent. Choose a single model per run and keep its evidence separate from
other families. Model selection does not change the dataset or safety settings.

Safety settings remain omitted in the baseline. Segmind Pro documents numeric `safety_tolerance`, fal documents a string enum, and Google exposes its own safety controls. Matching numbers across these APIs is not evidence of matching filters. The runner records account mode and actual submitted settings rather than claiming equivalence.

The mappings select the corresponding advertised families. A third-party provider can change the backend behind an alias; its actual revision may not be exposed. Never substitute a preview, newer family, or fallback endpoint without a new profile and clear result label.

## Segmind

Submit once to `POST https://api.segmind.com/v2/{model}` with the `x-api-key` header. Poll the returned status URL and fetch the final response. Preserve the request ID for an unknown or timed-out result. Do not resubmit just because polling timed out.

The model API documents public URLs in `image_urls`. This runner requires a public URL for every Segmind reference and fetches it before inference to verify its SHA-256 matches the local reference. The runner derives each URL from the published checkout commit and the repository-relative asset path. fal and Vertex receive the same local file bytes through their documented inline mechanisms.

The adapter accepts current `images[]` results and older `output` media envelopes. A JSON-encoded `output.data.finish_reason` can carry a Gemini safety or recitation result even under HTTP 200. The classifier recognizes exact known enum values, including the `FinishReason.` prefix, rather than matching words in a message. Failed HTTP 422 polls with `status: FAILED` are followed by a result fetch so full native diagnostics are preserved.

Segmind's async `FAILED` state and HTTP 422 cover multiple failure types. They do not by themselves establish a policy refusal. Public documentation does not specify a stable typed Nano Banana moderation-error schema; ambiguous errors remain unclassified for human review.

Sources: [original API](https://www.segmind.com/models/nano-banana/api), [Pro API](https://www.segmind.com/models/nano-banana-pro/api), [2 API](https://www.segmind.com/models/nano-banana-2/api), [Lite API](https://www.segmind.com/models/nano-banana-2-lite/api), [2.1 API](https://www.segmind.com/models/nano-banana-2.1/api), [async inference](https://docs.segmind.com/docs/serverless-api/async-inference).

## fal

Submit to `https://queue.fal.run/{endpoint}` with `Authorization: Key ...`. Use the generation endpoint for prompt-only cases and the `/edit` endpoint when references are present. `image_urls` accepts data URIs, allowing identical local bytes without a separate hosted input.

The queue's `COMPLETED` state is terminal, not a success assertion. Retrieve the final result. An explicit error type `content_policy_violation` is a policy signal; `no_media_generated` is not enough to identify the cause. Some endpoints may still return older error shapes, which should remain preserved for review.

Sources: [original edit API](https://fal.ai/models/fal-ai/nano-banana/edit/api), [Pro edit API](https://fal.ai/models/fal-ai/nano-banana-pro/edit/api), [2 edit API](https://fal.ai/models/fal-ai/nano-banana-2/edit/api), [Lite schema](https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=google/nano-banana-2-lite/edit), [2.1 edit API](https://fal.ai/models/google/nano-banana-2.1/edit/api), [error taxonomy](https://fal.ai/docs/documentation/model-apis/errors), [queue status](https://fal.ai/docs/api-reference/inference-api/queue/status).

## Google Direct through Vertex AI

Use `POST https://aiplatform.googleapis.com/v1/projects/{project}/locations/global/publishers/google/models/{model}:generateContent` with a Google OAuth bearer token. This is the Google Cloud API, separate from the Gemini Developer API and its API-key authentication.

The request contains the exact prompt and reference bytes in `contents[].parts`, with `responseModalities` set to `TEXT` and `IMAGE`. Preserve `promptFeedback`, candidate finish reasons, safety ratings, response ID, and `modelVersion` when returned. A thought image is not a final generated image.

Explicit safety, blocklist, or prohibited-content reasons are content-policy signals. Recitation is a separate category. `NO_IMAGE`, `IMAGE_OTHER`, `OTHER`, and text-only `STOP` responses need their own labels or manual review. Google's image-safety documentation explains that some model refusals can arrive as text with `STOP`.

Sources: [Pro model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-pro-image), [2 model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-flash-image), [Lite model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/3-1-flash-lite-image), [2.1 model](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/gemini/nano-banana-2-1), [model lifecycle](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions), [response schema](https://docs.cloud.google.com/gemini-enterprise-agent-platform/reference/rest/v1/GenerateContentResponse), [image safety behavior](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/gemini-image-responsible-ai).

## Live evidence still required

Before using a comparative headline, validate the included references, smoke-test each configured adapter, complete the planned runs, and visually review the returned images. Offline tests and credential skips do not establish a provider performance result.

## Reference count limits used by the runner

The maintained suite uses up to three separately submitted images. Limits
below apply to the image-only input path. Requests exceeding a configured
count are recorded as unsupported without submitting inference.

| Profile | Segmind | fal |
| --- | ---: | ---: |
| Nano Banana | 3 ([Segmind schema](https://www.segmind.com/models/nano-banana/api)) | 3 benchmark cap ([fal array schema](https://fal.ai/models/fal-ai/nano-banana/edit/api), [Google guidance](https://ai.google.dev/gemini-api/docs/image-generation#limitations)) |
| Nano Banana Pro | 14 ([Segmind schema](https://www.segmind.com/models/nano-banana-pro/api)) | 14 ([fal model](https://fal.ai/models/fal-ai/nano-banana-pro/edit)) |
| Nano Banana 2 | 14 ([Segmind schema](https://www.segmind.com/models/nano-banana-2/api)) | 14 ([fal model](https://fal.ai/models/fal-ai/nano-banana-2/edit)) |
| Nano Banana 2 Lite | 14 ([Segmind schema](https://www.segmind.com/models/nano-banana-2-lite/api)) | 14 upstream image allowance ([fal array schema](https://fal.ai/api/openapi/queue/openapi.json?endpoint_id=google/nano-banana-2-lite/edit), [Google guidance](https://ai.google.dev/gemini-api/docs/image-generation)) |
| Nano Banana 2.1 | 14 ([Segmind schema](https://www.segmind.com/models/nano-banana-2.1/api)) | 14 ([fal model](https://fal.ai/models/google/nano-banana-2.1/edit)) |

The fal Original and Lite schemas publish an image list without a numeric
maximum. The runner uses Google's Original recommendation and Lite image
allowance. Google describes fidelity capabilities separately from the number
of images the endpoint accepts. The Lite model's object guidance does not
establish character fidelity. The benchmark measures that through visual
review. Live compatibility still depends on the endpoint and account.
