/**
 * Local BERTimbau adapter.
 *
 * The quantized ONNX artifact and tokenizer are shipped under
 * /models/writing_bertimbau. The runtime is loaded lazily so the app can still
 * explain a partial result on devices where the optional ONNX bridge is not
 * available. No text is sent to a server by this module.
 */
export type WritingResult = { available: boolean; score: number | null; label: string | null };

let classifier: ((text: string) => Promise<unknown>) | null | undefined;

async function loadClassifier() {
  if (classifier !== undefined) return classifier;
  try {
    const packageName = "@huggingface/transformers";
    const runtime = await import(/* @vite-ignore */ packageName) as {
      pipeline: (task: string, model: string, options?: Record<string, unknown>) => Promise<(text: string) => Promise<unknown>>;
    };
    classifier = await runtime.pipeline("text-classification", "/models/writing_bertimbau", {
      local_files_only: true,
      model_file_name: "model.int8.onnx",
    });
  } catch {
    classifier = null;
  }
  return classifier;
}

export async function classifyWriting(text: string): Promise<WritingResult> {
  const run = await loadClassifier();
  if (!run) return { available: false, score: null, label: null };
  try {
    const output = await run(text.slice(0, 20_000));
    const first = Array.isArray(output) ? output[0] as { label?: string; score?: number } : output as { label?: string; score?: number };
    return { available: typeof first?.score === "number", score: first?.score ?? null, label: first?.label ?? null };
  } catch {
    return { available: false, score: null, label: null };
  }
}
