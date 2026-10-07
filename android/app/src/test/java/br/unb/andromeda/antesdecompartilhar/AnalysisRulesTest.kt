package br.unb.andromeda.antesdecompartilhar

import org.json.JSONObject
import org.jsoup.Jsoup
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AnalysisRulesTest {
    private val page = Jsoup.parse("""
        <html><head><meta name="author" content="Redação"><meta property="article:published_time" content="2026-10-07"></head>
        <body><a href="/contato">Contato</a><article><p>Texto da reportagem.</p></article></body></html>
    """.trimIndent())

    @Test fun governmentWithoutFactCheckKeepsHighBandAndOriginalWording() {
        val result = AnalysisRules.explain("Governo publica medida", "https://noticias.gov.br/medida", page, emptySet(), JSONObject("{\"claims\":[]}"), 0.95f)
        assertTrue(result.explanation.startsWith("Confiabilidade alta. Não há checagem factual disponível."))
        assertTrue(result.explanation.contains("A avaliação considera a credibilidade da fonte e o estilo de escrita; não confirma os fatos da notícia."))
        assertTrue(result.explanation.contains("Ponto positivo: o site verificado é um site oficial do governo."))
        assertTrue(result.evidence.isEmpty())
    }

    @Test fun negativeSameClaimContributesAndExposesItsLink() {
        val fact = facts("Lula afirma que ser gari não dá orgulho: coisa pobre", "Fora de contexto")
        val result = AnalysisRules.explain("Lula diz que ser lixeiro não dá orgulho: coisa pobre", "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), fact, 0.85f)
        assertTrue(result.explanation.startsWith("Confiabilidade baixa. Há evidências contrárias ao fato analisado."))
        assertEquals(1, result.evidence.size)
        assertEquals("https://checador.com.br/checagem", result.evidence.single().url)
    }

    @Test fun unrelatedCheckDoesNotChangeTheScoreOrShowEvidence() {
        val fact = facts("Vacina altera DNA de crianças", "Falso")
        val result = AnalysisRules.explain("Lula diz que ser lixeiro não dá orgulho", "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), fact, 0.85f)
        assertTrue(result.explanation.contains("Não há checagem factual disponível."))
        assertTrue(result.evidence.isEmpty())
    }

    @Test fun positiveOrUnmappedRatingNeverExposesNegativeEvidence() {
        val title = "Lula diz que ser lixeiro não dá orgulho: coisa pobre"
        val claim = "Lula afirma que ser gari não dá orgulho: coisa pobre"
        val positive = AnalysisRules.explain(title, "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), facts(claim, "Verdadeiro"), 0.85f)
        assertTrue(positive.evidence.isEmpty())
        val unmapped = AnalysisRules.explain(title, "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), facts(claim, "Not true"), 0.85f)
        assertFalse(unmapped.explanation.contains("Há evidências contrárias"))
        assertTrue(unmapped.evidence.isEmpty())
    }

    @Test fun changedNegationOrNumberCannotBorrowAnOldVerdict() {
        val url = "https://jornal.com.br/noticia"
        val atlas = setOf("jornal.com.br")
        val changedNegation = AnalysisRules.explain("Lula diz que ser lixeiro não dá orgulho", url, page, atlas,
            facts("Lula diz que ser gari dá orgulho", "Falso"), 0.85f)
        assertTrue(changedNegation.evidence.isEmpty())
        val changedNumber = AnalysisRules.explain("Governo anuncia 2026 como prazo", url, page, atlas,
            facts("Governo anuncia 2025 como prazo", "Falso"), 0.85f)
        assertTrue(changedNumber.evidence.isEmpty())
    }

    private fun facts(claim: String, rating: String): JSONObject = JSONObject().put("claims", org.json.JSONArray().put(
        JSONObject().put("text", claim).put("claimReview", org.json.JSONArray().put(
            JSONObject().put("publisher", JSONObject().put("name", "Estadão").put("site", "estadao.com.br"))
                .put("textualRating", rating).put("url", "https://checador.com.br/checagem")
        ))
    ))
}
