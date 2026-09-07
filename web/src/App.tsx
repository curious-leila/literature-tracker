import { useEffect, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { ArrowUpRight, CheckCircle2, Database, FileInput, Mail, SearchCheck } from "lucide-react";
import type { RunSummary } from "./types";

const steps = [
  [FileInput, "双源导入"],
  [SearchCheck, "统一解析"],
  [Database, "历史去重"],
  [CheckCircle2, "LLM甄选"],
  [Mail, "简报交付"],
] as const;

function App() {
  const [data, setData] = useState<RunSummary | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(import.meta.env.BASE_URL + "run-summary.json")
      .then((response) => {
        if (!response.ok) throw new Error("Evidence unavailable");
        return response.json();
      })
      .then(setData)
      .catch(() => setError(true));
  }, []);

  if (error) {
    return <main className="state-message">证据文件加载失败，请稍后重试。</main>;
  }

  if (!data) {
    return <main className="state-message">正在校验 Recorded Run…</main>;
  }

  return (
    <>
      <header className="topbar">
        <a className="brand" href="#top">LT / EVIDENCE</a>
        <nav aria-label="主导航">
          <a href="#workflow">工作流</a>
          <a href="#cases">案例</a>
          <a href="#iterations">Prompt迭代</a>
          <a href="https://github.com/curious-leila/literature-tracker" target="_blank" rel="noreferrer">
            GitHub <ArrowUpRight size={16} aria-hidden="true" />
          </a>
        </nav>
      </header>

      <main id="top">
        <section className="hero section">
          <p className="eyebrow">RECORDED RUN · 2026.05</p>
          <h1>从 {data.summary.raw_records} 条检索结果，到可行动的文献简报。</h1>
          <p>人工导出后，解析、去重、语义分层与邮件交付由工作流自动完成。</p>
        </section>

        <section className="metrics section" aria-label="核心指标">
          <article><strong>{data.summary.input_files}</strong><span>份导出文件</span></article>
          <article><strong>{data.summary.raw_records}</strong><span>条原始记录</span></article>
          <article><strong>{data.summary.unique_papers}</strong><span>篇唯一文献</span></article>
          <article><strong>{data.summary.links.reachable_total}</strong><span>篇可直达</span></article>
        </section>

        <section className="section" id="workflow">
          <h2>工作流</h2>
          <div className="steps">
            {steps.map(([Icon, label]) => (
              <article key={label}><Icon aria-hidden="true" /><span>{label}</span></article>
            ))}
          </div>
        </section>

        <section className="section" id="cases">
          <h2>案例回放</h2>
          <Tabs.Root defaultValue="0">
            <Tabs.List aria-label="选择案例">
              {data.cases.map((item, index) => (
                <Tabs.Trigger key={item.id} value={String(index)}>{item.relevance.toUpperCase()}</Tabs.Trigger>
              ))}
            </Tabs.List>
            {data.cases.map((item, index) => (
              <Tabs.Content key={item.id} value={String(index)}>
                <h3>{item.title}</h3>
                <p>{item.reason}</p>
                <strong>{item.suggestion}</strong>
              </Tabs.Content>
            ))}
          </Tabs.Root>
        </section>

        <section className="section" id="iterations">
          <h2>Prompt 迭代</h2>
          <div className="timeline">
            {data.prompt_milestones.map((item) => (
              <article key={item.version}>
                <strong>{item.version}</strong><h3>{item.change}</h3><p>{item.result}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}

export default App;
