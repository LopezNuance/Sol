# Handoff: Port Qwen3.8 tool-call safeguards to Procyon NVFP4

Date: 2026-09-12

## Objective

Port the Qwen3.8 tool-call fixes from the local W4A16 setup to Procyon, where the NVFP4 quantization of Qwen3.8-27B is running.

The failure being addressed: under sampled generation at long context, Qwen sometimes emits an incomplete Qwen3 XML tool call, especially after sampling `<|endoftext|>` token ID `248044` inside a tool argument. vLLM then treats that as EOS, stops generation mid-argument, and the Qwen3 parser/server conversion can emit an OpenAI tool call with `arguments: "{}"` or malformed/truncated arguments. That poisoned historical `function_call.arguments` can later make Responses requests fail with HTTP 400 when reparsed.

## Recommended skills for next agent

- Use `diagnose` if available. Keep the loop tight: verify live config, patch, restart, replay one known request, then expand.
- Use normal repo discipline: inspect `AGENTS.md`, `git status --short`, and `git log --oneline -5` before changing files.

## Source of truth from local fix

Local repo:

```text
/media/scott/Main/repos/qwen38-27b-rtx3090
```

Committed fix:

```text
62017ed fix qwen tool-call sampling safeguards
```

Files changed by that commit:

```text
single-user/start_qwen.sh
single-user/README.md
patches/qwen3-incomplete-tool-args.patch
```

Live local model config also changed outside git:

```text
/media/scott/raid0/llm_models/Qwen3.8-27B-W4A16-AutoRound-fast/generation_config.json
```

Backup made:

```text
/media/scott/raid0/llm_models/Qwen3.8-27B-W4A16-AutoRound-fast/generation_config.json.codex-backup-20260911T2159Z
```

## What changed locally

1. `SPEC=none` now actually disables speculative decoding.

Previously `SPEC=none` fell through to the default MTP branch and still emitted:

```text
--speculative-config {"method":"mtp",...}
```

The fixed startup script leaves `SPEC_CFG` empty for `SPEC=none` and only appends `--speculative-config` when `SPEC_CFG` is non-empty.

2. Added `SAMPLING=greedy`.

This startup knob passes:

```json
{"temperature":0,"top_p":1,"top_k":0,"eos_token_id":[248046]}
```

through vLLM `--override-generation-config`. It makes omitted-temperature OpenAI/Responses requests default to greedy while preserving per-request overrides. It also prevents token `248044` (`<|endoftext|>`) from being used as a stop/EOS token.

3. Hardened Qwen3 parser.

New patch:

```text
patches/qwen3-incomplete-tool-args.patch
```

It changes the Qwen3 arg converter to return `None` for final extraction when a raw tool argument body contains an unterminated `<parameter=...>` tag. `ParserEngine` then suppresses that incomplete tool call instead of emitting `arguments: "{}"`. Partial streaming deltas still work.

## Procyon porting steps

1. Find Procyon’s active Qwen serving repo and model path.

Inspect the actual live process first:

```bash
pgrep -af 'vllm serve|qwen3.8|Qwen3'
```

Record:

- repo path used to launch
- venv path
- model path
- served model name
- whether `--speculative-config` appears
- whether `--override-generation-config` appears

2. Inspect NVFP4 generation config.

```bash
cat /path/to/Qwen3.8-27B-NVFP4/generation_config.json
```

If it contains `eos_token_id` with both `248046` and `248044`, the same EOS-side fix applies. Back it up before editing:

```bash
cp /path/to/model/generation_config.json /path/to/model/generation_config.json.codex-backup-YYYYMMDDTHHMMZ
```

Target safe defaults:

```json
{
  "do_sample": false,
  "eos_token_id": [248046],
  "temperature": 0.0,
  "top_k": 0,
  "top_p": 1.0
}
```

Keep unrelated model fields as-is. Do not change `pad_token_id` just because it is `248044`; the observed bug is stopping on `248044`, not padding with it.

3. Port repo changes.

Best path if Procyon has the same repo history: fetch/cherry-pick commit `62017ed`.

Fallback: manually copy/apply these changes:

