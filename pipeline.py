"""Parse exported files, deduplicate, analyze, and deliver a literature brief."""

import argparse
import sys
import time
from pathlib import Path

import config
from parser import (
    init_db,
    insert_paper,
    get_unpushed_papers,
    update_relevance,
    mark_as_pushed,
    parse_file,
    get_journal_tier,
    TIER_RANK,
)


def step_collect(import_dir: Path, conn) -> int:
    """
    Scan data/imports/ for CNKI and WOS export files.
    Parse each file, insert new papers into the database.
    Returns count of newly inserted papers.
    """
    if not import_dir.exists():
        print(f"[DIR] Import directory not found: {import_dir}")
        return 0

    files = list(import_dir.glob("*"))
    if not files:
        print("[DIR] No files in import directory. Drop exported files into data/imports/ and re-run.")
        return 0

    keyword_map = {
        "nanjing-massacre-translation": "南京大屠杀 翻译",
        "nanjing-translation": "南京大屠杀 翻译",
        "vautrin-diary": "魏特琳日记",
        "vautrin": "魏特琳日记",
        "minnie vautrin": "Minnie Vautrin diary",
        "translation-cultural-memory": "翻译 文化记忆",
        "cultural memory": "translation cultural memory",
        "cnki_": "CNKI",
    }

    total_new = 0
    for fp in files:
        if fp.name.startswith(".") or fp.name.startswith("~"):
            continue
        try:
            # guess keyword from filename
            kw = _guess_keyword(fp.name, keyword_map)
            papers = parse_file(fp, search_keyword=kw)
            new_count = 0
            for p in papers:
                if insert_paper(conn, p):
                    new_count += 1
            print(f"   {fp.name}: {len(papers)} parsed, {new_count} new ({kw})")
            total_new += new_count
        except Exception as e:
            print(f"   [WARN]  {fp.name}: {e}")

    return total_new


def _guess_keyword(filename: str, keyword_map: dict) -> str:
    """Guess search keyword from filename."""
    lower = filename.lower()
    for pattern, kw in keyword_map.items():
        if pattern.lower() in lower:
            return kw
    return "unknown"


def step_analyze(conn) -> list[dict]:
    """
    Get unpushed papers and analyze them with the configured LLM.

    The run is all-or-nothing: incomplete or malformed model output is not
    persisted, so the same papers remain eligible for a safe retry.
    """
    papers = get_unpushed_papers(conn, since_days=30)
    if not papers:
        print("[---] No new papers to analyze.")
        return []

    print(f"[AI] Sending {len(papers)} papers to {config.LLM_BACKEND} for analysis...")
    analyzed = _call_ai_analyze(papers)
    _validate_analysis_results(analyzed, expected_count=len(papers))

    for p in analyzed:
        update_relevance(conn, p["id"], p["relevance"], p["analysis"])

    return analyzed


def _validate_analysis_results(papers: list[dict], expected_count: int) -> None:
    """Reject partial or malformed LLM output before it reaches persistence."""
    allowed = {"high", "medium", "low"}
    invalid = []

    if len(papers) != expected_count:
        raise ValueError(
            f"Incomplete AI response: expected {expected_count} papers, got {len(papers)}."
        )

    for position, paper in enumerate(papers, start=1):
        relevance = paper.get("relevance")
        analysis = paper.get("analysis")
        if relevance not in allowed or not isinstance(analysis, str) or not analysis.strip():
            invalid.append(str(paper.get("id", position)))

    if invalid:
        raise ValueError(
            "Incomplete AI response for paper ids: " + ", ".join(invalid)
        )


def _call_ai_analyze(papers: list[dict]) -> list[dict]:
    """
    Send papers to AI for relevance screening.
    Uses SiliconFlow (free, China-friendly) by default.
    Groq / Gemini / Claude optional.
    """
    if config.LLM_BACKEND == "claude":
        return _analyze_with_claude(papers)
    elif config.LLM_BACKEND == "gemini":
        return _analyze_with_gemini(papers)
    elif config.LLM_BACKEND == "groq":
        return _analyze_with_groq(papers)
    else:
        return _analyze_with_siliconflow(papers)


