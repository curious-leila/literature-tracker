import { useEffect, useState } from "react";
import {
  ArrowRight,
  ArrowUp,
  ArrowUpRight,
  Braces,
  Check,
  Code2,
  Database,
  FileInput,
  Link2,
  Mail,
  SearchCheck,
  ShieldCheck,
} from "lucide-react";
import type { RunSummary } from "./types";

const GITHUB_URL = "https://github.com/curious-leila/literature-tracker";

const workflowSteps = [
  { icon: FileInput, label: "双源解析", detail: "识别知网 RefWorks 与 WOS RIS，统一为同一种文献记录。" },
  { icon: Database, label: "历史去重", detail: "基于标题指纹，跨文件、跨批次识别重复文献。" },
  { icon: SearchCheck, label: "LLM 语义分层", detail: "按研究问题分为三档，并为每条结果保留判断理由。" },
  { icon: Braces, label: "简报生成", detail: "整理阅读优先级、研究交叉点、建议和原文入口。" },
  { icon: Mail, label: "邮件送达", detail: "SMTP 发送成功后才更新状态，失败记录可以继续重试。" },
] as const;

function App() {
  const [data, setData] = useState<RunSummary | null>(null);
  const [error, setError] = useState(false);
  const [activeSection, setActiveSection] = useState("top");

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}run-summary.json`)
      .then((response) => {
        if (!response.ok) throw new Error("Evidence unavailable");
        return response.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  useEffect(() => {
    if (!data) return;
    const header = document.querySelector<HTMLElement>(".topbar");
    const updateOffset = () => {
      document.documentElement.style.setProperty("--nav-offset", `${(header?.offsetHeight ?? 64) + 20}px`);

    };
    updateOffset();
    const resizeObserver = new ResizeObserver(updateOffset);
    if (header) resizeObserver.observe(header);
    const main = document.getElementById("main-content");
    if (main) resizeObserver.observe(main);
    window.addEventListener("resize", updateOffset);

    // The JSON arrives after the browser's initial fragment navigation.
    // Reapply that fragment only once the destination exists.
    const restoreFragment = () => {
      const id = window.location.hash.slice(1);
      if (id) document.getElementById(id)?.scrollIntoView({ behavior: "instant", block: "start" });
    };
    const frame = requestAnimationFrame(restoreFragment);
    window.addEventListener("hashchange", updateActive);
    window.addEventListener("scroll", updateActive, { passive: true });
    function updateActive() {
      const offset = (header?.offsetHeight ?? 64) + 40;
      const sections = [...document.querySelectorAll<HTMLElement>("main > [id]")];
      const current = sections.filter((section) => section.getBoundingClientRect().top <= offset).at(-1);
      setActiveSection(current?.id ?? "top");
    }
    updateActive();
    return () => {
      cancelAnimationFrame(frame);
      resizeObserver.disconnect();
      window.removeEventListener("resize", updateOffset);
      window.removeEventListener("hashchange", updateActive);
      window.removeEventListener("scroll", updateActive);
      document.documentElement.style.removeProperty("--nav-offset");
    };
  }, [data]);

  if (error) {
    return (
      <main className="state-message">
        <ShieldCheck aria-hidden="true" />
        <h1>证据文件加载失败</h1>
        <p>请稍后重试，或前往 GitHub 查看运行记录。</p>
        <a className="button button-primary" href={GITHUB_URL}>审阅 GitHub</a>
      </main>
    );
  }

  if (!data) {
    return <main className="state-message" aria-live="polite">正在加载真实运行记录…</main>;
  }

  const featuredCase = data.cases.find((item) => item.relevance === "high") ?? data.cases[0];
  const emailImage = `${import.meta.env.BASE_URL}evidence/email-delivery-proof.png`;
  const fullRunRecord = `${import.meta.env.BASE_URL}run-summary.json`;
  const promptLog = `${GITHUB_URL}/blob/master/docs/prompt-tuning-log.md`;

  const storyMetrics = [
    { value: data.summary.input_files, label: "份导出文件" },
    { value: data.summary.raw_records, label: "条原始记录" },
    { value: data.summary.unique_papers, label: "篇去重结果" },
    { value: 1, label: "封简报送达" },
  ];

  const deliveryMetrics = [
    { value: data.summary.unique_papers, label: "完成处理", detail: "篇" },
    { value: data.summary.relevance.high, label: "优先阅读全文", detail: "篇" },
    { value: data.summary.relevance.medium, label: "浏览摘要", detail: "篇" },
    { value: data.summary.relevance.low, label: "背景参考", detail: "篇" },
    { value: data.summary.links.reachable_total, label: "保留原文入口", detail: "篇" },
  ];

  return (
    <>
      <a className="skip-link" href="#main-content">跳到主要内容</a>

      <header className="topbar">
        <a className="brand" href="#top" aria-label="返回页面顶部">
          <span>Literature Workflow</span>
        </a>
        <nav aria-label="主导航">
          <a href="#delivery" aria-current={activeSection === "delivery" ? "location" : undefined}>邮件证据</a>
          <a href="#workflow" aria-current={activeSection === "workflow" ? "location" : undefined}>工作流</a>
          <a href="#case" aria-current={activeSection === "case" ? "location" : undefined}>判断案例</a>
          <a className="nav-github" href={GITHUB_URL} target="_blank" rel="noreferrer">
            <Code2 size={16} aria-hidden="true" />
            GitHub
            <ArrowUpRight size={14} aria-hidden="true" />
          </a>
        </nav>
      </header>

      <main id="main-content">
        <section className="hero section" id="top">
          <div className="hero-copy">
            <p className="project-name">文献AI筛选与邮件简报工作流</p>
            <p className="eyebrow"><span aria-hidden="true" /> 真实运行 · 2026.05 · Qwen2.5-32B</p>
            <h1>把跨平台检索结果，<br className="desktop-break" />变成可行动的文献简报。</h1>
            <p className="hero-lead">导入知网与 WOS 检索文件后，自动完成解析、历史去重、LLM 分层和邮件推送。</p>
            <div className="hero-actions">
              <a className="button button-primary" href="#delivery">
                查看邮件交付 <ArrowRight size={17} aria-hidden="true" />
              </a>
            </div>
          </div>

          <figure className="hero-email">
            <a href={emailImage} target="_blank" rel="noreferrer" aria-label="打开首屏邮件证据原图">
              <img src={emailImage} width="846" height="1860" alt="真实送达的文献邮件简报" />
              <span>真实交付 · 查看原图 <ArrowUpRight size={14} aria-hidden="true" /></span>
            </a>
          </figure>
          <ol className="story-chain" aria-label="一次真实运行的数据链路">
            {storyMetrics.map((metric, index) => (
              <li key={metric.label}>
                <div><strong>{metric.value}</strong><span>{metric.label}</span></div>
                {index < storyMetrics.length - 1 && <ArrowRight aria-hidden="true" />}
              </li>
            ))}
          </ol>
          <p className="hero-boundary"><ShieldCheck size={16} aria-hidden="true" /> 自动化从文件导入开始，源站检索与导出仍由人完成。</p>
        </section>

        <section className="section delivery-section" id="delivery" aria-labelledby="delivery-title">
          <div className="section-heading compact-heading">
            <p className="eyebrow">01 / 邮件交付证据</p>
            <h2 id="delivery-title">结果不只停在脚本里，而是成为可直接阅读的邮件简报。</h2>
            <p>同一批运行结果按阅读动作分层，保留判断理由、研究交叉点和原文入口。</p>
          </div>

          <div className="delivery-layout">
            <div className="delivery-summary">
              <div className="delivery-status"><Check size={16} aria-hidden="true" /> 已真实送达</div>
              <dl className="delivery-metrics">
                {deliveryMetrics.map((metric) => (
                  <div key={metric.label}>
                    <dt>{metric.label}</dt>
                    <dd><strong>{metric.value}</strong><span>{metric.detail}</span></dd>
                  </div>
                ))}
              </dl>
              <p className="delivery-note">
                <Link2 size={17} aria-hidden="true" />
                其中 {data.summary.links.reachable_total} 篇保留可访问的原文或 DOI 入口，便于收到邮件后直接复核。
              </p>
            </div>

            <figure className="email-proof">
              <a href={emailImage} target="_blank" rel="noreferrer" aria-label="打开完整尺寸的邮件交付截图">
                <img
                  src={emailImage}
                  alt="手机邮箱中的文献简报，显示本次处理159篇、优先阅读全文12篇、浏览摘要61篇、背景参考86篇"
                  width="846"
                  height="1860"
                  loading="lazy"
                  decoding="async"
                />
                <span>查看原尺寸 <ArrowUpRight size={15} aria-hidden="true" /></span>
              </a>
              <figcaption>2026.05 真实运行记录，于 2026.09 复现发送；仅对账号尾号进行隐私遮挡。</figcaption>
            </figure>
          </div>
        </section>

        <section className="section workflow-section" id="workflow" aria-labelledby="workflow-title">
          <div className="section-heading">
            <p className="eyebrow">02 / 核心工作流</p>
            <h2 id="workflow-title">从导入文件到收到简报，五步完成。</h2>
            <p>人负责检索策略和源站导出；系统负责文件进入后的重复劳动。</p>
          </div>

          <div className="workflow-boundary">
            <div><span>人工输入</span><strong>知网 / WOS 检索与导出</strong></div>
            <ArrowRight aria-hidden="true" />
            <div><span>自动化起点</span><strong>文件导入项目目录</strong></div>
          </div>

          <ol className="workflow-steps">
            {workflowSteps.map(({ icon: Icon, label, detail }, index) => (
              <li key={label}>
                <span className="step-index">0{index + 1}</span>
                <Icon aria-hidden="true" />
                <h3>{label}</h3>
                <p>{detail}</p>
              </li>
            ))}
          </ol>
        </section>

        <div className="closing-chapter section" id="case">
        {featuredCase && (
          <section className="case-section" aria-labelledby="case-title">
            <div className="section-heading case-heading">
              <p className="eyebrow">03 / 一个判断案例</p>
              <h2 id="case-title">不是只看关键词，而是输出“为什么相关”和“下一步做什么”。</h2>
            </div>

            <article className="case-card">
              <div className="case-meta">
                <span className="evidence-badge"><span aria-hidden="true" /> 高度相关</span>
                <span>{featuredCase.source}{featuredCase.journal_tier ? ` · ${featuredCase.journal_tier}` : ""}{featuredCase.year ? ` · ${featuredCase.year}` : ""}</span>
              </div>
              <h3>《{featuredCase.title}》</h3>
              <div className="case-reasoning">
                <div><span>判定理由</span><p>{featuredCase.reason}</p></div>
                <div><span>研究交叉点</span><p>{featuredCase.cross_point}</p></div>
                <div className="case-action"><span>建议动作</span><strong>{featuredCase.suggestion}</strong></div>
              </div>
            </article>
          </section>
        )}

        <section className="proof-section" id="boundary" aria-labelledby="proof-title">
          <div className="proof-copy">
            <p className="eyebrow">04 / 证据原则</p>
            <h2 id="proof-title">只展示可以核验的事实。</h2>
            <p>页面仅展示可由运行记录、邮件截图或源码核验的事实，不填充或包装未经验证的数据。</p>
          </div>
          <nav className="proof-links" aria-label="深度证据入口">
            <a href={fullRunRecord} target="_blank" rel="noreferrer">
              <span>完整运行记录<small>159 条结构化结果</small></span>
              <ArrowUpRight aria-hidden="true" />
            </a>
            <a href={promptLog} target="_blank" rel="noreferrer">
              <span>Prompt 迭代记录<small>查看 8 轮调整过程</small></span>
              <ArrowUpRight aria-hidden="true" />
            </a>
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              <span>GitHub 源码<small>审阅解析、去重与推送实现</small></span>
              <ArrowUpRight aria-hidden="true" />
            </a>
          </nav>
        </section>
      <footer className="footer">
        <div><strong>Literature Workflow</strong></div>
        <p>个人产品 · 2026.05 · 数据口径与源码保持一致</p>
        <a href={GITHUB_URL} target="_blank" rel="noreferrer">审阅源码 <ArrowUpRight size={15} aria-hidden="true" /></a>
      </footer>
        </div>
      </main>
      {activeSection !== "top" && <a className="back-to-top" href="#top" aria-label="回到顶部">
        <ArrowUp size={17} aria-hidden="true" /><span>回到顶部</span>
      </a>}
    </>
  );
}

export default App;