- `single-user/start_qwen.sh`: add real `SPEC=none`, conditional `SPEC_ARGS`, and `SAMPLING=greedy` / `OVERRIDE_GENERATION_CONFIG`.
- `single-user/README.md`: document `SPEC=none` and `SAMPLING=greedy`.
- `patches/qwen3-incomplete-tool-args.patch`: add the parser hardening patch.

Then apply the patch to Procyon’s vLLM install:

```bash
patch -p1 -d venv/lib/python3.12/site-packages/vllm < patches/qwen3-incomplete-tool-args.patch
```

If the vLLM path differs, locate it with:

```bash
venv/bin/python -c "import vllm, pathlib; print(pathlib.Path(vllm.__file__).parent)"
```

4. Restart Procyon with speculative decoding off and greedy defaults.

Use the local equivalent of:

```bash
MODEL=/path/to/Qwen3.8-27B-NVFP4 \
CUDA_DEVICE_ORDER=PCI_BUS_ID \
CUDA_VISIBLE_DEVICES=<gpu> \
SPEC=none \
SAMPLING=greedy \
PREFIX_CACHE=1 \
CTX=long \
bash single-user/start_qwen.sh
```

After boot, verify:

```bash
pgrep -af 'vllm serve|qwen3.8|Qwen3'
```

Expected:

- no `--speculative-config`
- either `--override-generation-config ...` from `SAMPLING=greedy`, or a model `generation_config.json` already edited to greedy defaults

Also check server logs for:

```text
speculative_config=None
```

5. Validate behavior.

Minimal smoke:

```bash
curl -sS -H 'Content-Type: application/json' \
  --data '{"model":"qwen3.8-27b","input":"Call exec_command with cmd exactly: echo TOOL_TEST","tools":[{"type":"function","name":"exec_command","parameters":{"type":"object","properties":{"cmd":{"type":"string"}},"required":["cmd"],"additionalProperties":false}}],"tool_choice":"auto","stream":false}' \
  http://127.0.0.1:<port>/v1/responses | jq -c '[.output[]? | select(.type=="function_call") | {name, arguments}]'
```

Long-context replay if available:

- Use the same known-problem full-context Responses request if it exists on Procyon.
- First replay with omitted temperature. Expect stable greedy output.
- Then explicitly set `"temperature": 1.0` and run 10 times. Expected after parser/EOS fixes: no `arguments:"{}"` and no malformed/truncated tool arguments. Sampled commands may differ.

## Local validation evidence

Local W4A16 validation after fixes:

- Live argv had no `--speculative-config`.
- Engine log showed `speculative_config=None`.
- Saved bad raw generation parsed as `tool_call_count: 0`, not `{}`.
- Saved valid raw generation still parsed as one valid `exec_command`.
- Original full-context omitted-temperature replay: 5/5 identical valid tool calls.
- Explicit `temperature=1.0` replay after fixes: 10/10 valid tool calls, no `{}`, no truncation.
- `bash -n single-user/start_qwen.sh`: pass.
- `git diff --cached --check`: pass before commit.
- `verify.sh --no-server`: all vLLM patches including `qwen3-incomplete-tool-args.patch` detected as applied; only failure was missing repo-local default model directory because local serving used external `/media/scott/raid0/...`.

## Important caveats

- `SPEC=none` disables speculative decoding only. It does not turn off sampling by itself.
- Sampling is controlled by request parameters and server/model generation config. For omitted-temperature OpenAI Responses calls, vLLM defaults to temperature `1.0` unless generation config/override changes it.
- The parser hardening is quantization-independent and should apply to W4A16, NVFP4, or other Qwen3.8 quantizations using the same Qwen3 XML tool-call parser.
- The EOS fix should be applied only after confirming the NVFP4 model config uses `248044` as an EOS stop ID. If its config already has only `248046`, do not invent extra EOS changes.
- Do not use `pkill -f` to stop the server. Resolve PIDs and stop by PID.

## If Procyon differs

If Procyon has a newer vLLM where patch hunks do not apply, locate equivalent functions:

```bash
rg --no-ignore -n '_qwen3_arg_converter|arg_converter|_build_extracted_result' venv/lib/python3.12/site-packages/vllm
```

Preserve the same behavior:

- partial Qwen3 arg conversion may include an in-progress parameter;
- final extraction must reject an unterminated `<parameter=...>` instead of returning `{}`;
- engine extraction must suppress a tool call when the converter returns `None`.
