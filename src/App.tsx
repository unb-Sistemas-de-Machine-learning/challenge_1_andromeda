import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  CheckCheck,
  CircleHelp,
  RotateCcw,
  Search,
  TriangleAlert,
} from "lucide-react";
import { analyzeNews, examples, type Analysis, type Outcome } from "./analysis";
import { SourceList } from "./components";

type Stage = "input" | "loading" | "result" | "error";
const labels: Record<Outcome, string> = {
  supported: "Informação confirmada",
  context: "Falta contexto",
  insufficient: "Sem provas suficientes",
};
const icons = {
  supported: Check,
  context: TriangleAlert,
  insufficient: CircleHelp,
};

const testMode = new URLSearchParams(window.location.search).has("teste");

export default function App() {
  const [stage, setStage] = useState<Stage>("input");
  const [input, setInput] = useState("");
  const [emptyError, setEmptyError] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [simulateFailure, setSimulateFailure] = useState(false);
  const textRef = useRef<HTMLTextAreaElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

  useEffect(() => {
    if (stage === "result" || stage === "error") headingRef.current?.focus();
  }, [stage]);

  function fillExample(outcome: Outcome) {
    setInput(examples[outcome]);
    setEmptyError(false);
    textRef.current?.focus();
  }

  async function submit() {
    if (!input.trim()) {
      setEmptyError(true);
      textRef.current?.focus();
      return;
    }
    setEmptyError(false);
    setStage("loading");
    try {
      setResult(await analyzeNews(input, { simulateFailure }));
      setStage("result");
    } catch {
      setStage("error");
      setSimulateFailure(false);
    }
  }

  function reset() {
    setInput("");
    setResult(null);
    setStage("input");
    requestAnimationFrame(() => textRef.current?.focus());
  }

  const Icon = result ? icons[result.outcome] : Check;

  return (
    <>
      <a className="skip-link" href="#main">
        Ir para o conteúdo
      </a>
      <header className="site-header">
        <a
          className="brand"
          href="/"
          aria-label="Antes de compartilhar — início"
        >
          <CheckCheck size={30} aria-hidden="true" />
          Antes de compartilhar
        </a>
      </header>

      <main id="main" className="page">
        {stage === "loading" && (
          <div className="loading" role="status">
            <Search size={44} aria-hidden="true" />
            <p>Conferindo a notícia…</p>
          </div>
        )}

        {(stage === "input" || stage === "error") && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
            noValidate
          >
            {stage === "error" ? (
              <div className="error-panel" role="alert">
                <TriangleAlert size={28} aria-hidden="true" />
                <h2 ref={headingRef} tabIndex={-1}>
                  Não deu certo. Seu texto foi mantido. Tente de novo.
                </h2>
              </div>
            ) : (
              <h1>Recebeu uma notícia e ficou em dúvida?</h1>
            )}

            <label className="input-label" htmlFor="news">
              Cole aqui o texto ou o link
            </label>
            <textarea
              ref={textRef}
              id="news"
              rows={6}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setEmptyError(false);
              }}
              placeholder="Toque aqui e cole a notícia"
              aria-describedby={emptyError ? "empty-error" : undefined}
              aria-invalid={emptyError}
            />
            {emptyError && (
              <p className="field-error" id="empty-error" role="alert">
                Cole um texto ou link para continuar.
              </p>
            )}

            <button className="button primary" type="submit">
              {stage === "error" ? (
                <RotateCcw size={24} />
              ) : (
                <Search size={24} />
              )}
              {stage === "error" ? "Tentar de novo" : "Verificar"}
              <ArrowRight size={24} className="button-arrow" />
            </button>

            {testMode && (
              <details className="extras" open>
                <summary>Ver exemplos</summary>
                <div className="example-buttons">
                  {(Object.keys(labels) as Outcome[]).map((key) => (
                    <button
                      type="button"
                      key={key}
                      onClick={() => fillExample(key)}
                    >
                      {labels[key]}
                    </button>
                  ))}
                </div>
                <label className="failure-toggle">
                  <input
                    type="checkbox"
                    checked={simulateFailure}
                    onChange={(e) => setSimulateFailure(e.target.checked)}
                  />
                  Simular uma falha no próximo envio
                </label>
              </details>
            )}
          </form>
        )}

        {stage === "result" && result && (
          <div className={`result result-${result.outcome}`}>
            <div className="verdict">
              <Icon size={34} aria-hidden="true" />
              <h1
                ref={headingRef as React.RefObject<HTMLHeadingElement>}
                tabIndex={-1}
              >
                {labels[result.outcome]}
              </h1>
            </div>
            <p className="result-title">{result.title}</p>
            {result.explanation.map((text) => (
              <p key={text}>{text}</p>
            ))}
            <SourceList sources={result.sources} />
            <p className="next-step">
              <strong>O que fazer:</strong> {result.next}
            </p>
            <p className="result-warning">
              Esta análise pode ter erros. Confira as fontes.
            </p>
            <button className="button primary" onClick={reset}>
              <RotateCcw size={24} />
              Verificar outra notícia
            </button>
          </div>
        )}
      </main>
    </>
  );
}