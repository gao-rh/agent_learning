"""A thin learning UI for the book's attention_cli.py experiment.

The page does not change the experiment. It asks for a prediction, builds the
equivalent CLI command, runs the upstream script, and displays its PNG output.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field


LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[1]
EXPERIMENT_DIR = (
    REPO_ROOT
    / "学习资料/Agent/参考资料/深入理解AI-Agent/ai-agent-book-chapter2-current"
    / "chapter2/attention_visualization"
)
CLI_PATH = EXPERIMENT_DIR / "attention_cli.py"
ENHANCED_RUNNER = LAB_DIR / "enhanced_runner.py"
OUTPUT_DIR = LAB_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Attention Visualization 学习操作台")
app.mount("/outputs", StaticFiles(directory=OUTPUT_DIR), name="outputs")
run_lock = threading.Lock()


class RenderRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)
    prediction: str = Field(min_length=1, max_length=2000)
    layer: int = Field(default=-1, ge=-28, le=27)
    head: int = Field(default=-1, ge=-1, le=15)
    max_new_tokens: int = Field(default=0, ge=0, le=80)
    no_chat_template: bool = False
    cmap: Literal["viridis", "magma", "plasma", "cividis", "turbo"] = "magma"


def build_command(request: RenderRequest, output_path: Path) -> list[str]:
    command = [
        sys.executable,
        str(CLI_PATH),
        "--prompt",
        request.prompt,
        "--layer",
        str(request.layer),
        "--head",
        str(request.head),
        "--max-new-tokens",
        str(request.max_new_tokens),
        "--output",
        str(output_path),
        "--cmap",
        request.cmap,
    ]
    if request.no_chat_template:
        command.append("--no-chat-template")
    return command


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return PAGE


@app.get("/api/health")
def health() -> dict[str, object]:
    return {
        "ok": CLI_PATH.is_file(),
        "experiment": str(CLI_PATH),
        "output_directory": str(OUTPUT_DIR),
    }


@app.post("/api/render")
def render_attention(request: RenderRequest) -> dict[str, str]:
    if not CLI_PATH.is_file():
        raise HTTPException(status_code=500, detail=f"找不到教材脚本：{CLI_PATH}")

    run_id = uuid.uuid4().hex[:10]
    output_name = f"attention-{run_id}-original.png"
    detail_name = f"attention-{run_id}-detail.png"
    output_path = OUTPUT_DIR / output_name
    detail_path = OUTPUT_DIR / detail_name
    command = build_command(request, output_path)
    runner_command = [
        sys.executable,
        str(ENHANCED_RUNNER),
        "--prompt",
        request.prompt,
        "--layer",
        str(request.layer),
        "--head",
        str(request.head),
        "--max-new-tokens",
        str(request.max_new_tokens),
        "--cmap",
        request.cmap,
        "--original-output",
        str(output_path),
        "--detail-output",
        str(detail_path),
    ]
    if request.no_chat_template:
        runner_command.append("--no-chat-template")

    if not run_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="已有一次实验正在运行，请稍后再试。")
    try:
        result = subprocess.run(
            runner_command,
            cwd=EXPERIMENT_DIR,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=504, detail="实验运行超过 10 分钟，已停止。") from exc
    finally:
        run_lock.release()

    command_text = shlex.join(command).replace(str(sys.executable), "python", 1)
    log = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
    if result.returncode != 0 or not output_path.is_file() or not detail_path.is_file():
        raise HTTPException(
            status_code=500,
            detail={"message": "实验运行失败", "command": command_text, "log": log},
        )

    return {
        "image_url": f"/outputs/{output_name}",
        "detail_image_url": f"/outputs/{detail_name}",
        "command": command_text,
        "log": log,
        "prediction": request.prediction,
    }


PAGE = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Attention Visualization 学习操作台</title>
  <style>
    :root { color-scheme: light; --ink:#172033; --muted:#647089; --line:#dce2ec; --blue:#315efb; --paper:#fff; --bg:#f5f7fb; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--bg); }
    main { width:min(1180px,calc(100% - 32px)); margin:32px auto 64px; }
    header { margin-bottom:22px; }
    h1 { font-size:clamp(26px,4vw,42px); margin:0 0 8px; letter-spacing:-.03em; }
    h2 { margin:0 0 14px; font-size:18px; }
    p { color:var(--muted); line-height:1.65; margin:0; }
    .badge { display:inline-block; color:#2148cd; background:#e9efff; border-radius:999px; padding:5px 10px; font-size:13px; margin-bottom:12px; }
    .grid { display:grid; grid-template-columns:minmax(300px,390px) minmax(0,1fr); gap:20px; align-items:start; }
    .card { background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:20px; box-shadow:0 8px 30px rgba(32,45,75,.06); }
    label { display:block; font-weight:650; font-size:14px; margin:15px 0 7px; }
    input,textarea,select { width:100%; border:1px solid #cbd3e1; border-radius:10px; padding:11px 12px; font:inherit; color:inherit; background:#fff; }
    textarea { min-height:78px; resize:vertical; }
    input:focus,textarea:focus,select:focus { outline:3px solid rgba(49,94,251,.14); border-color:var(--blue); }
    .three { display:grid; grid-template-columns:repeat(3,1fr); gap:10px; }
    .check { display:flex; align-items:center; gap:9px; font-weight:500; }
    .check input { width:auto; }
    button { width:100%; border:0; border-radius:11px; padding:12px 16px; margin-top:18px; color:#fff; background:var(--blue); font:700 15px inherit; cursor:pointer; }
    button:disabled { opacity:.6; cursor:wait; }
    .tip { margin-top:12px; font-size:13px; }
    .stage { min-height:520px; padding:0; overflow:hidden; }
    .empty { margin:auto; padding:40px 20px; }
    .viewer { display:none; width:100%; }
    .axis-guide { display:grid; grid-template-columns:auto 1fr; gap:12px; align-items:center; padding:14px 16px; background:#eef3ff; border-bottom:1px solid var(--line); text-align:left; }
    .axis-guide strong { color:#2449c5; }
    .axis-y { writing-mode:vertical-rl; transform:rotate(180deg); font-size:13px; padding:12px 0; }
    .image-scroll { display:grid; grid-template-columns:34px minmax(0,1fr); max-height:720px; overflow:auto; background:#fff; }
    .image-scroll a { display:block; width:max-content; min-width:100%; }
    .stage img { width:1200px; max-width:none; height:auto; border-radius:0; display:block; }
    .view-tabs { display:flex; gap:8px; padding:12px 16px 0; }
    .view-tabs button { width:auto; margin:0; padding:8px 12px; color:#2449c5; background:#edf2ff; font-size:13px; }
    .view-tabs button.active { color:#fff; background:#315efb; }
    .view-note { padding:10px 16px; text-align:left; font-size:13px; color:var(--muted); border-bottom:1px solid var(--line); }
    .viewer-tools { display:flex; flex-wrap:wrap; align-items:center; gap:12px; padding:10px 16px; border-top:1px solid var(--line); text-align:left; font-size:13px; color:var(--muted); }
    .viewer-tools input { width:150px; padding:0; }
    .viewer-tools a { color:#2449c5; font-weight:650; }
    .empty { max-width:430px; }
    .empty strong { display:block; margin-bottom:8px; }
    .result { display:none; margin-top:20px; }
    pre { white-space:pre-wrap; overflow-wrap:anywhere; background:#111827; color:#dbe6ff; border-radius:10px; padding:13px; font-size:12px; line-height:1.5; }
    details { margin-top:12px; }
    .error { display:none; color:#a11b1b; background:#fff0f0; border:1px solid #ffc9c9; padding:12px; border-radius:10px; margin-top:14px; white-space:pre-wrap; }
    @media (max-width:800px) { .grid { grid-template-columns:1fr; } .stage { min-height:320px; } }
  </style>
</head>
<body>
<main>
  <header>
    <span class="badge">实验 2-2 · 公共操作界面</span>
    <h1>Attention Visualization</h1>
    <p>先预测，再运行，再描述。这个页面只包装教材命令，不改变实验内容。</p>
  </header>
  <div class="grid">
    <form class="card" id="form">
      <h2>1. 写下预测</h2>
      <label for="prediction">运行前，你预计哪里最亮？为什么？</label>
      <textarea id="prediction" required placeholder="例如：我猜……，因为……"></textarea>
      <h2 style="margin-top:24px">2. 设置并运行</h2>
      <label for="prompt">Prompt</label>
      <textarea id="prompt" required>北京 的 天气 怎么样</textarea>
      <div class="three">
        <div><label for="layer">Layer</label><input id="layer" type="number" value="-1" min="-28" max="27"></div>
        <div><label for="head">Head</label><input id="head" type="number" value="-1" min="-1" max="15"></div>
        <div><label for="tokens">续写数</label><input id="tokens" type="number" value="0" min="0" max="80"></div>
      </div>
      <label for="cmap">颜色方案</label>
      <select id="cmap">
        <option value="magma" selected>高对比 · magma</option>
        <option value="plasma">高对比 · plasma</option>
        <option value="turbo">鲜明 · turbo</option>
        <option value="viridis">教材默认 · viridis</option>
        <option value="cividis">色觉友好 · cividis</option>
      </select>
      <label class="check"><input id="raw" type="checkbox">不使用 Chat Template</label>
      <button id="run" type="submit">运行当前步骤</button>
      <p class="tip">首次或重新加载模型可能需要一些时间。一次只运行一个实验。</p>
      <div class="error" id="error"></div>
    </form>
    <section>
      <div class="card stage">
        <div class="empty" id="empty"><strong>结果会显示在这里</strong><p>当前第一步保持默认参数：Layer -1、Head -1、续写数 0。</p></div>
        <div class="viewer" id="viewer">
          <div class="axis-guide"><strong>读图方向</strong><span>纵轴 Query ＝ <b>谁在看</b>　→　横轴 Key ＝ <b>它在看谁</b></span></div>
          <div class="view-tabs">
            <button type="button" id="detailTab" class="active">低权重细节图</button>
            <button type="button" id="originalTab">教材原始权重图</button>
          </div>
          <div class="view-note" id="viewNote">细节图使用非线性颜色映射，让小权重差异可见；attention 数值没有改变。</div>
          <div class="image-scroll">
            <div class="axis-y">纵轴 Query · 谁在看</div>
            <a id="imageLink" target="_blank" title="点击打开原始大图"><img id="image" alt="Attention heatmap"></a>
          </div>
          <div class="viewer-tools">
            <label for="zoom" style="margin:0">图片宽度</label>
            <input id="zoom" type="range" min="700" max="1800" step="100" value="1200">
            <span id="zoomValue">1200 px</span>
            <a id="fullImage" target="_blank">打开原始大图 ↗</a>
          </div>
        </div>
      </div>
      <div class="card result" id="result">
        <h2>3. 先描述，再解释</h2>
        <p>请先观察横轴、纵轴、最亮区域，以及结果是否符合你的预测。把你的描述发给 Codex，再一起解释机制。</p>
        <label>本次等价命令</label><pre id="command"></pre>
        <details><summary>查看原始运行日志</summary><pre id="log"></pre></details>
      </div>
    </section>
  </div>
</main>
<script>
const form = document.querySelector('#form');
const run = document.querySelector('#run');
const error = document.querySelector('#error');
form.addEventListener('submit', async (event) => {
  event.preventDefault(); error.style.display = 'none'; run.disabled = true; run.textContent = '正在运行模型…';
  const payload = {
    prediction: document.querySelector('#prediction').value.trim(),
    prompt: document.querySelector('#prompt').value.trim(),
    layer: Number(document.querySelector('#layer').value),
    head: Number(document.querySelector('#head').value),
    max_new_tokens: Number(document.querySelector('#tokens').value),
    no_chat_template: document.querySelector('#raw').checked,
    cmap: document.querySelector('#cmap').value
  };
  try {
    const response = await fetch('/api/render', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail, null, 2));
    window.attentionViews = {original:data.image_url, detail:data.detail_image_url};
    showView('detail');
    document.querySelector('#empty').style.display = 'none';
    document.querySelector('#viewer').style.display = 'block';
    document.querySelector('#command').textContent = data.command;
    document.querySelector('#log').textContent = data.log;
    document.querySelector('#result').style.display = 'block';
  } catch (err) { error.textContent = err.message; error.style.display = 'block'; }
  finally { run.disabled = false; run.textContent = '运行当前步骤'; }
});
const zoom = document.querySelector('#zoom');
zoom.addEventListener('input', () => {
  document.querySelector('#image').style.width = zoom.value + 'px';
  document.querySelector('#zoomValue').textContent = zoom.value + ' px';
});
function showView(kind) {
  if (!window.attentionViews) return;
  const url = window.attentionViews[kind];
  document.querySelector('#image').src = url + '?t=' + Date.now();
  document.querySelector('#imageLink').href = url;
  document.querySelector('#fullImage').href = url;
  document.querySelector('#detailTab').classList.toggle('active', kind === 'detail');
  document.querySelector('#originalTab').classList.toggle('active', kind === 'original');
  document.querySelector('#viewNote').textContent = kind === 'detail'
    ? '细节图使用非线性颜色映射，让小权重差异可见；attention 数值没有改变。'
    : '教材原始图使用线性颜色映射，适合确认绝对权重、attention sink 和 causal triangle。';
}
document.querySelector('#detailTab').addEventListener('click', () => showView('detail'));
document.querySelector('#originalTab').addEventListener('click', () => showView('original'));
</script>
</body>
</html>"""


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
