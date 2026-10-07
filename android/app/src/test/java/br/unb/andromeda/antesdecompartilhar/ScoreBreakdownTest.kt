package br.unb.andromeda.antesdecompartilhar

import org.jsoup.Jsoup
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ScoreBreakdownTest {
    @Test fun governmentExampleMatchesAvailableWeightFormula() {
        val source = SourceCredibility.evaluate(Jsoup.parse("<html></html>"),
            "https://www.gov.br/noticia", emptySet(), AtlasStatus.UNAVAILABLE, 3325)
        val result = ScoreCalculator.calculate(null, source, 1.0)

        assertEquals(100, source.score)
        assertEquals(60, source.coverage)
        assertEquals(35, result.coverage)
        assertEquals("(0.20 × C + 0.15 × W) / 0.35 × 100", result.formula)
        assertEquals(100.0, result.finalScore, 0.0001)
        assertEquals(57.1429, result.criteria[1].contribution!!, 0.0001)
        assertEquals(42.8571, result.criteria[2].contribution!!, 0.0001)
    }

    @Test fun sourceAgeBandsAndVetoFollowLegacyPolicy() {
        val page = Jsoup.parse("<html></html>")
        val recent = SourceCredibility.evaluate(page, "https://jornal.com.br/noticia",
            emptySet(), AtlasStatus.UNAVAILABLE, 20)
        assertEquals(5, recent.score)
        assertEquals(0, recent.signals[2].points)
        val capped = ScoreCalculator.calculate(null, recent, 1.0)
        assertTrue(capped.scoreBeforeVeto > 35)
        assertEquals(35.0, capped.finalScore, 0.0001)
        assertTrue(capped.sourceVetoApplied)

        val old = SourceCredibility.evaluate(page, "https://jornal.com.br/noticia",
            emptySet(), AtlasStatus.CURRENT, 3000)
        assertEquals(13, old.signals[2].points)
        assertEquals(18, old.score)
    }

    @Test fun registeredDomainKeepsBrazilianCategorySuffix() {
        assertEquals("jornal.com.br", DomainAge.registrableDomain("www.jornal.com.br"))
        assertEquals("anpd.gov.br", DomainAge.registrableDomain("www.anpd.gov.br"))
        assertEquals("example.com", DomainAge.registrableDomain("news.example.com"))
    }
}
