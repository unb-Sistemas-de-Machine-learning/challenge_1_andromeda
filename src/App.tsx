import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ArrowUpRight,
  Check,
  CheckCheck,
  CircleHelp,
  ClipboardPaste,
  Info,
  Link,
  RotateCcw,
  Search,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";
import { analyzeNews, examples, type Analysis, type Outcome } from "./analysis";
import { DemoBadge, SourceList } from "./components";

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
    if (stage === "result" || stage === "error") headingRef.current?.focus();
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
              Como usar
            </a>
            <span className="prototype">Protótipo exploratório</span>
          </nav>
        </div>
      </header>

      <main id="main" className="page">
        <div className="eyebrow">
          <span /> INFORMAÇÃO COM MAIS CUIDADO
        </div>
        <div className="intro">
          <h1>
            Recebeu uma notícia
            <br className="desktop-break" /> e ficou em dúvida?
          </h1>
          <p>Confira as informações antes de compartilhar.</p>
        </div>
        <div className="workspace">
          <section className="main-card" aria-label="Verificação de notícia">
            <div className="card-top">
              <DemoBadge />
              <span className="card-mark" aria-hidden="true">
                <ShieldCheck size={24} />
              </span>
            </div>
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
                  aria-describedby={`input-help input-note${emptyError ? " empty-error" : ""}`}
                  aria-invalid={emptyError}
                />
                <div className="input-note" id="input-note">
                  <Link size={17} aria-hidden="true" />
                  <span>
                    Aceita texto ou link. Neste protótipo, links não são
                    acessados.
                  </span>
                </div>
                {emptyError && (
                  <p className="field-error" id="empty-error" role="alert">
                    Cole o texto ou o link da notícia para continuar.
                  </p>
                )}
                <div className="form-actions">
                  <button className="button primary" type="submit">
                    {stage === "error" ? (
                      <RotateCcw size={21} />
                    ) : (
                      <Search size={21} />
                    )}
                    {stage === "error"
                      ? "Tentar novamente"
                      : "Verificar notícia"}
                    <ArrowRight className="button-arrow" size={21} />
                  </button>
                  <button
                    className="button secondary"
                    type="button"
                    onClick={() => fillExample("supported")}
                  >
                    Ver um exemplo
                  </button>
                </div>
                <p className="sr-only" role="status">
                  {exampleMessage}
                </p>
                <div className="example-options">
                  <p>Explore os resultados com exemplos fictícios:</p>
                  <div>
                    {(Object.keys(labels) as Outcome[]).map((key) => (
                      <button
                        type="button"
                        key={key}
                        onClick={() => fillExample(key)}
                      >
                        {labels[key]}
                        <ArrowUpRight size={16} />
                      </button>
                    ))}
                  </div>
                </div>
                <details className="test-controls">
                  <summary>Testar uma falha de verificação</summary>
                  <label>
                    <input
                      type="checkbox"
                      checked={simulateFailure}
                      onChange={(event) =>
                        setSimulateFailure(event.target.checked)
                      }
                    />
                    Simular falha no próximo envio
                  </label>
                  <p>Seu conteúdo será mantido para tentar novamente.</p>
                </details>
              </form>
            )}

            {stage === "result" && result && (
              <div className={`result result-${result.outcome}`}>
                <div className="result-status">
                  {result.outcome === "supported" ? (
                    <Check size={22} />
                  ) : result.outcome === "context" ? (
                    <TriangleAlert size={22} />
                  ) : (
                    <CircleHelp size={22} />
                  )}
                  {labels[result.outcome]}
                </div>
                <section>
                  <h2 ref={headingRef} tabIndex={-1}>
                    O que encontramos
                  </h2>
                  <p className="result-title">{result.title}</p>
                  <div className="claim">
                    <h3>Afirmação analisada</h3>
                    <p>{result.claim}</p>
                  </div>
                  <p className="simulation-note">
                    Resultado de demonstração, baseado apenas no acervo
                    fictício. Não é uma avaliação real do conteúdo enviado.
                  </p>
                </section>
                <section>
                  <h2>Por que chegamos a esse resultado</h2>
                  {result.explanation.map((text) => (
                    <p key={text}>{text}</p>
                  ))}
                </section>
                <section>
                  <h2>Fontes para conferir</h2>
                  <SourceList sources={result.sources} />
                </section>
                <section className="next-step">
                  <h2>Próximo passo</h2>
                  <p>{result.next}</p>
                </section>
                <p className="result-warning">
                  <Info size={23} />
                  Esta análise pode conter erros. Confira as fontes antes de
                  compartilhar.
                </p>
                <button className="button primary" onClick={reset}>
                  <RotateCcw size={21} />
                  Verificar outra notícia
                </button>
              </div>
            )}
          </section>

          <aside className="guide" aria-label="Orientações">
            <div className="guide-illustration" aria-hidden="true">
              <div className="illustration-orbit" />
              <div className="paper">
                <span />
                <span />
                <span />
                <div className="paper-line" />
              </div>
              <div className="search-disc">
                <Search size={40} strokeWidth={1.7} />
              </div>
              <span className="mini-check">
                <Check size={19} />
              </span>
            </div>
            <h2>
              Uma pausa faz
              <br />a diferença.
            </h2>
            <p>
              Antes de passar uma notícia adiante, confira o que está por trás
              da informação.
            </p>
            <ol className="steps">
              <li>
                <span>1</span>
                <div>
                  <strong>Cole a notícia.</strong>
                  <p>Um texto ou um link já é um começo.</p>
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  <strong>Solicite a verificação.</strong>
                  <p>Vamos organizar as informações para você.</p>
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  <strong>Leia o resultado e confira as fontes.</strong>
                  <p>Decida com mais informação.</p>
                </div>
              </li>
            </ol>
            <div className="guide-note">
              <Info size={21} />
              <p>Conferir é um cuidado com você e com quem recebe a notícia.</p>
            </div>
          </aside>
        </div>

        <div className="bottom-note">
          <ShieldCheck size={24} />
          <p>
            <strong>Um apoio para refletir, sem respostas absolutas.</strong>
            <span>
              Este protótipo não determina a verdade. Todas as análises são
              demonstrativas.
            </span>
          </p>
          <span className="no-signup">Sem cadastro</span>
        </div>
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
              <strong>Copie o conteúdo.</strong> No celular, toque e segure o
              texto ou link e escolha “Copiar”. No computador, selecione o
              conteúdo e use Ctrl+C (ou ⌘C).
            </li>
            <li>
              <strong>Cole no campo acima.</strong> Toque e segure o campo e
              escolha “Colar”, ou use Ctrl+V (ou ⌘V).
            </li>
            <li>
              <strong>Selecione “Verificar notícia”.</strong> Leia a explicação
              e abra as fontes. Para explorar este protótipo, use “Ver um
              exemplo”.
            </li>
          </ol>
        </section>
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
