import { useEffect, useRef, useState, type FormEvent } from "react";
import { ArrowLeft, ArrowRight, ExternalLink, Search, ShieldCheck } from "lucide-react";
import { analyzeLocally, searchNewsByTitle, type LocalAnalysis, type ArticleCandidate } from "./pipeline/localAnalysis";
import { screenInput } from "./pipeline";
import { classifyContent } from "./pipeline/opinionFilter";

type Mode = "title" | "url";
type Stage = "entry" | "searching" | "choices" | "analyzing" | "result";

function isOpinionTitle(title: string): boolean {
  return classifyContent({ kind: "text", text: title, raw: title }).type === "opinion";
}

export default function App() {
  const [mode, setMode] = useState<Mode>("title");
  const [stage, setStage] = useState<Stage>("entry");
  const [value, setValue] = useState("");
  const [candidates, setCandidates] = useState<ArticleCandidate[]>([]);
  const [selected, setSelected] = useState<ArticleCandidate | null>(null);
  const [result, setResult] = useState<LocalAnalysis | null>(null);
  const [message, setMessage] = useState("");
  const heading = useRef<HTMLHeadingElement>(null);

  useEffect(() => { if (stage !== "entry" || message) heading.current?.focus(); }, [stage, message]);

  function reset() {
    setStage("entry"); setValue(""); setCandidates([]); setSelected(null);
    setResult(null); setMessage("");
  }

  function onMode(next: Mode) { reset(); setMode(next); }

  async function search() {
    const title = value.trim();
    if (title.length < 12 || title.length > 180 || title.split(/\s+/).length < 3) {
      setMessage("Digite pelo menos três palavras do título, com 12 a 180 caracteres."); return;
    }
    if (isOpinionTitle(title)) {
      setMessage("Esse título parece ser de opinião ou editorial. Procure uma reportagem factual para analisar."); return;
    }
    setMessage(""); setStage("searching");
    try {
      const found = (await searchNewsByTitle(title)).filter((candidate) => {
        const screened = screenInput(candidate.url);
        return screened.status === "accepted" && !isOpinionTitle(candidate.title);
      });
      setCandidates(found); setStage("choices");
      if (!found.length) setMessage("Nenhuma reportagem correspondente foi encontrada. Tente outro título ou cole o link.");
    } catch (error) { setStage("entry"); setMessage(error instanceof Error ? error.message : "Não foi possível buscar notícias."); }
  }

  async function analyze(candidate: ArticleCandidate) {
    const screened = screenInput(candidate.url);
    if (screened.status !== "accepted" || isOpinionTitle(candidate.title)) {
      setMessage("Este link parece ser de opinião, coluna ou editorial e não será avaliado como notícia."); return;
    }
    setSelected(candidate); setMessage(""); setStage("analyzing");
    try { setResult(await analyzeLocally(screened.request.content)); setStage("result"); }
    catch (error) { setStage(mode === "title" ? "choices" : "entry"); setMessage(error instanceof Error ? error.message : "Não foi possível analisar a notícia."); }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "title") { void search(); return; }
    const screened = screenInput(value);
    if (screened.status === "invalid") { setMessage(screened.message); return; }
    if (screened.status === "opinion") {
      setMessage("Este link aponta para opinião, coluna ou editorial e não será avaliado como notícia."); return;
    }
    if (screened.request.type !== "url") { setMessage("Cole o link completo da reportagem para continuar."); return; }
    void analyze({ title: "Notícia informada por link", url: screened.request.content, publisher: new URL(screened.request.content).hostname });
  }

  return <main className="app-shell">
    <header className="app-header"><ShieldCheck aria-hidden="true"/><span>Antes de compartilhar</span></header>
    <div className="app-content">
      {stage === "entry" && <>
        <div className="intro-mobile"><p className="eyebrow-mobile">VERIFIQUE COM CALMA</p><h1 ref={heading} tabIndex={-1}>Qual notícia você leu?</h1><p>Encontre a reportagem pelo título ou use o link que você já tem.</p></div>
        <div className="mode-switch" role="group" aria-label="Forma de encontrar a notícia">
          <button type="button" aria-pressed={mode === "title"} onClick={() => onMode("title")}>Tenho o título</button>
          <button type="button" aria-pressed={mode === "url"} onClick={() => onMode("url")}>Tenho o link</button>
        </div>
        <form onSubmit={submit} className="entry-form">
          <label htmlFor="news-input">{mode === "title" ? "Título da notícia" : "Link da reportagem"}</label>
          <input id="news-input" value={value} onChange={(event) => { setValue(event.target.value); setMessage(""); }}
            placeholder={mode === "title" ? "Digite o título que você lembra" : "https://site.com.br/noticia"}
            type="text" inputMode={mode === "url" ? "url" : "text"} autoComplete="off" aria-invalid={!!message} aria-describedby={message ? "feedback" : undefined}/>
          <button className="primary-action" type="submit"><Search size={20} aria-hidden="true"/>{mode === "title" ? "Buscar notícia" : "Analisar notícia"}<ArrowRight size={20} aria-hidden="true"/></button>
        </form>
      </>}
      {stage === "searching" && <section className="state-card" role="status"><Search size={32} aria-hidden="true"/><h1 ref={heading} tabIndex={-1}>Buscando reportagens</h1><p>Estamos procurando notícias com esse título.</p></section>}
      {stage === "choices" && <section className="choice-screen">
        <button className="back-action" onClick={() => { setStage("entry"); setMessage(""); }}><ArrowLeft size={18}/>Voltar à busca</button>
        <h1 ref={heading} tabIndex={-1}>Escolha a reportagem</h1><p>Confirme o título e o veículo antes de analisar. A busca não confirma os fatos.</p>
        <div className="choices">{candidates.map((candidate) => <button className="choice" key={candidate.url} onClick={() => void analyze(candidate)}><strong>{candidate.title}</strong><span>{candidate.publisher}<ArrowRight size={18} aria-hidden="true"/></span></button>)}</div>
      </section>}
      {stage === "analyzing" && <section className="state-card" role="status"><ShieldCheck size={32} aria-hidden="true"/><h1 ref={heading} tabIndex={-1}>Analisando a notícia</h1><p>Isso pode levar alguns instantes.</p></section>}
      {stage === "result" && result && <section className="result-screen">
        <p className="eyebrow-mobile">RESULTADO DA ANÁLISE</p><h1 ref={heading} tabIndex={-1}>O que encontramos</h1>
        <p className="article-name">{result.article?.title || selected?.title}</p>
        <div className="explanation" role="status"><ShieldCheck size={26} aria-hidden="true"/><p>{result.explanation.text}</p></div>
        {selected && <a className="article-link" href={result.article?.final_url || selected.url} target="_blank" rel="noopener noreferrer">Abrir reportagem original <ExternalLink size={18} aria-hidden="true"/></a>}
        <button className="primary-action" onClick={reset}>Analisar outra notícia <ArrowRight size={20} aria-hidden="true"/></button>
      </section>}
      {message && <p className="feedback" id="feedback" role="alert">{message}</p>}
      <p className="scope-note">A avaliação pode ser parcial e não substitui a leitura das fontes. Artigos de opinião não recebem veredito factual.</p>
    </div>
  </main>;
}
