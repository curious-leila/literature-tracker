import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import * as Tooltip from "@radix-ui/react-tooltip";
import {
  ArrowRight,
  ArrowUpRight,
  Braces,
  Check,
  CheckCircle2,
  Code2,
  Database,
  FileInput,
  Filter,
  Link2,
  Mail,
  Search,
  SearchCheck,
  ShieldCheck,
} from "lucide-react";
import type { EvidenceCase, Relevance, RunSummary } from "./types";

const RelevanceChart = lazy(() => import("./RelevanceChart"));

const workflowSteps = [
  {
    icon: FileInput,
    label: "双源解析",
    detail: "自动识别知网 RefWorks 与 WOS RIS，并统一为文献记录。",
  },
  {
    icon: Database,
    label: "历史去重",
    detail: "基于标准化标题生成唯一键，跨文件、跨批次拒绝重复入库。",
  },
  {
    icon: SearchCheck,
    label: "语义分层",
    detail: "Qwen 按研究问题将文献分为 HIGH、MEDIUM、LOW，并返回理由。",
  },
  {
    icon: Braces,
    label: "简报生成",
    detail: "按相关度与期刊等级排序，保留交叉点、建议和原文入口。",
  },
  {
    icon: Mail,
    label: "邮件送达",
    detail: "SMTP 成功后才写入 pushed 状态；失败记录保留，等待重试。",
  },
] as const;

const relevanceMeta: Record<Relevance, { label: string; color: string; action: string }> = {
  high: { label: "高度相关", color: "#1e40af", action: "优先阅读全文" },
  medium: { label: "间接相关", color: "#d97706", action: "浏览摘要" },
  low: { label: "低度相关", color: "#94a3b8", action: "仅作背景参考" },
};

const promptPurpose: Record<string, string> = {
  v1: "先验证结构化输出可行性",
  v2: "让批量结果能够稳定进入下游",
  v3: "把主题词命中与真实研究相关性拆开",
  v8: "提升边界理解，并要求给出具体理由",
};

function EvidenceBadge({ relevance }: { relevance: Relevance }) {
  return (
    <span className={`badge badge-${relevance}`}>
      <span className="badge-dot" aria-hidden="true" />
      {relevanceMeta[relevance].label}
    </span>
  );
}

