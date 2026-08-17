#!/usr/bin/env python3
"""扫描中文 Markdown 的可读性风险，不自动修改正文。

用途：为人工审稿提供线索。指标不能单独证明文章好读或难读。
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\s*\n.*?\n---\s*\n", re.S)
CODE_BLOCK = re.compile(r"```.*?```", re.S)
MATH_BLOCK = re.compile(r"\$\$.*?\$\$", re.S)
TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
LIST_LINE = re.compile(r"^\s*(?:[-*+] |\d+[.)] )")
HEADING = re.compile(r"^(#{1,6})\s+(.+)$")
SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?])(?:[”’」』】）)]*)")
CLAUSE_SPLIT = re.compile(r"[，；：、]")
AI_PATTERNS = {
    "不是……而是……": re.compile(r"不是.{0,24}而是"),
    "真正的……是……": re.compile(r"真正的.{0,20}是"),
    "需要注意": re.compile(r"需要注意(?:的是)?"),
    "本质上": re.compile(r"本质上"),
    "这意味着": re.compile(r"这意味着"),
    "换句话说": re.compile(r"换句话说"),
    "因此至少": re.compile(r"因此至少"),
}
ABSTRACT_TERMS = (
    "框架", "维度", "闭环", "抓手", "赋能", "范式", "链路", "底层逻辑", "方法论",
    "体系", "机制", "模型", "结构", "目标", "价值", "体验", "关系", "状态", "反馈",
)


def strip_markup(text: str) -> str:
    text = FRONTMATTER.sub("", text)
    text = CODE_BLOCK.sub("", text)
    text = MATH_BLOCK.sub("", text)
    lines = []
    for line in text.splitlines():
        if HEADING.match(line) or TABLE_LINE.match(line):
            continue
        line = LIST_LINE.sub("", line)
        line = re.sub(r"!\[[^]]*]\([^)]*\)", "", line)
        line = re.sub(r"\[([^]]+)]\([^)]*\)", r"\1", line)
        line = re.sub(r"[`*_>#]", "", line).strip()
        lines.append(line)
    return "\n".join(lines)


def paragraphs(text: str) -> list[str]:
    body = FRONTMATTER.sub("", text)
    body = CODE_BLOCK.sub("", body)
    body = MATH_BLOCK.sub("", body)
    result = []
    for block in re.split(r"\n\s*\n", body):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or any(HEADING.match(line) for line in lines):
            continue
        if all(TABLE_LINE.match(line) or LIST_LINE.match(line) for line in lines):
            continue
        plain = strip_markup("\n".join(lines)).replace("\n", "")
        if plain:
            result.append(plain)
    return result


def sentence_list(plain: str) -> list[str]:
    chunks = SENTENCE_SPLIT.split(plain.replace("\n", ""))
    return [chunk.strip() for chunk in chunks if chunk.strip()]


def analyze(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    plain = strip_markup(raw)
    paras = paragraphs(raw)
    sentences = sentence_list(plain)
    headings = [m.group(2).strip() for line in raw.splitlines() if (m := HEADING.match(line))]
    list_items = sum(1 for line in raw.splitlines() if LIST_LINE.match(line))
    body_lines = [line for line in raw.splitlines() if line.strip() and not HEADING.match(line)]
    prose_chars = sum(1 for ch in plain if not ch.isspace())
    sentence_lengths = [len(re.sub(r"\s", "", s)) for s in sentences]
    long_sentences = [s for s in sentences if len(re.sub(r"\s", "", s)) > 60]
    long_paragraphs = [p for p in paras if len(p) > 220]
    pattern_hits = {name: len(rx.findall(plain)) for name, rx in AI_PATTERNS.items()}
    pattern_hits = {name: count for name, count in pattern_hits.items() if count}
    abstract_counts = Counter({term: plain.count(term) for term in ABSTRACT_TERMS if plain.count(term)})
    top_abstract = abstract_counts.most_common(8)
    starters = Counter()
    for sentence in sentences:
        clean = re.sub(r"^[“‘「『（(\s]+", "", sentence)
        starters[clean[:4]] += 1
    repeated_starters = [(start, count) for start, count in starters.most_common() if start and count >= 3][:8]
    examples = len(re.findall(r"例如|举例|案例|以《|假设", plain))
    questions = len(re.findall(r"[？?]", plain))
    formulas = len(re.findall(r"\$\$|\$[^$]+\$", raw))
    tables = sum(1 for line in raw.splitlines() if TABLE_LINE.match(line))
    return {
        "file": path.as_posix(),
        "chars": prose_chars,
        "headings": len(headings),
        "paragraphs": len(paras),
        "sentences": len(sentences),
        "avg_sentence_chars": round(sum(sentence_lengths) / len(sentence_lengths), 1) if sentence_lengths else 0,
        "max_sentence_chars": max(sentence_lengths, default=0),
        "long_sentences_over_60": len(long_sentences),
        "long_sentence_samples": long_sentences[:3],
        "long_paragraphs_over_220": len(long_paragraphs),
        "list_items": list_items,
        "list_ratio_per_body_line": round(list_items / len(body_lines), 2) if body_lines else 0,
        "table_lines": tables,
        "formula_markers": formulas,
        "example_markers": examples,
        "question_marks": questions,
        "template_phrases": pattern_hits,
        "top_abstract_terms": top_abstract,
        "repeated_sentence_starters": repeated_starters,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+", help="Markdown 文件或目录")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    files: list[Path] = []
    for value in args.paths:
        path = Path(value)
        files.extend(sorted(path.rglob("*.md")) if path.is_dir() else [path])
    results = [analyze(path) for path in files if path.exists()]
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return
    for item in results:
        print(f"\n{item['file']}")
        print(
            f"  正文 {item['chars']} 字；平均句长 {item['avg_sentence_chars']}；"
            f"长句 {item['long_sentences_over_60']}；长段 {item['long_paragraphs_over_220']}；"
            f"列表项 {item['list_items']}；示例标记 {item['example_markers']}"
        )
        if item["template_phrases"]:
            print(f"  模板句：{item['template_phrases']}")
        if item["repeated_sentence_starters"]:
            print(f"  重复句首：{item['repeated_sentence_starters']}")


if __name__ == "__main__":
    main()
