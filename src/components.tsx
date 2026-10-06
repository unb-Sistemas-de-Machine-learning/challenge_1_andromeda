import { ArrowUpRight } from "lucide-react";
import type { Source } from "./analysis";

export function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) {
    return <p className="no-source">Não há fonte para mostrar neste exemplo.</p>;
  }
  return (
    <ul className="sources">
      {sources.map((s) => (
        <li key={s.href}>
          <a href={s.href} target="_blank" rel="noreferrer">
            <span>
              <strong>{s.title}</strong>
              <span>Abre em nova aba</span>
            </span>
            <ArrowUpRight size={24} aria-hidden="true" />
          </a>
        </li>
      ))}
    </ul>
  );
}