function App() {
  const [data, setData] = useState<RunSummary | null>(null);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Relevance | "all">("all");
  const [visibleCount, setVisibleCount] = useState(6);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "run-summary.json")
      .then((response) => {
        if (!response.ok) throw new Error("Evidence unavailable");
        return response.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  useEffect(() => setVisibleCount(6), [query, filter]);

  const filteredRecords = useMemo(() => {
    if (!data) return [];
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return data.records.filter((record) => {
      const matchesFilter = filter === "all" || record.relevance === filter;
      const haystack = `${record.title} ${record.reason} ${record.cross_point} ${record.journal} ${record.source}`.toLocaleLowerCase();
      return matchesFilter && (!normalizedQuery || haystack.includes(normalizedQuery));
    });
  }, [data, filter, query]);

  if (error) {
    return (
      <main className="state-message">
        <ShieldCheck aria-hidden="true" />
        <h1>证据文件加载失败</h1>
        <p>请确认 run-summary.json 已由证据脚本生成。</p>
      </main>
    );
  }

  if (!data) {
    return <main className="state-message">正在校验 Recorded Run…</main>;
  }

  const chartData = (Object.keys(relevanceMeta) as Relevance[]).map((key) => ({
    key,
    name: relevanceMeta[key].label,
    value: data.summary.relevance[key],
    fill: relevanceMeta[key].color,
  }));

  const recordedAt = new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(data.summary.recorded_at.replace(" ", "T")));

  return (
    <Tooltip.Provider delayDuration={180}>
      <a className="skip-link" href="#main-content">跳到主要内容</a>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="返回页面顶部">
          <span className="brand-mark" aria-hidden="true">LT</span>
          <span>Literature Triage</span>
        </a>
        <nav aria-label="主导航">
          <a href="#workflow">工作流</a>
          <a href="#cases">案例</a>
          <a href="#records">运行记录</a>
          <a className="nav-github" href="https://github.com/curious-leila/literature-tracker" target="_blank" rel="noreferrer">
            <Code2 size={16} aria-hidden="true" />
            GitHub
            <ArrowUpRight size={14} aria-hidden="true" />
          </a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero section" id="top">
          <div className="hero-copy">
            <p className="eyebrow"><span /> 真实运行证据 · {recordedAt}</p>
            <h1>把跨平台检索结果，变成一份可行动的文献简报。</h1>
            <p className="hero-lead">
              人工从知网与 WOS 导出检索文件；导入后，解析、历史去重、LLM 语义分层、简报生成与邮件推送由同一工作流完成。
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href="#cases">
                查看真实案例 <ArrowRight size={17} aria-hidden="true" />
              </a>
              <a className="button button-secondary" href="#boundary">了解证据边界</a>
            </div>
          </div>

          <aside className="run-card" aria-label="本次运行概览">
            <div className="run-card-header">
              <div>
                <p className="micro-label">本次运行</p>
                <h2>证据已固化</h2>
              </div>
              <span className="status-pill"><Check size={14} aria-hidden="true" /> 已复算</span>
            </div>
            <dl className="run-meta">
              <div><dt>模型</dt><dd>Qwen2.5-32B</dd></div>
              <div><dt>Prompt</dt><dd>{data.model.prompt_version}</dd></div>
              <div><dt>数据源</dt><dd>CNKI + WOS</dd></div>
              <div><dt>证据类型</dt><dd>真实历史运行</dd></div>
            </dl>
            <p className="run-note">
              <ShieldCheck size={17} aria-hidden="true" />
              页面数据由脚本从导入文件与 SQLite 运行记录生成，可在仓库中一键复算。
            </p>
          </aside>
        </section>

        <section className="section problem-section" aria-labelledby="problem-title">
          <div className="problem-intro">
            <p className="eyebrow">01 / 真实问题</p>
            <h2 id="problem-title">小众交叉选题的难点，不是“搜不到”，而是结果散、重复多、逐篇判断慢。</h2>
            <p>
              项目从“翻译学 × 文化记忆”论文选题出发。知网与 WOS 的结果需要分别导出，再靠人工核对标题、摘要与研究交叉点，需求阶段估算每周约 {data.problem_context.manual_screening_minutes_per_week / 60} 小时。
            </p>
            <span className="source-note">该时长为需求阶段自述基线，不是受控计时实验。</span>
          </div>
          <div className="pain-grid">
            <article><span>01</span><h3>来源分散</h3><p>两套平台、两种导出格式，结果无法直接汇总。</p></article>
            <article><span>02</span><h3>重复劳动</h3><p>跨关键词、跨周检索会反复出现同一篇文献。</p></article>
            <article><span>03</span><h3>判断成本高</h3><p>关键词命中不等于研究相关，仍需逐篇理解语义。</p></article>
          </div>
        </section>

        <section className="metrics section" aria-label="核心运行指标">
          <article><span className="metric-index">01</span><strong>{data.summary.input_files}</strong><span>份导出文件</span></article>
          <article><span className="metric-index">02</span><strong>{data.summary.raw_records}</strong><span>条原始记录</span></article>
          <article><span className="metric-index">03</span><strong>{data.summary.unique_papers}</strong><span>篇唯一文献</span></article>
          <article><span className="metric-index">04</span><strong>{data.summary.links.reachable_total}</strong><span>篇保留原文入口</span></article>
        </section>

        <section className="section section-grid" id="workflow">
          <div className="section-heading">
            <p className="eyebrow">02 / 自动化工作流</p>
            <h2>自动化从“文件导入”开始</h2>
            <p>源站检索与导出仍由人完成。边界之后的五个步骤可以重复运行，并通过数据库状态维持跨批次连续性。</p>
          </div>
          <div className="workflow-panel">
            <div className="manual-boundary">
              <span className="micro-label">人工输入</span>
              <strong>知网 / WOS 检索导出</strong>
              <span>学校权限与检索策略由用户控制</span>
            </div>
            <div className="boundary-line" aria-hidden="true"><span>自动化边界</span></div>
            <div className="workflow-steps">
              {workflowSteps.map(({ icon: Icon, label, detail }, index) => (
                <Tooltip.Root key={label}>
                  <Tooltip.Trigger asChild>
                    <button className="workflow-step" type="button" aria-label={`${label}：${detail}`}>
                      <span className="step-number">0{index + 1}</span>
                      <Icon aria-hidden="true" />
                      <strong>{label}</strong>
                    </button>
                  </Tooltip.Trigger>
                  <Tooltip.Portal>
                    <Tooltip.Content className="tooltip-content" sideOffset={10}>
                      {detail}
                      <Tooltip.Arrow className="tooltip-arrow" />
                    </Tooltip.Content>
                  </Tooltip.Portal>
                </Tooltip.Root>
              ))}
            </div>
          </div>
        </section>

        <section className="section evidence-grid">
          <div className="classification-card">
            <div className="card-heading">
              <div>
                <p className="eyebrow">03 / 真实运行结果</p>
                <h2>159 篇文献被分成三种阅读动作</h2>
              </div>
              <span className="card-kicker">共 {data.summary.unique_papers} 篇</span>
            </div>
            <div className="chart-layout">
              <div className="chart-wrap" aria-hidden="true">
                <Suspense fallback={<div className="chart-loading">正在绘制分布…</div>}>
                  <RelevanceChart data={chartData} />
                </Suspense>
                <div className="chart-center"><strong>{data.summary.unique_papers}</strong><span>唯一文献</span></div>
              </div>
              <div className="chart-legend">
                {chartData.map((entry) => (
                  <div key={entry.key}>
                    <span className="legend-swatch" style={{ background: entry.fill }} aria-hidden="true" />
                    <span><strong>{entry.name}</strong><small>{relevanceMeta[entry.key].action}</small></span>
                    <b>{entry.value}</b>
                  </div>
                ))}
              </div>
            </div>
            <p className="sr-only">高度相关 {data.summary.relevance.high} 篇，间接相关 {data.summary.relevance.medium} 篇，低度相关 {data.summary.relevance.low} 篇。</p>
          </div>

          <aside className="quality-card">
            <p className="eyebrow">交付完整度</p>
            <h2>{data.summary.links.reachable_total} / {data.summary.unique_papers}</h2>
            <p>篇文献在简报中保留了可直达入口</p>
            <div className="quality-breakdown">
              <div><span>原始链接</span><strong>{data.summary.links.direct}</strong></div>
              <div><span>DOI 回退</span><strong>{data.summary.links.doi_fallback}</strong></div>
              <div><span>无入口</span><strong>{data.summary.links.without_link}</strong></div>
            </div>
            <p className="quality-note"><Link2 size={16} aria-hidden="true" /> 链接状态在证据构建时从源记录复算。</p>
          </aside>
        </section>

        <section className="section section-grid cases-section" id="cases">
          <div className="section-heading sticky-heading">
            <p className="eyebrow">04 / 结果案例</p>
            <h2>三档结果，不只是三个标签</h2>
            <p>每条判断同时返回相关性理由、研究交叉点和下一步阅读建议，让用户能复核模型为什么这样分。</p>
          </div>

          <Tabs.Root className="case-tabs" defaultValue="0">
            <Tabs.List className="case-tab-list" aria-label="选择相关度案例">
              {data.cases.map((item, index) => (
                <Tabs.Trigger key={item.id} value={String(index)}>
                  <span>案例 0{index + 1}</span>
                  {relevanceMeta[item.relevance].label}
                </Tabs.Trigger>
              ))}
            </Tabs.List>
            {data.cases.map((item, index) => (
              <Tabs.Content className="case-panel" key={item.id} value={String(index)}>
                <div className="case-topline">
                  <EvidenceBadge relevance={item.relevance} />
                  <span>{item.source}{item.journal_tier ? ` · ${item.journal_tier}` : ""}{item.year ? ` · ${item.year}` : ""}</span>
                </div>
                <h3>{item.title}</h3>
                <div className="case-reasoning">
                  <div><span>判定理由</span><p>{item.reason}</p></div>
                  <div><span>研究交叉点</span><p>{item.cross_point}</p></div>
                </div>
                <div className="case-action">
                  <span><CheckCircle2 size={18} aria-hidden="true" /> 建议动作</span>
                  <strong>{item.suggestion}</strong>
                </div>
              </Tabs.Content>
            ))}
          </Tabs.Root>
        </section>

        <section className="section implementation-section" id="implementation">
          <div className="section-heading horizontal-heading">
            <div>
              <p className="eyebrow">05 / 工作流实现</p>
              <h2>三个关键设计，让它能重复运行，而不只是一次性脚本</h2>
            </div>
            <p>实现重点放在输入兼容、状态连续和失败可恢复上；每项都能在源码或测试中定位。</p>
          </div>
          <div className="implementation-grid">
            <article>
              <span className="implementation-icon"><FileInput aria-hidden="true" /></span>
              <div><p className="micro-label">parser.py</p><h3>双格式统一解析</h3><p>将知网 RefWorks 与 WOS RIS 转为同一数据结构，隔离来源差异。</p></div>
            </article>
            <article>
              <span className="implementation-icon"><Database aria-hidden="true" /></span>
              <div><p className="micro-label">literature.db</p><h3>历史状态去重</h3><p>用标题指纹维护唯一记录和 pushed 状态，支持跨文件、跨周增量处理。</p></div>
            </article>
            <article>
              <span className="implementation-icon"><ShieldCheck aria-hidden="true" /></span>
              <div><p className="micro-label">pipeline.py</p><h3>失败保留重试</h3><p>只有邮件发送成功才标记已推送；分析结果不完整则整批拒绝写入。</p></div>
            </article>
          </div>
        </section>

        <section className="section records-section" id="records">
          <div className="card-heading records-heading">
            <div>
              <p className="eyebrow">06 / 运行记录核验</p>
              <h2>直接核查本次运行的 159 条结果</h2>
              <p>搜索标题、来源、期刊或判定理由；展开任意记录查看模型输出。</p>
            </div>
            <span className="result-count" aria-live="polite">{filteredRecords.length} 条结果</span>
          </div>

          <div className="record-controls">
            <label className="search-field">
              <Search size={18} aria-hidden="true" />
              <span className="sr-only">搜索运行记录</span>
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索标题、期刊或判断理由" type="search" />
            </label>
            <div className="filter-group" aria-label="按相关度筛选">
              <Filter size={17} aria-hidden="true" />
              {(["all", "high", "medium", "low"] as const).map((value) => (
                <button type="button" aria-pressed={filter === value} onClick={() => setFilter(value)} key={value}>
                  {value === "all" ? "全部" : relevanceMeta[value].label}
                </button>
              ))}
            </div>
          </div>

          <div className="record-list">
            {filteredRecords.slice(0, visibleCount).map((record: EvidenceCase) => (
              <details className="record-row" key={record.id}>
                <summary>
                  <span className={`record-dot record-dot-${record.relevance}`} aria-hidden="true" />
                  <span className="record-title">{record.title}</span>
                  <span className="record-source">{record.source}{record.year ? ` · ${record.year}` : ""}</span>
                  <EvidenceBadge relevance={record.relevance} />
                  <span className="record-chevron" aria-hidden="true"><ArrowRight size={17} /></span>
                </summary>
                <div className="record-detail">
                  <div><span>判定理由</span><p>{record.reason}</p></div>
                  <div><span>研究交叉点</span><p>{record.cross_point}</p></div>
                  <div><span>阅读建议</span><p>{record.suggestion}</p></div>
                  <div><span>期刊</span><p>{record.journal || "源记录未提供"}{record.journal_tier ? ` · ${record.journal_tier}` : ""}</p></div>
                </div>
              </details>
            ))}
            {filteredRecords.length === 0 && (
              <div className="empty-state"><Search aria-hidden="true" /><strong>没有匹配的记录</strong><span>试试更短的关键词或切换相关度。</span></div>
            )}
          </div>

          {visibleCount < filteredRecords.length && (
            <button className="button button-secondary load-more" type="button" onClick={() => setVisibleCount((count) => count + 12)}>
              再显示 {Math.min(12, filteredRecords.length - visibleCount)} 条
            </button>
          )}
        </section>

        <section className="section" id="iterations">
          <div className="section-heading horizontal-heading">
            <div>
              <p className="eyebrow">07 / Prompt 迭代</p>
              <h2>从“模型能回答”到“结果能进入工作流”</h2>
            </div>
            <p>8 轮迭代的核心不是追求更长的 Prompt，而是逐步修复格式失效、关键词误判和理由空泛。</p>
          </div>
          <div className="timeline">
            {data.prompt_milestones.map((item, index) => (
              <article key={item.version}>
                <div className="timeline-marker"><span>{index + 1}</span></div>
                <p className="micro-label">{item.version}</p>
                <h3>{item.change}</h3>
                <p>{promptPurpose[item.version]}</p>
                <strong>{item.result}</strong>
              </article>
            ))}
          </div>
        </section>

        <section className="section proof-section" id="proof">
          <div className="section-heading horizontal-heading">
            <div>
              <p className="eyebrow">08 / 可复算证据</p>
              <h2>页面数字不靠手填：导入文件、数据库与展示 JSON 可相互校验</h2>
            </div>
            <a className="button button-secondary" href={`${import.meta.env.BASE_URL}run-summary.json`} target="_blank" rel="noreferrer">
              查看原始 JSON <ArrowUpRight size={16} aria-hidden="true" />
            </a>
          </div>
          <div className="proof-flow">
            <div><span>输入</span><strong>data/imports/</strong><p>5 份真实导出文件</p></div>
            <ArrowRight aria-hidden="true" />
            <div><span>计算</span><strong>build_evidence.py</strong><p>复算、校验、固定案例</p></div>
            <ArrowRight aria-hidden="true" />
            <div><span>输出</span><strong>run-summary.json</strong><p>页面唯一数据源</p></div>
          </div>
          <div className="proof-links">
            <a href="https://github.com/curious-leila/literature-tracker/blob/master/scripts/build_evidence.py" target="_blank" rel="noreferrer">查看计算脚本 <ArrowUpRight size={15} aria-hidden="true" /></a>
            <a href="https://github.com/curious-leila/literature-tracker/blob/master/tests/test_workflow.py" target="_blank" rel="noreferrer">查看可靠性测试 <ArrowUpRight size={15} aria-hidden="true" /></a>
          </div>
        </section>

        <section className="section capability-section">
          <div className="section-heading horizontal-heading">
            <div>
              <p className="eyebrow">09 / 能力映射</p>
              <h2>从真实痛点到可验证交付，项目体现了五项 AI 产品能力</h2>
            </div>
          </div>
          <div className="capability-grid">
            <article><span>01</span><h3>问题定义</h3><p>从重复筛选痛点拆出可自动化边界。</p></article>
            <article><span>02</span><h3>数据接入</h3><p>兼容多源格式并维护历史状态。</p></article>
            <article><span>03</span><h3>LLM 分类</h3><p>把模糊相关性转成三级阅读动作。</p></article>
            <article><span>04</span><h3>工作流交付</h3><p>从输入到邮件形成可恢复闭环。</p></article>
            <article><span>05</span><h3>证据验证</h3><p>用真实运行记录复算产品结果。</p></article>
          </div>
        </section>

        <section className="section boundary-card" id="boundary">
          <div>
            <p className="eyebrow">10 / 项目边界</p>
            <h2>当前证据的适用范围</h2>
          </div>
          <div className="boundary-columns">
            <div>
              <span className="boundary-icon boundary-icon-positive"><CheckCircle2 aria-hidden="true" /></span>
              <h3>当前可证明</h3>
              <ul>
                <li>双格式解析、跨批次去重、语义分层与推送闭环已实现</li>
                <li>5 份真实导出文件可稳定复算为 159 篇唯一文献</li>
                <li>结构化分类结果 159 / 159 成功进入下游</li>
              </ul>
            </div>
            <div>
              <span className="boundary-icon boundary-icon-caution"><ShieldCheck aria-hidden="true" /></span>
              <h3>当前不声称</h3>
              <ul>
                <li>没有人工金标集，因此不声称 85% 分类准确率</li>
                <li>没有计时实验，因此不声称 2 小时缩短至 5 分钟</li>
                <li>迁移逻辑已抽象，但尚未完成跨领域实测</li>
              </ul>
            </div>
          </div>
        </section>
      </main>

      <footer className="footer section">
        <div><span className="brand-mark" aria-hidden="true">LT</span><strong>Literature Triage Evidence</strong></div>
        <p>个人产品 · 2026.05 · 数据口径与源码保持一致</p>
        <a href="https://github.com/curious-leila/literature-tracker" target="_blank" rel="noreferrer">审阅源码 <ArrowUpRight size={15} aria-hidden="true" /></a>
      </footer>
    </Tooltip.Provider>
  );
}

export default App;
