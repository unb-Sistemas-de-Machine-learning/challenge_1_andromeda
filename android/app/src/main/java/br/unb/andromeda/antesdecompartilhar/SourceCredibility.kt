package br.unb.andromeda.antesdecompartilhar

import org.json.JSONArray
import org.json.JSONObject
import org.jsoup.nodes.Document
import java.net.URI
import java.text.Normalizer

data class SourceSignal(val name: String, val points: Int, val maximum: Int, val available: Boolean, val detail: String)
data class SourceAssessment(val score: Int, val coverage: Int, val veto: Boolean, val signals: List<SourceSignal>)

/** Mirrors the source-policy-v5 point bands used by sdd_v1. */
object SourceCredibility {
    fun evaluate(document: Document, url: String, atlas: Set<String>, atlasStatus: AtlasStatus,
                 ageDays: Int?): SourceAssessment {
        val domain = URI(url).host.lowercase().removePrefix("www.")
        val recognized = atlasStatus != AtlasStatus.UNAVAILABLE && domain in atlas
        val atlasAvailable = atlasStatus != AtlasStatus.UNAVAILABLE
        val authorMeta = document.select("meta[name=author], meta[property=article:author], [rel=author], [itemprop=author]")
            .any { it.attr("content").isNotBlank() || it.text().isNotBlank() }
        val dateMeta = document.select("meta[name=date], meta[name=datePublished], meta[property=article:published_time], meta[name=pubdate], time[datetime]")
            .any { it.attr("content").isNotBlank() || it.attr("datetime").isNotBlank() }
        val jsonLd = document.select("script[type=application/ld+json]").mapNotNull { script ->
            runCatching { JSONObject(script.data()) }.getOrNull()
        }
        val author = authorMeta || jsonLd.any { articleField(it, "author") }
        val date = dateMeta || jsonLd.any { articleField(it, "datePublished") }
        val contact = document.select("a[href]").any { link ->
            val target = runCatching { URI(url).resolve(link.attr("href")) }.getOrNull()
            val label = normalize("${link.text()} ${target?.path.orEmpty()}")
            target?.host?.lowercase()?.removePrefix("www.") == domain &&
                listOf("sobre", "contato", "about", "contact", "quem somos").any { label.contains(it) }
        }
        val transparency = (if (author) 12 else 0) + (if (date) 6 else 0) + (if (contact) 12 else 0)
        val agePoints = ageDays?.let { days ->
            var points = when {
                days < 30 -> 0
                days < 183 -> 5
                days < 730 -> 13
                days < 1826 -> 20
                else -> 25
            }
            if (!recognized && transparency < 18) points = minOf(points, 13)
            points
        }
        val institutional = listOf("gov.br", "edu.br", "jus.br", "leg.br", "mp.br")
            .any { domain == it || domain.endsWith(".$it") }
        val https = URI(url).scheme.equals("https", true)
        val signals = listOf(
            SourceSignal("Veículo no Atlas", if (recognized) 40 else 0, 40, atlasAvailable,
                if (recognized) "Encontrado" else if (atlasAvailable) "Não encontrado" else "Base indisponível"),
            SourceSignal("Transparência editorial", transparency, 30, true,
                listOfNotNull(if (author) "autor" else null, if (date) "data" else null,
                    if (contact) "contato" else null).joinToString(", ").ifBlank { "Nenhum sinal localizado" }),
            SourceSignal("Idade do domínio", agePoints ?: 0, 25, agePoints != null,
                if (ageDays == null) "Data indisponível" else "$ageDays dias"),
            SourceSignal("Domínio institucional", if (institutional) 100 else 0, 100, institutional,
                if (institutional) "Bônus oficial" else "Não identificado; sem penalidade"),
            SourceSignal("Conexão HTTPS", if (https) 5 else 0, 5, true,
                if (https) "Conexão segura" else "Sem HTTPS")
        )
        val score = minOf(100, signals.sumOf { it.points })
        val coverage = (if (atlasAvailable) 40 else 0) + 30 + (if (agePoints != null) 25 else 0) + 5
        return SourceAssessment(score, coverage, score < 20, signals)
    }

    private fun articleField(value: JSONObject, field: String): Boolean {
        val graph = value.optJSONArray("@graph")
        if (graph != null && (0 until graph.length()).any { index ->
                graph.optJSONObject(index)?.let { articleField(it, field) } == true }) return true
        val types = value.opt("@type")
        val article = when (types) {
            is String -> types in ARTICLE_TYPES
            is JSONArray -> (0 until types.length()).any { types.optString(it) in ARTICLE_TYPES }
            else -> false
        }
        if (!article) return false
        val candidate = value.opt(field)
        return when (candidate) {
            is String -> candidate.isNotBlank()
            is JSONObject -> candidate.optString("name").isNotBlank()
            is JSONArray -> (0 until candidate.length()).any { index ->
                when (val item = candidate.opt(index)) {
                    is String -> item.isNotBlank()
                    is JSONObject -> item.optString("name").isNotBlank()
                    else -> false
                }
            }
            else -> false
        }
    }

    private val ARTICLE_TYPES = setOf("Article", "NewsArticle", "BlogPosting", "ReportageNewsArticle")
    private fun normalize(value: String): String = Normalizer.normalize(value.lowercase(), Normalizer.Form.NFKD)
        .replace(Regex("\\p{M}+"), "").replace(Regex("[^a-z0-9]+"), " ").trim()
}
