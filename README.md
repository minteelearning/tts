# Mintee Mandarin TTS API

A small protected API that turns Mandarin learning text into MP3 using the
Microsoft Edge online speech service via [`edge-tts`](https://github.com/rany2/edge-tts).
It is intentionally a separate conventional Python service: Cloudflare Python Workers
run in Pyodide/WebAssembly and cannot host a normal voice-synthesis library.

## Local setup

```sh
cp .env.example .env
# Edit .env and replace the placeholder with a long random secret.
uv sync
set -a; source .env; set +a
uv run uvicorn src.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```sh
curl http://127.0.0.1:8000/health
curl --fail-with-body \
  -H "Authorization: Bearer $TTS_API_KEY" \
  -H "Content-Type: application/json" \
  --data '{"input":"你好，欢迎来到明德。", "voice":"zh-CN-XiaoxiaoNeural"}' \
  http://127.0.0.1:8000/v1/audio/speech \
  --output test.mp3
```

The four supported voices are `zh-CN-XiaoxiaoNeural` (default),
`zh-CN-XiaoyiNeural`, `zh-CN-YunxiNeural`, and `zh-CN-YunjianNeural`.

## Before connecting Mintee

1. Run the local test and listen to `test.mp3`.
2. Deploy this API to a conventional Python host that provides a persistent HTTPS URL.
   Keep `TTS_API_KEY` as a host secret, never in source control.
3. Confirm the public `/health` route works, then repeat the authenticated MP3 request
   against that HTTPS URL.
4. Give the same secret to the Cloudflare Worker as `TTS_INTERNAL_SECRET`. The Worker
   will later use it server-to-server; browsers will never receive it.
5. Only then add the Worker cache flow: deterministic R2 key -> return existing MP3 ->
   otherwise call this API -> store the returned MP3 in R2 -> return a signed or public URL.

`edge-tts` depends on an online Microsoft Edge speech endpoint. It is excellent for
prototyping and small-scale use, but it is not an SLA-backed commercial TTS contract.
If availability, contractual support, or fixed voice versions become important, the API
shape can remain unchanged while its provider is swapped for Azure Speech or another
commercial TTS provider.
