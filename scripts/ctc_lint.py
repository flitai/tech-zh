#!/usr/bin/env python3
"""对中文技术文本做确定性的机械初筛。

本脚本只提示可复核位置。它不理解技术语义，也不证明文本合规。

用法：
    python3 ctc_lint.py FILE [FILE ...]
    cat FILE | python3 ctc_lint.py --json
    python3 ctc_lint.py --strict FILE
    python3 ctc_lint.py --max-chars 50 FILE
    python3 ctc_lint.py --selftest

默认模式的所有发现均为 advisory。--strict 会把分号、注释中的命令、
列表项悬空连接词和超长句提升为 hard。hard 数超过 --baseline 时退出 1。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


FENCE_RE = re.compile(r"^\s*(```|~~~)")
INLINE_CODE_RE = re.compile(r"`[^`]*`")
MARKDOWN_LINK_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+")
LIST_RE = re.compile(r"^(?P<indent>\s{0,3})(?P<marker>[-*+]|\d+[.)])\s+(?P<body>.*)$")
SENTENCE_RE = re.compile(r"[^。！？!?\n]+[。！？!?]?")

ADVISORY_PATTERNS = (
    (
        "ambiguous-reference",
        re.compile(
            r"(?:其(?!(?:他|中|次|实|余|一|前|后))|"
            r"此(?!(?:外|时|处|前|后))|上述|前者|后者|相关|"
            r"(?<!应)(?<!不)该)(?=[\u4e00-\u9fff])"
        ),
        "可能存在不明确指代。确认先行词唯一，否则重复对象名称。",
    ),
    (
        "vague-qualifier",
        re.compile(r"(及时|尽快|适当|酌情|若干|有关|必要时|一般情况下|原则上|视情况|较高|较低|较快|较慢|相关人员|相关信息)"),
        "该表达通常不能直接执行或验收。给出条件、角色、阈值或时限。",
    ),
    (
        "nominalized-action",
        re.compile(r"(进行|开展|实施|予以|实现对).{0,12}(分析|检查|测试|验证|确认|记录|配置|处理|评估|更新|监控|管理)"),
        "可能使用了动作壳。确认能否改成直接动词。",
    ),
    (
        "possible-passive",
        re.compile(r"(被|由).{1,18}(执行|完成|处理|分析|检查|测试|验证|记录|配置|更新|删除|创建|发送|接收)"),
        "可能使用了隐藏责任主体的被动结构。确认是否需要写明执行者。",
    ),
)

COMMAND_RE = re.compile(r"(请|必须|应当|应|不得|严禁|务必|确保|检查|设置|安装|删除|提交|关闭|断开|启动|停止|执行)")
SAFETY_LABEL_RE = re.compile(r"^\s*(警告|危险|注意|小心)\s*[：:]")
CONSEQUENCE_RE = re.compile(r"(导致|造成|可能|风险|伤害|死亡|损坏|失效|故障|触电|灼伤|爆炸|火灾|腐蚀)")
DANGLING_RE = re.compile(r"(?:并|或|以及|且|并且)\s*[，,。.]?\s*$")


def visible_text(text: str) -> str:
    text = INLINE_CODE_RE.sub("", text)
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = HEADING_RE.sub("", text)
    return text


def effective_length(text: str) -> int:
    text = visible_text(text)
    return len(re.sub(r"[\s\-—_*#>|，。；：！？、,.；:!?()（）\[\]【】{}]", "", text))


def finding(filename, line, col, rule, level, match, message):
    return {
        "file": filename,
        "line": line,
        "col": col,
        "rule": rule,
        "level": level,
        "match": match,
        "message": message,
    }


def lint(text: str, filename: str = "<stdin>", *, strict: bool = False,
         max_chars: int | None = None):
    threshold = max_chars if max_chars is not None else (45 if strict else 60)
    findings = []
    in_fence = False

    for lineno, raw in enumerate(text.splitlines(), 1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        line = visible_text(raw)
        if not line.strip():
            continue

        for rule, pattern, message in ADVISORY_PATTERNS:
            for match in pattern.finditer(line):
                findings.append(finding(
                    filename, lineno, match.start() + 1, rule,
                    "advisory", match.group(0), message
                ))

        for match in re.finditer(r"[；;]", line):
            findings.append(finding(
                filename, lineno, match.start() + 1, "semicolon",
                "hard" if strict else "advisory", match.group(0),
                "分号可能连接了应拆分的动作或判断。严格文本应改用句号或列表。",
            ))

        if re.match(r"^\s*注\s*[：:]", line) and COMMAND_RE.search(line):
            match = COMMAND_RE.search(line)
            findings.append(finding(
                filename, lineno, match.start() + 1, "command-in-note",
                "hard" if strict else "advisory", match.group(0),
                "注释中可能包含必做动作、禁止事项或要求。将其移到正式步骤。",
            ))

        if SAFETY_LABEL_RE.match(line) and not CONSEQUENCE_RE.search(line):
            findings.append(finding(
                filename, lineno, 1, "safety-without-consequence", "advisory",
                line.strip(), "安全说明可能没有写明危险源或可能后果。",
            ))

        list_match = LIST_RE.match(raw)
        if list_match:
            body = visible_text(list_match.group("body"))
            dangling = DANGLING_RE.search(body)
            if dangling:
                findings.append(finding(
                    filename, lineno, raw.find(list_match.group("marker")) + 1,
                    "dangling-conjunction", "hard" if strict else "advisory",
                    dangling.group(0).strip(), "列表项以连接词结束。补全该项或重写列表关系。",
                ))

        search_from = 0
        for sentence in SENTENCE_RE.finditer(line):
            content = sentence.group(0).strip()
            if not content:
                continue
            length = effective_length(content)
            if length > threshold:
                col = line.find(content, search_from) + 1
                search_from = max(col, 0) + len(content)
                findings.append(finding(
                    filename, lineno, max(col, 1), "long-sentence",
                    "hard" if strict else "advisory", f"{length} 个有效字符",
                    f"句子超过 {threshold} 个有效字符。复核是否包含多个动作、条件或判断。",
                ))

    findings.sort(key=lambda item: (item["line"], item["col"], item["rule"]))
    return findings


def run_selftest():
    bad = (
        "注：提交前必须删除临时文件。\n"
        "系统应及时进行相关信息的处理；然后由管理员执行验证。\n"
        "警告：小心操作。\n"
        "- 检查配置并\n"
    )
    findings = lint(bad, strict=True)
    rules = {item["rule"] for item in findings}
    expected = {
        "command-in-note", "vague-qualifier", "nominalized-action",
        "semicolon", "possible-passive", "safety-without-consequence",
        "dangling-conjunction",
    }
    assert expected <= rules, (expected - rules, findings)
    assert all(
        item["level"] == "hard"
        for item in findings
        if item["rule"] in {"command-in-note", "semicolon", "dangling-conjunction"}
    )
    assert not lint("```text\n注：必须删除。\n```", strict=True)
    assert not lint("网络中断可能导致任务失败。", strict=True)
    ordinary = lint("系统应该记录其他输入。此外，系统记录本次输出。")
    assert not any(item["rule"] == "ambiguous-reference" for item in ordinary)
    long_text = "系统" + "持续记录目标状态" * 10 + "。"
    assert any(
        item["rule"] == "long-sentence"
        for item in lint(long_text, strict=True)
    )
    print("selftest OK")


def read_inputs(paths):
    if not paths:
        return [("<stdin>", sys.stdin.read())]
    return [
        (path, Path(path).read_text(encoding="utf-8"))
        for path in paths
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--max-chars", type=int)
    parser.add_argument("--baseline", type=int, default=0)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        run_selftest()
        return 0

    all_findings = []
    for filename, text in read_inputs(args.paths):
        all_findings.extend(lint(
            text, filename, strict=args.strict, max_chars=args.max_chars
        ))

    hard_count = sum(item["level"] == "hard" for item in all_findings)
    if args.json:
        print(json.dumps({
            "findings": all_findings,
            "count": len(all_findings),
            "hard_count": hard_count,
            "baseline": args.baseline,
        }, ensure_ascii=False, indent=2))
    else:
        for item in all_findings:
            print(
                f"{item['file']}:{item['line']}:{item['col']} "
                f"{item['level']} {item['rule']}: {item['message']} "
                f"[{item['match']}]"
            )
        print(
            f"\n共 {len(all_findings)} 项，其中 hard {hard_count} 项；"
            f"baseline {args.baseline}。"
        )
        print("结果只用于机械初筛，不能证明语义正确或符合任何正式标准。")

    return 1 if hard_count > args.baseline else 0


if __name__ == "__main__":
    raise SystemExit(main())