def _build_prompt(papers: list[dict]) -> tuple[str, str]:
    """Build system and user prompts for paper analysis."""
    paper_texts = []
    for i, p in enumerate(papers):
        text = f"[{i+1}] {p['title']}\n"
        text += f"    来源: {p['source']} | 年份: {p['year']} | 类型: {p['pub_type']}\n"
        text += f"    关键词: {p['keywords']}\n"
        if p['abstract']:
            text += f"    摘要: {p['abstract'][:500]}\n"
        if p['authors']:
            text += f"    作者: {p['authors']}\n"
        paper_texts.append(text)

    papers_block = "\n".join(paper_texts)

    system = f"""你是翻译学与文化记忆交叉研究领域的助理。按以下标准对文献严格分类：

研究框架：魏特琳日记汉译对南京大屠杀文化记忆的建构作用
理论视角：文化记忆理论（Jan Assmann & Aleida Assmann）——翻译如何参与建构文化记忆

【正面规则】以下任一情况为强相关（HIGH）：
1. 直接讨论南京大屠杀/魏特琳日记的翻译问题
2. 讨论历史记忆/文化记忆与翻译的关系，且涉及创伤事件
3. 讨论大屠杀/战争相关文本的翻译伦理或翻译策略
4. 从文化记忆理论视角研究翻译（不限具体事件）

以下情况为中度相关（MEDIUM）：
1. 讨论翻译与文化记忆，但案例不涉及创伤事件
2. 讨论南京大屠杀的历史/记忆/传播，但不以翻译为核心
3. 讨论翻译与身份认同/民族情感/集体记忆

以下情况为低相关（LOW）：
1. 纯文化记忆理论研究（不涉及翻译）
2. 南京大屠杀的历史研究（不涉及翻译也不涉及记忆）
3. 泛化的翻译策略/翻译伦理讨论（无文化记忆维度）

【硬性条件】HIGH必须同时满足：
(1) 确实涉及翻译/译介问题
(2) 涉及南京大屠杀/魏特琳日记/文化记忆理论中至少一个
缺任一条件则降为MEDIUM或LOW。

【常见误判提醒】以下情况最多给MEDIUM：
- 纯南京大屠杀历史研究，如不涉及翻译 → LOW
- 教材改编、歌剧表演、舞剧研究，如不涉及翻译 → LOW
- 泛泛的翻译策略讨论（如"外宣翻译策略"无文化记忆维度）→ LOW
- 翻译实践报告如不涉及相关理论框架 → LOW

【补充排除规则】以下翻译类型即使涉及南京大屠杀，如不涉及记忆建构/叙事框定/历史再现，最多给MEDIUM：
- 博物馆展陈翻译、建筑标识翻译等应用型翻译
- 翻译质量评估等纯语言技术类型
- 译者素养归纳、翻译策略总结等无文化记忆理论框架型

请对以下{len(papers)}篇文献逐一分析。"""

    user = f"""文献列表：

{papers_block}

对每篇文献，严格按以下格式输出（每篇一行，不要任何多余内容）：
[序号] 相关度 | 判定理由 | 研究交叉点 | 阅读建议

相关度用: HIGH / MEDIUM / LOW
阅读建议用: 优先阅读全文 / 阅读相关章节 / 浏览摘要 / 背景参考 / 不相关
交叉点如果LOW则为"无"

重要：判定理由必须针对该文献的具体内容撰写，禁止使用模板化表述。例如"讨论南京大屠杀战时对外宣传的翻译活动"优于"直接讨论南京大屠杀翻译与记忆建构"。

示例：
[1] HIGH | 直接讨论南京大屠杀翻译与记忆建构 | 使用了你的核心理论框架文化记忆 | 优先阅读全文
[2] MEDIUM | 讨论翻译与文化记忆但案例不涉及创伤 | 可借鉴理论框架 | 浏览摘要
[3] LOW | 纯历史研究无翻译维度 | 无 | 不相关"""

    return system, user


