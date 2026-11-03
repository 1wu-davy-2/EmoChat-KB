# -*- coding: utf-8 -*-
"""EmoChat-KB 便携检索（零依赖，预构建 BM25 索引）。

用法:
    python emochat_search.py "查询词"
    python emochat_search.py "查询词" --top 5
    python emochat_search.py "查询词" --tag 话术示例
    python emochat_search.py "查询词" --board 06
    python emochat_search.py "查询词" --json
    python emochat_search.py "查询词" --kb /path/to/EmoChat-KB

知识库路径优先级: --kb > EMOCHAT_KB 环境变量 > 技能根目录 .emochat-kb
文件 > 从脚本位置向上查找包含 索引/metadata.json 的目录。
"""
import argparse
import json
import sys
import time
from pathlib import Path

import emochat_core as core


def emit_error(message, as_json):
    if as_json:
        print(json.dumps({"error": message}, ensure_ascii=False, indent=2))
    else:
        print(message, file=sys.stderr)


def print_result(result, show_why, excerpt_chars):
    print("[%6.2f] %s  %s" % (result["score"], result["id"], result["title"]))
    print("          path: %s" % result["path"])
    print("          abs:  %s" % result["abs_path"])
    print(
        "          tags: %s | type: %s | stage: %s"
        % (core.printable(result["tags"]), result["type"], core.printable(result["stage"]))
    )
    if show_why and result.get("why"):
        phrase = result.get("phrase") or ""
        print("          why:  %s%s" % (
            ",".join(result["why"]),
            (" | phrase: " + phrase) if phrase else "",
        ))
    if excerpt_chars and result.get("excerpt"):
        print("          excerpt:")
        for line in result["excerpt"].splitlines():
            print("            " + line)
    print()


def attach_excerpts(engine, results, query, chars, safe=True):
    if not chars:
        return results
    for result in results:
        result["excerpt"] = engine.excerpt(result, query=query, max_chars=chars, safe=safe)
    return results


def load_batch_queries(path):
    queries = []
    text = Path(path).read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        queries.append(line)
    return queries


def main():
    core.setup_streams()
    parser = argparse.ArgumentParser(description="EmoChat-KB 便携检索")
    parser.add_argument("query", nargs="?", help="查询词")
    parser.add_argument("--top", type=int, default=8, help="返回条数，默认 8")
    parser.add_argument("--tag", help="按标签/类型/受众过滤")
    parser.add_argument("--board", help="按板块前缀过滤，如 06")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument("--kb", help="知识库根目录")
    parser.add_argument("--excerpt", nargs="?", type=int, const=600, default=0,
                        help="附带卡片摘要，默认 600 字；不传则不输出")
    parser.add_argument("--queries", nargs="+", help="一次运行多组查询")
    parser.add_argument("--batch", help="查询词文件，一行一组")
    parser.add_argument("--merge", action="store_true", help="批量查询合并排序")
    parser.add_argument("--why", action="store_true", help="显示命中词与短语")
    parser.add_argument("--no-diversify", action="store_true", help="关闭板块/标题去重")
    parser.add_argument("--rebuild-index", action="store_true", help="忽略缓存重建索引")
    parser.add_argument("--cache-dir", help="索引缓存目录")
    parser.add_argument("--index-info", action="store_true", help="显示索引来源与规模")
    parser.add_argument("--timing", action="store_true", help="向 stderr 输出耗时")
    args = parser.parse_args()

    queries = []
    if args.query:
        queries.append(args.query)
    if args.queries:
        queries.extend(args.queries)
    if args.batch:
        try:
            queries.extend(load_batch_queries(args.batch))
        except OSError as exc:
            emit_error("无法读取查询文件: %s" % exc, args.json)
            return 2
    if not queries and not args.index_info:
        parser.print_help()
        return 1

    kb = core.resolve_kb(args.kb)
    if kb is None:
        message = (
            "找不到 EmoChat-KB。请用 --kb 指定仓库根目录，"
            "或设置 EMOCHAT_KB 环境变量。"
        )
        emit_error(message, args.json)
        return 2

    total_started = time.perf_counter()
    engine = core.SearchEngine(kb, cache_dir=args.cache_dir, rebuild=args.rebuild_index)
    diversify = not args.no_diversify

    if args.index_info:
        info = {
            "kb": str(kb),
            "source": engine.meta.get("source"),
            "load_ms": engine.meta.get("load_ms"),
            "build_ms": engine.meta.get("build_ms"),
            "cached": engine.meta.get("cached"),
            "docs": len(engine.docs),
            "vocab": len(engine.vocab),
            "cache_dir": engine.meta.get("cache_dir"),
            "signature": engine.meta.get("signature"),
        }
        if args.json:
            print(json.dumps(info, ensure_ascii=False, indent=2))
        else:
            for key, value in info.items():
                print("%s: %s" % (key, value))
        return 0

    search_started = time.perf_counter()
    if len(queries) > 1 or args.batch or args.queries:
        specs = [{"query": query, "weight": 1.0} for query in queries]
        if args.merge:
            results, normalized = engine.batch(specs, top=args.top,
                                               per_query=max(6, args.top),
                                               diversify=diversify)
            attach_excerpts(engine, results, " ".join(queries), args.excerpt)
            if args.json:
                print(json.dumps({
                    "queries": [item["query"] for item in normalized],
                    "results": results,
                }, ensure_ascii=False, indent=2))
            else:
                print("## merged: %s" % " | ".join(item["query"] for item in normalized))
                for result in results:
                    print_result(result, args.why, args.excerpt)
        else:
            grouped = {}
            for query in queries:
                results = engine.search(query, top=args.top, tag=args.tag,
                                        board=args.board, diversify=diversify)
                attach_excerpts(engine, results, query, args.excerpt)
                grouped[query] = results
            if args.json:
                print(json.dumps(grouped, ensure_ascii=False, indent=2))
            else:
                for query, results in grouped.items():
                    print("## %s" % query)
                    if not results:
                        print("(无匹配结果)\n")
                        continue
                    for result in results:
                        print_result(result, args.why, args.excerpt)
    else:
        results = engine.search(queries[0], top=max(1, args.top), tag=args.tag,
                                board=args.board, diversify=diversify)
        attach_excerpts(engine, results, queries[0], args.excerpt)
        if args.json:
            print(json.dumps(results, ensure_ascii=False, indent=2))
        elif not results:
            print("(无匹配结果)")
        else:
            for result in results:
                print_result(result, args.why, args.excerpt)

    if args.timing:
        elapsed = (time.perf_counter() - total_started) * 1000
        search_ms = (time.perf_counter() - search_started) * 1000
        print(
            "timing: total=%.0fms search=%.0fms index_load=%.0fms index_build=%.0fms "
            "source=%s docs=%d"
            % (
                elapsed,
                search_ms,
                engine.meta.get("load_ms") or 0,
                engine.meta.get("build_ms") or 0,
                engine.meta.get("source"),
                len(engine.docs),
            ),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
