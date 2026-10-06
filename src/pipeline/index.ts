// Orquestra o pipeline: entrada (texto ou link) → filtro de opinião → ML.
// A interface chama screenInput e só envia para sendToMl o que for
// "accepted", garantindo que apenas notícias cheguem à ML.

import { parseInput } from "./input";
import { classifyContent, type Signal } from "./opinionFilter";
import type { MlRequest } from "./mlClient";

export type ScreeningResult =
  | { status: "invalid"; message: string }
  | { status: "opinion"; signals: Signal[] }
  | { status: "accepted"; request: MlRequest };

export function screenInput(raw: string): ScreeningResult {
  const parsed = parseInput(raw);
  if (parsed.kind === "invalid") {
    return { status: "invalid", message: parsed.message };
  }
  const classification = classifyContent(parsed);
  if (classification.type === "opinion") {
    return { status: "opinion", signals: classification.signals };
  }
  return {
    status: "accepted",
    request: {
      type: parsed.kind,
      content: parsed.kind === "url" ? parsed.url.href : parsed.text,
    },
  };
}

export { sendToMl } from "./mlClient";
export type { Signal } from "./opinionFilter";