def _parse_ai_response(raw: str, papers: list[dict]) -> list[dict]:
    """Parse line-format or JSON response and map back to papers."""
    import json
    import re
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:-3]
        raw = raw.strip()

    # Try JSON first (backward compat with Claude/Groq when they emit JSON)
    if raw.startswith("["):
        try:
            results = json.loads(raw)
            for r in results:
                idx = r["index"] - 1
                if 0 <= idx < len(papers):
                    papers[idx]["relevance"] = r["relevance"]
                    papers[idx]["analysis"] = (
                        f"判定理由: {r['reason']}\n"
                        f"研究交叉点: {r['cross_point']}\n"
                        f"阅读建议: {r['suggestion']}"
                    )
            return papers
        except (json.JSONDecodeError, KeyError, TypeError):
            pass  # Fall through to line-based parsing

    # Line-based format: [N] RELEVANCE | reason | cross_point | suggestion
    for line in raw.split("\n"):
        line = line.strip()
        if not line or not line.startswith("["):
            continue
        m = re.match(r"\[(\d+)\]\s*(\w+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.+)", line)
        if not m:
            continue
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(papers):
            relevance = m.group(2).lower()
            if relevance not in ("high", "medium", "low"):
                relevance = "low"
            papers[idx]["relevance"] = relevance
            papers[idx]["analysis"] = (
                f"判定理由: {m.group(3).strip()}\n"
                f"研究交叉点: {m.group(4).strip()}\n"
                f"阅读建议: {m.group(5).strip()}"
            )
    return papers


def _analyze_with_groq(papers: list[dict]) -> list[dict]:
    """Use Groq API (free tier) for analysis. Processes papers in batches of 10 to stay within free tier limits."""
    try:
        from groq import Groq
    except ImportError:
        print("[WARN] groq not installed. Run: pip install groq")
        return _mark_unanalyzed(papers)

    if not config.GROQ_API_KEY:
        print("[WARN] GROQ_API_KEY not set. Trying Gemini...")
        if config.GEMINI_API_KEY:
            return _analyze_with_gemini(papers)
        return _mark_unanalyzed(papers)

    client = Groq(api_key=config.GROQ_API_KEY)
    BATCH_SIZE = 10
    all_results = papers.copy()

    for batch_start in range(0, len(all_results), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_results))
        batch = all_results[batch_start:batch_end]
        batch_index = batch_start  # the starting index of this batch in all_results

        system, user = _build_prompt(batch)
        print(f"   ... batch {batch_start//BATCH_SIZE + 1}: papers {batch_start+1}-{batch_end} / {len(all_results)}")

        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            batch = _parse_ai_response(response.choices[0].message.content, batch)
            # write back to all_results
            for i, p in enumerate(batch):
                all_results[batch_start + i] = p
        except Exception as e:
            print(f"      [WARN] batch failed: {e}")
            for i in range(batch_start, batch_end):
                all_results[i] = _mark_one(all_results[i])

        time.sleep(3)  # rate limit buffer

    ok_count = sum(1 for p in all_results if p.get("relevance") != "unanalyzed")
    print(f"   [OK] Groq analyzed: {ok_count}/{len(all_results)} papers.")
    return all_results


def _mark_one(p: dict) -> dict:
    p["relevance"] = "unanalyzed"
    p["analysis"] = ""
    return p


