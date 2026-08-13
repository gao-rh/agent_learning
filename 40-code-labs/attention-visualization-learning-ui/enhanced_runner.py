"""Render the official attention heatmap plus a low-weight detail view.

This runner reuses the book experiment's model/input/matrix extraction and its
official heatmap renderer. The second image changes only the color
normalization (PowerNorm); it does not change any attention value.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.colors import PowerNorm


LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[1]
EXPERIMENT_DIR = (
    REPO_ROOT
    / "学习资料/Agent/参考资料/深入理解AI-Agent/ai-agent-book-chapter2-current"
    / "chapter2/attention_visualization"
)
sys.path.insert(0, str(EXPERIMENT_DIR))

from agent import AttentionVisualizationAgent  # noqa: E402
from attention_cli import build_input_ids, extract_layer_matrix  # noqa: E402
from visualization import (  # noqa: E402
    attention_sink_stats,
    clean_token_labels,
    create_layer_attention_heatmap,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--prompt", required=True)
    result.add_argument("--layer", type=int, default=-1)
    result.add_argument("--head", type=int, default=-1)
    result.add_argument("--max-new-tokens", type=int, default=0)
    result.add_argument("--no-chat-template", action="store_true")
    result.add_argument("--cmap", default="magma")
    result.add_argument("--original-output", type=Path, required=True)
    result.add_argument("--detail-output", type=Path, required=True)
    return result


def render_detail(
    matrix: np.ndarray,
    tokens: list[str],
    output: Path,
    title: str,
    cmap: str,
    context_boundary: int | None,
) -> None:
    seq_len = matrix.shape[0]
    masked = np.ma.array(
        matrix,
        mask=np.triu(np.ones_like(matrix, dtype=bool), k=1),
    )
    width = max(12.0, min(22.0, seq_len * 0.18))
    height = max(10.0, min(20.0, seq_len * 0.15))
    fig, ax = plt.subplots(figsize=(width, height))
    cmap_obj = plt.get_cmap(cmap).copy()
    cmap_obj.set_bad(color="#f0f0f0")
    maximum = max(float(np.max(matrix)), 1e-8)
    image = ax.imshow(
        masked,
        cmap=cmap_obj,
        aspect="auto",
        norm=PowerNorm(gamma=0.22, vmin=0.0, vmax=maximum),
    )

    labels = clean_token_labels(tokens)
    step = max(1, int(np.ceil(seq_len / 100)))
    ticks = np.arange(0, seq_len, step)
    tick_labels = [labels[index] for index in ticks]
    ax.set_xticks(ticks)
    ax.set_xticklabels(tick_labels, rotation=90, fontsize=7)
    ax.set_yticks(ticks)
    ax.set_yticklabels(tick_labels, fontsize=7)

    if context_boundary is not None and 0 < context_boundary < seq_len:
        ax.axvline(context_boundary - 0.5, color="#ff3b30", linewidth=1.4, linestyle="--")
        ax.axhline(context_boundary - 0.5, color="#ff3b30", linewidth=1.4, linestyle="--")

    colorbar = plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    colorbar.set_label("Attention weight · power-scaled color (γ=0.22)", rotation=270, labelpad=18)
    ax.set_xlabel("Key position · 被看的 token", fontsize=12, fontweight="bold")
    ax.set_ylabel("Query position · 正在看的 token", fontsize=12, fontweight="bold")
    ax.set_title(
        f"{title}\n低权重细节增强（仅改变颜色映射，不改变 attention 数值）",
        fontsize=13,
        fontweight="bold",
    )
    plt.tight_layout()
    plt.savefig(output, dpi=170, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    args = parser().parse_args()
    agent = AttentionVisualizationAgent(
        model_name="Qwen/Qwen3-0.6B",
        attention_layer_index=args.layer,
        verbose=True,
    )
    inputs = build_input_ids(agent, args.prompt, not args.no_chat_template)
    context_length = inputs["input_ids"].shape[1]
    if args.max_new_tokens > 0:
        with torch.no_grad():
            generated = agent.model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                pad_token_id=agent.tokenizer.pad_token_id,
            )
        full_ids = generated[0].unsqueeze(0)
    else:
        full_ids = inputs["input_ids"]

    token_ids = full_ids[0].tolist()
    tokens = [
        agent.tokenizer.decode([token_id], skip_special_tokens=False)
        for token_id in token_ids
    ]
    with torch.no_grad():
        outputs = agent.model(
            input_ids=full_ids,
            output_attentions=True,
            return_dict=True,
        )
    if not outputs.attentions:
        raise RuntimeError("模型没有返回 attention weights")

    matrix = extract_layer_matrix(outputs.attentions, args.layer, args.head)
    head_label = "avg heads" if args.head < 0 else f"head {args.head}"
    title = f"Layer {args.layer} ({head_label}) - '{args.prompt[:40]}'"
    boundary = context_length if args.max_new_tokens > 0 else None

    original = create_layer_attention_heatmap(
        matrix,
        tokens,
        title=title,
        save_path=str(args.original_output),
        cmap=args.cmap,
        context_boundary=boundary,
    )
    plt.close(original)
    render_detail(
        matrix,
        tokens,
        args.detail_output,
        title,
        args.cmap,
        boundary,
    )
    stats = attention_sink_stats(matrix)
    print(f"Sequence length: {len(tokens)} tokens")
    print(f"Attention sink mean: {stats['mean_sink_share'] * 100:.1f}%")
    print(f"Saved original: {args.original_output}")
    print(f"Saved detail: {args.detail_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
