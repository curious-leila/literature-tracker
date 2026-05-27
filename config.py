import os
from dotenv import load_dotenv

load_dotenv()

# ── LLM API (SiliconFlow free tier by default) ──
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Which LLM to use: "siliconflow" (free, China-friendly) / "groq" / "gemini"
LLM_BACKEND = os.getenv("LLM_BACKEND", "siliconflow")

# ── email push ──
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.163.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")

# ── research framework ──
RESEARCH_FRAMEWORK = """
研究框架：南京大屠杀翻译研究 × 文化记忆理论

核心研究对象：
- 南京大屠杀相关文本（史料、日记、口述、文学）的翻译与跨文化传播
- 魏特琳日记（Minnie Vautrin's Diary）及其汉译
- 翻译如何参与历史记忆的跨文化建构

核心理论框架：文化记忆理论（Jan Assmann & Aleida Assmann）
- 翻译作为文化记忆的媒介与建构方式
- 记忆场（lieux de mémoire）与翻译的关系
- 交际记忆向文化记忆的转换中的翻译角色

强相关判定标准（按优先级）：
1. 直接讨论南京大屠杀/魏特琳日记的翻译问题
2. 讨论历史记忆/文化记忆与翻译的关系，且涉及创伤事件
3. 讨论大屠杀/战争相关文本的翻译伦理或翻译策略
4. 从文化记忆理论视角研究翻译（不限具体事件）

中度相关判定标准：
1. 讨论翻译与文化记忆，但案例不涉及创伤事件
2. 讨论南京大屠杀的历史/记忆/传播，但不以翻译为核心
3. 讨论翻译与身份认同/民族情感/集体记忆

背景阅读：
1. 纯文化记忆理论研究（不涉及翻译）
2. 南京大屠杀的历史研究（不涉及翻译也不涉及记忆）
3. 泛化的翻译策略/翻译伦理讨论（无文化记忆维度）
"""

# ── search keywords ──
SEARCH_KEYWORDS = {
    "core": [
        "南京大屠杀 翻译",
        "魏特琳日记",
        "Nanjing Massacre translation",
        "Minnie Vautrin diary",
    ],
    "extended": [
        "翻译 文化记忆",
        "translation cultural memory",
    ],
}

# ── database path ──
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "literature.db")