def _analyze_with_siliconflow(papers: list[dict]) -> list[dict]:
    """Use SiliconFlow API (free tier, China-friendly, OpenAI-compatible) for analysis. Batched to stay under 32K context limit."""
    from openai import OpenAI

    if not config.SILICONFLOW_API_KEY:
        print("[WARN] SILICONFLOW_API_KEY not set.")
        return _mark_unanalyzed(papers)

    client = OpenAI(
        api_key=config.SILICONFLOW_API_KEY,
        base_url="https://api.siliconflow.cn/v1",
    )

    BATCH_SIZE = 8
    all_results = papers.copy()

    for batch_start in range(0, len(all_results), BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE, len(all_results))
        batch = all_results[batch_start:batch_end]

        system, user = _build_prompt(batch)
        print(f"   ... batch {batch_start//BATCH_SIZE + 1}: papers {batch_start+1}-{batch_end} / {len(all_results)}")

        try:
            response = client.chat.completions.create(
                model="Qwen/Qwen2.5-32B-Instruct",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.1,
                max_tokens=2048,
            )
            batch = _parse_ai_response(response.choices[0].message.content, batch)
            for i, p in enumerate(batch):
                all_results[batch_start + i] = p
        except Exception as e:
            print(f"      [WARN] batch failed: {e}")
            for i in range(batch_start, batch_end):
                all_results[i] = _mark_one(all_results[i])

        time.sleep(0.5)  # slight delay between batches

    ok_count = sum(1 for p in all_results if p.get("relevance") != "unanalyzed")
    print(f"   [OK] SiliconFlow analyzed: {ok_count}/{len(all_results)} papers.")
    return all_results


def _analyze_with_gemini(papers: list[dict]) -> list[dict]:
    """Use Gemini API (free tier) for analysis."""
    try:
        from google import genai
    except ImportError:
        print("[WARN]  google-genai not installed. Run: pip install google-genai")
        return _mark_unanalyzed(papers)

    if not config.GEMINI_API_KEY:
        print("[WARN]  GEMINI_API_KEY not set. Skipping AI analysis.")
        return _mark_unanalyzed(papers)

    client = genai.Client(api_key=config.GEMINI_API_KEY)
    system, user = _build_prompt(papers)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=user,
            config={
                "system_instruction": system,
                "temperature": 0.1,
                "max_output_tokens": 4096,
            },
        )
        papers = _parse_ai_response(response.text, papers)
        print(f"   [OK] Gemini analyzed {len(papers)} papers.")
        return papers
    except Exception as e:
        print(f"   [WARN]  Gemini API error: {e}")
        return _mark_unanalyzed(papers)


def _analyze_with_claude(papers: list[dict]) -> list[dict]:
    """Use Claude API (paid) for analysis."""
    try:
        import anthropic
    except ImportError:
        print("[WARN]  anthropic not installed. Run: pip install anthropic")
        return _mark_unanalyzed(papers)

    if not config.ANTHROPIC_API_KEY:
        print("[WARN]  ANTHROPIC_API_KEY not set. Falling back to Gemini.")
        return _analyze_with_gemini(papers)

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    system, user = _build_prompt(papers)

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        papers = _parse_ai_response(response.content[0].text, papers)
        print(f"   [OK] Claude analyzed {len(papers)} papers.")
        return papers
    except Exception as e:
        print(f"   [WARN]  Claude API error: {e}")
        return _mark_unanalyzed(papers)


def _mark_unanalyzed(papers: list[dict]) -> list[dict]:
    """Mark all papers as unanalyzed when no API is available."""
    for p in papers:
        p["relevance"] = "unanalyzed"
        p["analysis"] = ""
    return papers


