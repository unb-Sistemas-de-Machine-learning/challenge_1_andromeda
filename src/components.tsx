import { ArrowUpRight, BookOpen } from "lucide-react";
import type { Source } from "./analysis";

export function DemoBadge() {
  return (
    <span className="demo-badge">
      <span aria-hidden="true" /> Demonstração — análise simulada
    </span>
  );
}

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) {
    return (
      <p>
        Nenhuma fonte disponível no acervo demonstrativo para essa afirmação.
        Não houve pesquisa na internet.
      </p>
    );
  }
  return (
    <>
      <p className="source-note">
        Materiais fictícios criados para este protótipo.
      </p>
      <ul className="sources">
        {sources.map((source) => (
          <li key={source.href}>
            <a href={source.href} target="_blank" rel="noreferrer">
              <BookOpen size={23} aria-hidden="true" />
              <span>
                <strong>{source.title}</strong>
                <span>{source.institution}</span>
                <span>{source.date} · Abre em nova aba</span>
              </span>
              <ArrowUpRight size={20} aria-hidden="true" />
            </a>
          </li>
        ))}
      </ul>
    </>
  );
}
