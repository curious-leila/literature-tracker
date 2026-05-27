"""
Parse CNKI tagged export format and WOS RIS format into a unified data structure.
"""

import re
import hashlib
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Paper:
    title: str
    authors: str
    year: str
    source: str  # "CNKI" or "WOS"
    search_keyword: str  # which search query yielded this paper
    abstract: str = ""
    keywords: str = ""
    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    link: str = ""
    language: str = ""
    pub_type: str = ""  # Journal Article / Dissertation / Newspaper / Book / Conference
    advisor: str = ""  # dissertation advisor
    university: str = ""  # dissertation university
    degree: str = ""  # 硕士/博士

    @property
    def dedup_key(self) -> str:
        """Generate a stable dedup key from title (first 50 chars normalized)."""
        normalized = re.sub(r"[^a-zA-Z0-9一-鿿]", "", self.title.lower())
        return hashlib.md5(normalized[:50].encode()).hexdigest()

    @property
    def brief(self) -> str:
        """One-line description for sorting/filtering."""
        parts = [self.title[:80]]
        if self.year:
            parts.append(f"({self.year})")
        if self.journal:
            parts.append(self.journal[:30])
        return " ".join(parts)


# ── CNKI tagged format parser ──

def parse_cnki(text: str, search_keyword: str = "") -> list[Paper]:
    """
    Parse CNKI Refworks-format text export.
    Each record is separated by blank lines, fields are tagged like `T1 title`.
    """
    records = _split_cnki_records(text)
    papers = []
    for rec in records:
        p = _parse_one_cnki(rec, search_keyword)
        if p and p.title:
            papers.append(p)
    return papers


def _split_cnki_records(text: str) -> list[str]:
    """Split concatenated CNKI records into individual entries."""
    text = text.strip()
    # strategy: split on `RT ` (record type marker)
    parts = re.split(r"\n(?=RT \w)", text)
    return [p.strip() for p in parts if p.strip()]


def _parse_one_cnki(record: str, search_keyword: str) -> Paper | None:
    """Parse a single CNKI tagged record."""
    fields = _parse_tagged_fields(record)

    title = fields.get("T1", "")
    if not title:
        return None

    return Paper(
        title=title,
        authors=fields.get("A1", ""),
        year=_extract_year(fields.get("YR", "")),
        source="CNKI",
        search_keyword=search_keyword,
        abstract=fields.get("AB", ""),
        keywords=fields.get("K1", ""),
        journal=fields.get("JF", ""),
        volume=fields.get("vo", ""),
        issue=fields.get("IS", ""),
        pages=fields.get("OP", ""),
        doi=fields.get("DO", ""),
        link=fields.get("LK", ""),
        language=fields.get("LA", ""),
        pub_type=_normalize_cnki_type(fields.get("RT", "")),
        advisor=fields.get("A3", ""),
        university=fields.get("PB", ""),
        degree=_map_degree(fields.get("CL", "")),
    )


def _parse_tagged_fields(record: str) -> dict[str, str]:
    """Parse multi-line tagged format where each line is `TAG value`."""
    result = {}
    for line in record.split("\n"):
        line = line.strip()
        if not line:
            continue
        match = re.match(r"^(\w+)\s+(.*)", line)
        if match:
            tag, value = match.groups()
            value = value.strip()
            # some tags can appear multiple times (e.g. SN for ISSN + EISSN)
            if tag in result and tag in ("SN",):
                continue  # keep the first one
            result[tag] = value
    return result


def _normalize_cnki_type(rt: str) -> str:
    type_map = {
        "Journal Article": "Journal Article",
        "Newspaper Article": "Newspaper",
        "Dissertation/Thesis": "Dissertation",
        "Conference Proceeding": "Conference",
        "Book": "Book",
    }
    return type_map.get(rt, rt)


def _map_degree(cl: str) -> str:
    if "博士" in cl:
        return "博士"
    if "硕士" in cl:
        return "硕士"
    return cl


# ── WOS RIS format parser ──

def parse_wos_ris(text: str, search_keyword: str = "") -> list[Paper]:
    """
    Parse WOS RIS-format export.
    Records are delimited by `TY  - ...` ... `ER  -`.
    """
    records = _split_ris_records(text)
    papers = []
    for rec in records:
        p = _parse_one_ris(rec, search_keyword)
        if p and p.title:
            papers.append(p)
    return papers


def _split_ris_records(text: str) -> list[str]:
    """Split RIS text into individual records."""
    text = text.strip()
    parts = re.split(r"\n(?=TY\s+-)", text)
    return [p.strip() for p in parts if p.strip() and "TY  -" in p]