def step_format_brief(analyzed_papers: list[dict]) -> str:
    """Format analyzed papers into a readable email brief."""
    high = [p for p in analyzed_papers if p.get("relevance") == "high"]
    medium = [p for p in analyzed_papers if p.get("relevance") == "medium"]
    low = [p for p in analyzed_papers if p.get("relevance") in ("low", "background")]

    def _sort_by_tier(papers_list):
        """Sort papers: tier priority, then year descending, then Chinese before English."""
        def sort_key(p):
            tier = get_journal_tier(p.get("source", ""), p.get("journal", ""))
            rank = TIER_RANK.get(tier, 8)
            year = p.get("year", "0") or "0"
            lang = 0 if "en" not in (p.get("language", "")).lower() else 1
            return (rank, -(int(year) if year.isdigit() else 0), lang)
        return sorted(papers_list, key=sort_key)

    from datetime import date
    today = date.today().strftime("%Y.%m.%d")

    lines = []

    # ── Header ──
    lines.append(f"文献简报（{today}）")
    lines.append(f"南京大屠杀文化记忆建构中的魏特琳日记汉译考察（关键词：南京大屠杀翻译、魏特琳日记、翻译与文化记忆）")
    lines.append("")
    lines.append(
        f"本次共处理 {len(analyzed_papers)} 篇｜优先阅读全文 {len(high)} 篇"
        f"｜浏览摘要 {len(medium)} 篇｜背景参考 {len(low)} 篇"
    )
    lines.append("")

    # ── Opening ──
    if high:
        top3 = _sort_by_tier(high)[:3]
        lines.append(
            f"本期最值得关注：《{top3[0].get('title', '')[:40]}》等。"
            "以下优先展示 3 篇，并保留判定理由、研究交叉点和原文入口。"
        )
    elif medium:
        lines.append("本期无强相关新增，以下展示最值得浏览的中度相关文献。")
    else:
        lines.append("本期无强相关或中度相关新增，低相关结果已归档。")
    lines.append("")

    # 邮件只承担“快速决策”，完整记录留在证据页，避免首次全量导入生成数百行正文。
    if high:
        sorted_high = _sort_by_tier(high)
        lines.append("◆ 优先阅读全文｜Top 3")
        lines.append("")
        for i, p in enumerate(sorted_high[:3]):
            lines.extend(_format_paper_block(p, i + 1))

        remaining_high = sorted_high[3:]
        if remaining_high:
            lines.append(f"◆ 其他高相关（{len(remaining_high)} 篇）")
            lines.append("")
            for i, p in enumerate(remaining_high, 1):
                lines.extend(_format_compact_paper_line(p, i))

    if medium:
        sorted_medium = _sort_by_tier(medium)
        preview_count = min(5, len(sorted_medium))
        lines.append(f"◆ 浏览摘要（{len(medium)} 篇，邮件展示前 {preview_count} 篇）")
        lines.append("")
        for i, p in enumerate(sorted_medium[:preview_count], 1):
            lines.extend(_format_compact_paper_line(p, i))

    if not high and not medium and low:
        lines.append("◆ 背景参考｜Top 3")
        lines.append("")
        for i, p in enumerate(_sort_by_tier(low)[:3], 1):
            lines.extend(_format_compact_paper_line(p, i))

    if low:
        lines.append("")
        lines.append(f"◆ 背景参考（{len(low)} 篇）已归档，不在邮件中逐条展开。")

    # ── Closing ──
    lines.append("")
    lines.append("完整运行记录：https://curious-leila.github.io/literature-tracker/#records")
    lines.append("")

    return "\n".join(lines)


def _format_paper_block(p: dict, num: int) -> list[str]:
    """Format a single paper block."""
    lines = []
    journal_info = p.get("journal", "")
    if journal_info and p.get("volume"):
        journal_info += f" {p.get('volume', '')}"
        if p.get("issue"):
            journal_info += f"({p.get('issue', '')})"
    if p.get("year"):
        journal_info = f"{p.get('year', '')} | {journal_info}" if journal_info else p.get("year", "")

    title = p.get("title", "(无标题)")
    lang = p.get("language", "")
    lang_tag = "[EN] " if "en" in lang.lower() else ""

    # Journal tier tag
    tier = get_journal_tier(p.get("source", ""), p.get("journal", ""))
    tier_str = f" [{tier}]" if tier else ""

    lines.append(f"  {num}. {lang_tag}{title}")
    if journal_info:
        lines.append(f"     来源: {p.get('source', '')} | {journal_info}{tier_str}")

    # Clickable link
    link = p.get("link", "") or ""
    doi = p.get("doi", "") or ""
    if link:
        lines.append(f"     链接: {link}")
    elif doi:
        lines.append(f"     DOI: https://doi.org/{doi}")

    if p.get("analysis"):
        for line in p["analysis"].split("\n"):
            if line.strip():
                lines.append(f"     {line.strip()}")
    lines.append("")
    return lines


