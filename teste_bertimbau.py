"""Baixa e testa o classificador BERTimbau na CPU, sem alterar a API."""

import argparse

from news_analysis.config import Settings
from news_analysis.criteria.writing_style import WritingStyleClassifier
from news_analysis.pipeline.version import WRITING_MODEL_NAME


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--texto", help="Texto para testar; se omitido, solicita no terminal.")
    args = parser.parse_args()
    texto = args.texto if args.texto is not None else input("Digite o texto da notícia: ")
    if not texto.strip():
        parser.error("Informe um texto não vazio.")

    print(f"Carregando {WRITING_MODEL_NAME} na CPU...", flush=True)
    resultado = WritingStyleClassifier(cache_dir=Settings.from_env().model_cache).classify(texto)
    if not resultado.available:
        parser.exit(1, f"Falha na inferência: {resultado.error}\n")
    print(f"Classe prevista: {resultado.prediction.label}")
    print(f"Confiança do classificador: {resultado.prediction.confidence:.2%}")
    print(f"Score de escrita: {resultado.score:.4f}")
    print(f"Segmentos analisados: {resultado.segments_analyzed}")
    print(f"Revisão do modelo: {resultado.model_version}")
    print("A previsão do modelo não comprova a veracidade da notícia.")


if __name__ == "__main__":
    main()