def _parse_one_ris(record: str, search_keyword: str) -> Paper | None:
    """Parse a single RIS record."""
    fields = _parse_ris_fields(record)

    title = fields.get("TI", "")
    if not title:
        return None

    # extract year from PY or DA field
    year = _extract_year(fields.get("PY", ""))
    if not year:
        year = _extract_year(fields.get("DA", ""))

    return Paper(
        title=title,
        authors=fields.get("AU", ""),
        year=year,
        source="WOS",
        search_keyword=search_keyword,
        abstract=fields.get("AB", ""),
        keywords=fields.get("KW", ""),
        journal=fields.get("T2", "") or fields.get("JF", ""),
        volume=fields.get("VL", ""),
        issue=fields.get("IS", ""),
        pages=f"{fields.get('SP', '')}-{fields.get('EP', '')}".strip("-"),
        doi=fields.get("DO", ""),
        link="",
        language=fields.get("LA", ""),
        pub_type="Journal Article",  # WOS is primarily journals
    )


def _parse_ris_fields(record: str) -> dict[str, str]:
    """Parse RIS tagged format: `TAG  - value`."""
    result = {}
    for line in record.split("\n"):
        match = re.match(r"^(\w{2})\s+-\s+(.*)", line)
        if match:
            tag, value = match.groups()
            value = value.strip()
            # handle multi-occurrence fields
            if tag in ("AU", "KW", "SN"):
                if tag in result:
                    result[tag] += "; " + value
                else:
                    result[tag] = value
            elif tag not in result:
                result[tag] = value
    return result


# ── utilities ──

def _extract_year(s: str) -> str:
    """Extract first 4-digit year from a string."""
    match = re.search(r"(\d{4})", s)
    return match.group(1) if match else ""


def load_file(filepath: Path) -> str:
    """Load file content, trying UTF-8 first then GBK."""
    for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            return filepath.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"Cannot decode {filepath}")


def detect_format(filepath: Path) -> str:
    """
    Detect format by extension and content.
    Returns 'cnki', 'wos_ris', or 'unknown'.
    """
    name = filepath.name.lower()
    if name.endswith(".ris"):
        return "wos_ris"
    # try reading first few lines
    content = load_file(filepath)
    if content.strip().startswith("RT "):
        return "cnki"
    if "TY  -" in content[:200]:
        return "wos_ris"
    return "unknown"


def parse_file(filepath: Path, search_keyword: str = "") -> list[Paper]:
    """Auto-detect format and parse."""
    fmt = detect_format(filepath)
    content = load_file(filepath)
    if fmt == "cnki":
        return parse_cnki(content, search_keyword)
    elif fmt == "wos_ris":
        return parse_wos_ris(content, search_keyword)
    else:
        raise ValueError(f"Unknown format for {filepath}")


# ── database ──

def init_db(db_path: str) -> sqlite3.Connection:
    """Create or open the SQLite database with the papers table."""
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dedup_key TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            authors TEXT,
            year TEXT,
            source TEXT,
            search_keyword TEXT,
            abstract TEXT,
            keywords TEXT,
            journal TEXT,
            volume TEXT,
            issue TEXT,
            pages TEXT,
            doi TEXT,
            link TEXT,
            language TEXT,
            pub_type TEXT,
            advisor TEXT,
            university TEXT,
            degree TEXT,
            relevance TEXT,         -- 'high' / 'medium' / 'low' (set by Claude)
            analysis TEXT,          -- AI-generated analysis
            pushed INTEGER DEFAULT 0,  -- 0 = not pushed, 1 = pushed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


def paper_exists(conn: sqlite3.Connection, dedup_key: str) -> bool:
    """Check if a paper with this dedup_key already exists."""
    cur = conn.execute("SELECT 1 FROM papers WHERE dedup_key = ?", (dedup_key,))
    return cur.fetchone() is not None