def _format_compact_paper_line(p: dict, num: int) -> list[str]:
    """Format one paper as a compact title-and-link entry for email scanning."""
    tier = get_journal_tier(p.get("source", ""), p.get("journal", ""))
    meta = " · ".join(
        part for part in [p.get("source", ""), tier, p.get("year", "")] if part
    )
    link = p.get("link", "") or ""
    doi = p.get("doi", "") or ""
    if not link and doi:
        link = f"https://doi.org/{doi}"

    lines = [f"  {num}. {p.get('title', '(无标题)')}"]
    if meta:
        lines.append(f"     {meta}")
    if link:
        lines.append(f"     {link}")
    lines.append("")
    return lines


def step_send_email(content: str) -> bool:
    """Send the briefing via SMTP email."""
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
    from datetime import date

    if not all([config.SMTP_HOST, config.SMTP_USER, config.SMTP_PASS, config.RECIPIENT_EMAIL]):
        print("[WARN]  Email config incomplete. Printing brief to console instead:\n")
        print(content)
        return False

    today = date.today().strftime("%Y.%m.%d")
    msg = MIMEText(content, "plain", "utf-8")
    msg["Subject"] = Header(f"文献简报 | {today}", "utf-8")
    msg["From"] = config.SMTP_USER
    msg["To"] = config.RECIPIENT_EMAIL

    try:
        if config.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15)
            server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASS)
        server.sendmail(config.SMTP_USER, [config.RECIPIENT_EMAIL], msg.as_string())
        server.quit()
        print(f"[MAIL] Brief sent to {config.RECIPIENT_EMAIL}")
        return True
    except Exception as e:
        print(f"[WARN]  Email send failed: {e}")
        print("\n── Brief preview ──\n")
        print(content)
        return False


def run_pipeline(
    *,
    import_dir: Path,
    db_path: Path,
    dry_run: bool = False,
    output_path: Path | None = None,
) -> bool:
    """Run the workflow and return True only when delivery succeeds."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = init_db(str(db_path))

    try:
        print("[>>] Step 1: Collecting papers from import files...")
        new_count = step_collect(import_dir, conn)
        print(f"   [OK] {new_count} new papers inserted.\n")

        print("[AI] Step 2: AI analysis...")
        analyzed = step_analyze(conn)
        if not analyzed:
            print("   No papers to analyze. Done.")
            return True

        print("\n[DOC] Step 3: Formatting brief...")
        brief = step_format_brief(analyzed)
        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(brief, encoding="utf-8")
            print(f"   [OK] Brief written to {output_path}")

        if dry_run:
            print("[DRY RUN] Email skipped; database push state is unchanged.\n")
            print(brief)
            return True

        print("[MAIL] Step 4: Sending brief...")
        success = step_send_email(brief)
        if not success:
            print("   [WARN] Delivery failed; papers remain unpushed for retry.")
            return False

        pushed_ids = [p["id"] for p in analyzed]
        mark_as_pushed(conn, pushed_ids)
        print(f"   [OK] Marked {len(pushed_ids)} papers as pushed.")
        print("\n[OK] Pipeline complete.")
        return True
    finally:
        conn.close()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate the brief without sending email or marking papers as pushed.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional UTF-8 file path for the generated brief.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    success = run_pipeline(
        import_dir=Path("data/imports"),
        db_path=Path(config.DB_PATH),
        dry_run=args.dry_run,
        output_path=args.output,
    )
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
