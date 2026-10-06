import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  CheckCheck,
  CircleHelp,
  ClipboardPaste,
  Info,
  RotateCcw,
  Search,
  TriangleAlert,
} from "lucide-react";
import { analyzeNews, examples, type Analysis, type Outcome } from "./analysis";
import { SourceList } from "./components";

type Stage = "input" | "loading" | "result" | "error";
const labels: Record<Outcome, string> = {
  supported: "Informação sustentada",
  context: "Informação sem contexto",
  insufficient: "Evidências insuficientes",
};

export default function App() {
  const [stage, setStage] = useState<Stage>("input");
  const [input, setInput] = useState("");
  const [emptyError, setEmptyError] = useState(false);
  const [result, setResult] = useState<Analysis | null>(null);
  const [simulateFailure, setSimulateFailure] = useState(false);
  const [exampleMessage, setExampleMessage] = useState("");
  const textRef = useRef<HTMLTextAreaElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);

useEffect(() => {
  if (stage === "result" || stage === "error") {
    headingRef.current?.focus({ preventScroll: true });
    window.scrollTo({ top: 0 });
  }
}, [stage]);

  function fillExample(outcome: Outcome) {
    setInput(examples[outcome]);
    setEmptyError(false);
    setExampleMessage(
      "Exemplo fictício preenchido. Selecione “Verificar notícia” para continuar.",
    );
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
    setExampleMessage("");
    requestAnimationFrame(() => textRef.current?.focus());
  }

  return (
    <>
      <a className="skip-link" href="#main">
        Ir para o conteúdo
      </a>
      <header className="site-header">
        <div className="header-inner">
          <a
            className="brand"
            href="/"
            aria-label="Antes de compartilhar — início"
          >
            <span className="brand-icon">
              <CheckCheck size={29} />
            </span>
            <span>
              antes de
              <br />
              <strong>compartilhar</strong>
            </span>
          </a>
          <nav aria-label="Navegação principal">
            <a href="#como-usar">
              <CircleHelp size={21} />
              Como Usar?
            </a>
          </nav>
        </div>
      </header>

      <main id="main" className="page">
        <div className="intro">
          <h1>
            Recebeu uma notícia
            <br className="desktop-break" /> e ficou em dúvida?
          </h1>
        </div>
        <div className="workspace">
          <section className="main-card" aria-label="Verificação de notícia">
            <div
              role="status"
              className={stage === "loading" ? "loading-state" : "sr-only"}
              aria-live="polite"
            >
              {stage === "loading" && (
                <>
                  <span className="loading-symbol" aria-hidden="true">
                    <Search size={34} />
                  </span>
                  <p className="loading-title">
                    Estamos buscando informações sobre essa notícia.
                  </p>
                  <p>
                    Esta é uma simulação. Nenhuma pesquisa real está sendo
                    feita.
                  </p>
                  <span className="loading-dots" aria-hidden="true">
                    •••
                  </span>
                </>
              )}
            </div>

            {(stage === "input" || stage === "error") && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  void submit();
                }}
                noValidate
              >
                {stage === "error" && (
                  <div className="error-panel" role="alert">
                    <TriangleAlert size={24} />
                    <div>
                      <h2 ref={headingRef} tabIndex={-1}>
                        Não foi possível concluir a verificação.
                      </h2>
                      <p>Seu texto foi mantido. Tente novamente.</p>
                    </div>
                  </div>
                )}
                <label className="input-label" htmlFor="news">
                  Cole aqui o texto ou o link da notícia
                </label>
                <p className="field-hint" id="input-help">
                  Pode ser uma mensagem que você recebeu ou o endereço de uma
                  notícia.
                </p>
                <textarea
                  ref={textRef}
                  id="news"
                  rows={6}
                  value={input}
                  onChange={(event) => {
                    setInput(event.target.value);
                    setEmptyError(false);
                    setExampleMessage("");
                  }}
                  placeholder="Cole a notícia aqui…"
                  aria-describedby={`input-help${emptyError ? " empty-error" : ""}`}
                  aria-invalid={emptyError}
                />

                {emptyError && (
                  <p className="field-error" id="empty-error" role="alert">
                    Cole o texto ou o link da notícia para continuar.
                  </p>
                )}
                <button className="button primary" type="submit">
                  {stage === "error" ? (
                    <RotateCcw size={24} />
                  ) : (
                    <Search size={24} />
                  )}
                  {stage === "error" ? "Tentar novamente" : "Verificar notícia"}
                </button>
                <p className="sr-only" role="status">
                  {exampleMessage}
                </p>
                <div className="example-options">
                  <p>Quer ver como funciona? Toque em um exemplo:</p>
                  <div>
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
                </div>
              </form>
            )}

           {stage === "result" && result && (
  <div className={`result result-${result.outcome}`}>
    
    <div className="result-status">
      {result.outcome === "supported" ? (
        <Check size={38} />
      ) : result.outcome === "context" ? (
        <TriangleAlert size={38} />
      ) : (
        <CircleHelp size={38} />
      )}
      <span>{labels[result.outcome]}</span>
    </div>
    <section>
       <div className="claim">
      <h3>Notícia que você enviou</h3>
      <p>{result.claim}</p>
    </div>
    </section>
    <section>
      <h2 ref={headingRef} tabIndex={-1}>
        1. O que encontramos
      </h2>
      <p >{result.title}</p>
    </section>
    <section>
      <h2>2. Por que chegamos a esse resultado</h2>
      {result.explanation.map((text) => (
        <p key={text}>{text}</p>
      ))}
    </section>
    <section>
      <h2>3. Fontes para conferir</h2>
      <SourceList sources={result.sources} />
    </section>

    <section>
      <h2>4. Próximo passo</h2>
      <p>{result.next}</p>
    </section>
   
    <p className="result-warning">
      <Info size={23} />
      Esta análise pode conter erros. Confira as fontes antes de compartilhar.
    </p>
    <button className="button primary" onClick={reset}>
      <RotateCcw size={21} />
      Verificar outra notícia
    </button>
  </div>
)}
          </section>
          <section id="como-usar" className="help">
            <div>
              <span className="help-icon">
                <ClipboardPaste size={25} />
              </span>
              <h2>Como usar</h2>
              <p>
                Você pode conferir com calma,
                <br />
                um passo de cada vez.
              </p>
            </div>
            <ol>
              <li>
                <strong>Copie o Conteúdo.</strong> No celular, toque e segure o
                texto ou link e escolha “Copiar”.  <br /> No computador, selecione o
                conteúdo e aperte Ctrl + C.
              </li>
              <li>
                <strong>Cole no Campo da Notícia.</strong> No celular, toque e segure o
                campo e escolha “Colar”. <br /> No computador, clique no campo e aperte Ctrl + V .
              </li>
              <li>
                <strong>Selecione “Verificar Notícia”.</strong> Leia a
                explicação e abra as fontes. Para só testar, toque em um dos
                exemplos.
              </li>
            </ol>
          </section>
        </div>
      </main>
      <footer>
        <div>
          <span className="footer-brand">
            <CheckCheck size={21} /> antes de compartilhar
          </span>
          <span>Mais contexto. Mais cuidado ao compartilhar.</span>
          <span>Protótipo · 2026</span>
        </div>
      </footer>
    </>
  );
}