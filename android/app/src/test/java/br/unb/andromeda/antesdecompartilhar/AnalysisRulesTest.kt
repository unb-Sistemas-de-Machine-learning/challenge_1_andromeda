package br.unb.andromeda.antesdecompartilhar

import org.json.JSONObject
import org.jsoup.Jsoup
import java.net.URI
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

    @Test fun modalListsEveryLinkedRelevantReviewWithoutChangingUnknownVerdictScore() {
        val title = "Lula diz que ser lixeiro não dá orgulho: coisa pobre"
        val claim = "Lula afirma que ser gari não dá orgulho: coisa pobre"
        val reviews = org.json.JSONArray()
            .put(review("Estadão", "Fora de contexto", "https://estadao.com.br/checagem", "Lula falou sobre garis"))
            .put(review("Agência Lupa", "Falso", "https://lupa.com.br/checagem", "O que Lula disse"))
            .put(review("Outro veículo", "Depende do contexto", "https://outro.com.br/checagem", "Análise complementar"))
            .put(review("Estadão", "Fora de contexto", "https://estadao.com.br/checagem", "Duplicata"))
        val facts = JSONObject().put("claims", org.json.JSONArray()
            .put(JSONObject().put("text", claim).put("claimReview", reviews))
            .put(JSONObject().put("text", "Vacina altera DNA de crianças").put("claimReview",
                org.json.JSONArray().put(review("Irrelevante", "Falso", "https://irrelevante.com.br/checagem", "Outro assunto")))))

        val result = AnalysisRules.explain(title, "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), facts, 0.85f)

        assertEquals(3, result.evidence.size)
        assertEquals(setOf("https://estadao.com.br/checagem", "https://lupa.com.br/checagem", "https://outro.com.br/checagem"),
            result.evidence.map { it.url }.toSet())
        assertEquals("Lula falou sobre garis", result.evidence.first { it.publisher == "Estadão" }.title)
        assertTrue(result.explanation.contains("Há evidências contrárias"))
    }

    @Test fun relatedParaphrasesAppearAsLinksButDoNotChangeStrictScore() {
        val title = "Lula diz que ser lixeiro não dá orgulho: coisa pobre"
        val strict = "Lula diz que gari é profissão pobre e que não dá orgulho"
        val quote = "Quando eu vejo aquelas pessoas que trabalham colhendo lixo, é uma profissão muito pobre, porque não é uma profissão que dá orgulho. Eu sou lixeiro."
        val paraphrase = "Lula menospreza garis durante discurso"
        val claims = org.json.JSONArray()
            .put(JSONObject().put("text", strict).put("claimReview", org.json.JSONArray()
                .put(review("Estadão", "Fora de contexto", "https://estadao.com.br/checagem", "O que foi dito"))))
            .put(JSONObject().put("text", quote).put("claimReview", org.json.JSONArray()
                .put(review("Lupa", "Falso", "https://lupa.com.br/checagem", "A fala completa"))))
            .put(JSONObject().put("text", paraphrase).put("claimReview", org.json.JSONArray()
                .put(review("Aos Fatos", "Falso", "https://aosfatos.org/checagem", "Discurso sobre garis"))))
        val facts = JSONObject().put("claims", claims)
        val strictOnly = JSONObject().put("claims", org.json.JSONArray().put(claims.getJSONObject(0)))

        val result = AnalysisRules.explain(title, "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), facts, 0.85f)
        val original = AnalysisRules.explain(title, "https://jornal.com.br/noticia", page, setOf("jornal.com.br"), strictOnly, 0.85f)

        assertEquals(original.explanation, result.explanation)
        assertEquals(3, result.evidence.size)
        assertEquals(3, result.evidence.map { it.url }.toSet().size)
    }

    private fun review(publisher: String, rating: String, url: String, title: String): JSONObject = JSONObject()
        .put("publisher", JSONObject().put("name", publisher).put("site", URI(url).host))
        .put("textualRating", rating).put("url", url).put("title", title)

    private fun facts(claim: String, rating: String): JSONObject = JSONObject().put("claims", org.json.JSONArray().put(
        JSONObject().put("text", claim).put("claimReview", org.json.JSONArray().put(
            JSONObject().put("publisher", JSONObject().put("name", "Estadão").put("site", "estadao.com.br"))
                .put("textualRating", rating).put("url", "https://checador.com.br/checagem")
        ))
    ))
}