def insert_paper(conn: sqlite3.Connection, paper: Paper) -> bool:
    """
    Insert a paper if not already present.
    Returns True if inserted, False if duplicate.
    """
    if paper_exists(conn, paper.dedup_key):
        return False
    conn.execute("""
        INSERT INTO papers (dedup_key, title, authors, year, source, search_keyword,
                           abstract, keywords, journal, volume, issue, pages, doi,
                           link, language, pub_type, advisor, university, degree)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        paper.dedup_key, paper.title, paper.authors, paper.year, paper.source,
        paper.search_keyword, paper.abstract, paper.keywords, paper.journal,
        paper.volume, paper.issue, paper.pages, paper.doi, paper.link,
        paper.language, paper.pub_type, paper.advisor, paper.university, paper.degree,
    ))
    conn.commit()
    return True


def get_unpushed_papers(conn: sqlite3.Connection, since_days: int = 30) -> list[dict]:
    """Get papers that haven't been pushed yet, inserted in the last N days."""
    cur = conn.execute("""
        SELECT * FROM papers
        WHERE pushed = 0
          AND created_at >= datetime('now', ?)
        ORDER BY year DESC, created_at DESC
    """, (f"-{since_days} days",))
    return [dict(zip([c[0] for c in cur.description], row)) for row in cur.fetchall()]


def mark_as_pushed(conn: sqlite3.Connection, paper_ids: list[int]) -> None:
    """Mark papers as pushed."""
    conn.execute(
        f"UPDATE papers SET pushed = 1 WHERE id IN ({','.join('?' * len(paper_ids))})",
        paper_ids,
    )
    conn.commit()


# ── Journal tier lookup ──

TIER_RANK = {
    "SSCI": 1,
    "CSSCI": 2,
    "CSSCI扩展版": 3,
    "北大核心": 4,
    "AMI": 5,
    "普刊": 6,
    "WOS收录": 7,
    "": 8,  # unclassified
}

# SSCI journals (appeared in user's WOS exports)
SSCI_JOURNALS = {
    "BABEL", "TARGET", "TRANSLATOR", "TRANSLATION STUDIES",
    "PERSPECTIVES", "TRANSLATION AND INTERPRETING STUDIES",
    "INTERPRETER AND TRANSLATOR TRAINER", "ACROSS LANGUAGES AND CULTURES",
    "META", "LINGUISTICA ANTVERPIENSIA",
    "MEMORY STUDIES", "CHINA QUARTERLY", "JOURNAL OF ASIAN STUDIES",
    "RETHINKING HISTORY", "EUROPEAN JOURNAL OF ENGLISH STUDIES",
    "TOURISM GEOGRAPHIES", "SEMIOTICA", "EDUCATIONAL PHILOSOPHY AND THEORY",
    "DUTCH CROSSING", "INTERVENTIONS", "AREA",
    "BABEL-REVUE INTERNATIONALE DE LA TRADUCTION",
}

# CSSCI 来源期刊 (2023-2024, subset appearing in user's data)
CSSCI_JOURNALS = {
    "上海翻译", "外国语", "外国语(上海外国语大学学报)", "外国语文",
    "外语电化教学", "外语教学", "外语教学与研究", "外语界", "外语研究",
    "现代外语", "中国外语", "外语学刊", "中国翻译",
    "解放军外国语学院学报", "外语与外语教学",
    "抗日战争研究", "历史研究", "近代史研究", "中共党史研究",
    "社会学研究", "新闻与传播研究", "文学评论", "外国文学评论",
    "国外文学", "当代文坛", "扬子江评论", "华文文学", "文艺研究",
    "南京社会科学", "民国档案", "档案与建设",
    "新闻大学", "江西社会科学", "湖南科技大学学报(社会科学版)",
    "复旦外国语言文学论丛", "中国图书评论", "艺术评论",
    "中国农史", "中共党史资料",
}

# CSSCI 扩展版
CSSCI_EXTENDED = {
    "翻译研究与教学", "翻译学刊",
    "外语教育研究", "外国语文研究",
    "汕头大学学报(人文社会科学版)", "江苏科技大学学报(社会科学版)",
    "亚太跨学科翻译研究",
}

# 北大核心
BEIDA_CORE = {
    "日本侵华南京大屠杀研究", "日本侵华史研究",
    "中国朝鲜语文", "日语学习与研究",
    "南京大屠杀史研究", "江淮文史",
    "名作欣赏", "安徽史学", "文史精华",
    "钟山风雨", "兰台世界",
    "国际人才交流",
}

# AMI (社科院)
AMI_JOURNALS = {
    "翻译史论丛",
    "福建开放大学学报", "牡丹江大学学报", "唐山师范学院学报",
    "百色学院学报", "池州学院学报",
    "辽宁行政学院学报", "湖北经济学院学报(人文社会科学版)",
    "黑龙江工业学院学报(综合版)", "吉林省教育学院学报",
}

# 普刊 (clearly non-core)
PU_JOURNALS = {
    "海外英语", "英语广场", "校园英语", "现代英语",
    "文教资料", "档案", "档案天地", "山西档案",
    "全国新书目", "课外阅读", "青少年日记",
    "出版广角", "紫金岁月", "民国春秋", "百年潮",
    "传播与版权", "文化产业",
    "世纪风采", "黑河学刊", "云南档案", "广西党史",
    "共产党员", "唯实",
}


def get_journal_tier(source: str, journal: str) -> str:
    """Determine journal tier. Returns tier name string."""
    if not journal:
        return ""

    j_upper = journal.upper().strip()
    j_orig = journal.strip()

    if source == "WOS":
        for s in SSCI_JOURNALS:
            if s in j_upper:
                return "SSCI"
        return "WOS收录"

    if source == "CNKI":
        # Check CSSCI first
        for c in CSSCI_JOURNALS:
            if c in j_orig:
                return "CSSCI"
        # CSSCI扩展版
        for c in CSSCI_EXTENDED:
            if c in j_orig:
                return "CSSCI扩展版"
        # 北大核心
        for c in BEIDA_CORE:
            if c in j_orig:
                return "北大核心"
        # AMI
        for c in AMI_JOURNALS:
            if c in j_orig:
                return "AMI"
        # 普刊
        for c in PU_JOURNALS:
            if c in j_orig:
                return "普刊"
        # University journals (大学学报/学院学报) — assume AMI at minimum
        if "大学学报" in j_orig or "学院学报" in j_orig:
            return "AMI"
        return ""

    return ""


def update_relevance(conn: sqlite3.Connection, paper_id: int, relevance: str, analysis: str) -> None:
    """Update the AI analysis fields for a paper."""
    conn.execute(
        "UPDATE papers SET relevance = ?, analysis = ? WHERE id = ?",
        (relevance, analysis, paper_id),
    )
    conn.commit()
