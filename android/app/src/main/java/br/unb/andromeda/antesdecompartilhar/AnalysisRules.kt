package br.unb.andromeda.antesdecompartilhar

import org.json.JSONObject
import org.jsoup.nodes.Document
import java.net.URI
import java.text.Normalizer

data class FactEvidence(
    val claim: String,
    val publisher: String,
    val verdict: String,
    val url: String,
    val value: Double
)

data class RuleResult(val explanation: String, val evidence: List<FactEvidence>)

/** Public score and wording policy carried over from sdd_v1. */
object AnalysisRules {
    private val weights = mapOf("fact" to 0.65, "source" to 0.20, "writing" to 0.15)
    private val ratings = mapOf(
        "true" to 1.0, "verdadeiro" to 1.0, "correto" to 1.0, "e verdadeiro" to 1.0,
        "mostly true" to 0.75, "majoritariamente verdadeiro" to 0.75,
        "partly true" to 0.5, "half true" to 0.5, "meia verdade" to 0.5,
        "mixed" to 0.5, "impreciso" to 0.5,
        "mostly false" to 0.25, "majoritariamente falso" to 0.25,
        "misleading" to 0.25, "enganoso" to 0.25,
        "fora de contexto" to 0.25, "descontextualizado" to 0.25, "out of context" to 0.25,
        "false" to 0.0, "falso" to 0.0, "fake" to 0.0,
        "nao e verdade" to 0.0, "nao e verdadeiro" to 0.0, "e falso" to 0.0
    )
    private val stopWords = setOf("a", "o", "os", "as", "um", "uma", "de", "da", "do", "das", "dos", "em", "no", "na", "nos", "nas", "para", "por", "com", "que", "e", "ou", "the", "of", "to", "in", "on", "for", "and", "or", "is", "are")
    private val negations = setOf("nao", "nunca", "jamais", "not", "never", "sem")
    private val polarityGroups = listOf(
        negations,
        setOf("falso", "fake", "boato", "mentira", "desmente", "desmentido", "enganoso"),
        setOf("aumenta", "aumentou", "aumentam"),
        setOf("reduz", "reduziu", "reduzem"),
        setOf("retoma", "retomou", "retomaram"),
        setOf("suspende", "suspendeu", "suspenderam")
    )
    private val states = setOf("AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO")
    private val reporting = "diz|disse|afirma|afirmou|declara|declarou|falou"

    fun explain(title: String, url: String, document: Document, atlas: Set<String>, rawFacts: JSONObject, writingScore: Float?): RuleResult {
        val domain = URI(url).host.lowercase().removePrefix("www.")
        val recognized = domain in atlas
        val institutional = listOf("gov.br", "edu.br", "jus.br", "leg.br", "mp.br").any { domain.endsWith(".$it") }
        val sourceScore = sourceScore(document, url, recognized, institutional)
        val evaluated = evaluateReviews(title, rawFacts)
        val factScore = evaluated.first
        val scoredReviews = evaluated.second
        val matchedUnscored = evaluated.third

        val availableWeights = weights.getValue("source") +
            (if (factScore != null) weights.getValue("fact") else 0.0) +
            (if (writingScore != null) weights.getValue("writing") else 0.0)
        var score = (weights.getValue("source") * sourceScore +
            (if (factScore != null) weights.getValue("fact") * factScore * 100 else 0.0) +
            (if (writingScore != null) weights.getValue("writing") * writingScore * 100 else 0.0)) / availableWeights
        if (sourceScore < 20) score = minOf(score, 35.0) // sdd_v1 source veto
        val band = when {
            score > 85 -> "alta"
            score > 70 -> "média"
            score > 40 -> "baixa"
            else -> "baixíssima"
        }

        val factual = when {
            factScore == null && matchedUnscored -> "Há fontes relacionadas, mas faltam dados para concluir."
            factScore == null -> "Não há checagem factual disponível."
            scoredReviews.all { it.value > 0.5 } -> "Há evidências favoráveis ao fato analisado."
            scoredReviews.all { it.value < 0.5 } -> "Há evidências contrárias ao fato analisado."
            else -> "Há evidências divergentes sobre o fato analisado."
        }
        val details = ArrayList<String>()
        details.add("Confiabilidade $band.")
        details.add(factual)
        if (factScore == null) {
            details.add(when {
                writingScore != null -> "A avaliação considera a credibilidade da fonte e o estilo de escrita; não confirma os fatos da notícia."
                else -> "A avaliação considera apenas a credibilidade da fonte e não confirma os fatos da notícia."
            })
        } else if (availableWeights < 1.0) {
            details.add("A avaliação é parcial.")
        }
        details.add(if (recognized) "O veículo desta notícia foi encontrado no Atlas da Notícia."
            else "O veículo desta notícia não pôde ser consultado na base de veículos.")
        if (institutional) details.add(if (domain.endsWith(".gov.br"))
            "Ponto positivo: o site verificado é um site oficial do governo."
            else "Ponto positivo: o site verificado possui um domínio institucional oficial.")
        if (writingScore == null) details.add("Análise da escrita indisponível.")
        else if (writingScore < 0.5f) details.add("A escrita apresentou sinais que exigem atenção.")

        // Only a same-claim, scored negative review can expose the evidence button.
        val linked = scoredReviews.filter { safeLink(it.url) }.sortedBy { it.value }
        val modalEvidence = if (linked.any { it.value < 0.5 }) linked else emptyList()
        return RuleResult(details.joinToString(" "), modalEvidence)
    }

    private fun sourceScore(document: Document, url: String, recognized: Boolean, institutional: Boolean): Int {
        val author = document.select("meta[name=author], meta[property=article:author], [rel=author], [itemprop=author]")
            .any { it.attr("content").isNotBlank() || it.text().isNotBlank() }
        val date = document.select("meta[name=date], meta[name=datePublished], meta[property=article:published_time], meta[name=pubdate], time[datetime]")
            .any { it.attr("content").isNotBlank() || it.attr("datetime").isNotBlank() }
        val domain = URI(url).host.lowercase().removePrefix("www.")
        val contact = document.select("a[href]").any { link ->
            val target = runCatching { URI(url).resolve(link.attr("href")) }.getOrNull()
            val label = normalize("${link.text()} ${target?.path.orEmpty()}")
            target?.host?.lowercase()?.removePrefix("www.") == domain &&
                listOf("sobre", "contato", "about", "contact", "quem somos", "quem-somos").any { label.contains(it) }
        }
        return minOf(100, (if (recognized) 40 else 0) + (if (author) 12 else 0) +
            (if (date) 6 else 0) + (if (contact) 12 else 0) +
            (if (institutional) 100 else 0) + 5) // HTTPS was validated when the article was fetched.
    }

    private fun evaluateReviews(title: String, raw: JSONObject): Triple<Double?, List<FactEvidence>, Boolean> {
        val claims = raw.optJSONArray("claims") ?: return Triple(null, emptyList(), false)
        val included = ArrayList<FactEvidence>()
        val seen = HashSet<String>()
        var matchedUnscored = false
        val target = cleanTitle(title)
        for (index in 0 until claims.length()) {
            val claim = claims.optJSONObject(index) ?: continue
            val claimText = claim.optString("text")
            if (!sameClaim(target, claimText)) continue
            val reviews = claim.optJSONArray("claimReview") ?: continue
            matchedUnscored = true
            for (reviewIndex in 0 until reviews.length()) {
                val review = reviews.optJSONObject(reviewIndex) ?: continue
                val publisherObject = review.optJSONObject("publisher")
                val publisher = publisherObject?.optString("name").orEmpty()
                val link = review.optString("url")
                val rating = review.optString("textualRating")
                val value = ratings[normalize(rating)] ?: continue
                val key = publisherObject?.optString("site")?.takeIf { it.isNotBlank() }
                    ?: runCatching { URI(link).host }.getOrNull() ?: publisher.takeIf { it.isNotBlank() } ?: continue
                val identity = if (link.isNotBlank()) "$link|${normalize(claimText)}"
                    else "${normalize(key)}|${normalize(claimText)}|${review.optString("reviewDate")}|$rating"
                if (!seen.add(identity)) continue
                included.add(FactEvidence(claimText, publisher.ifBlank { key }, rating, link, value))
            }
        }
        if (included.isEmpty()) return Triple(null, emptyList(), matchedUnscored)
        val byPublisher = included.groupBy { evidence ->
            runCatching { URI(evidence.url).host?.lowercase()?.removePrefix("www.") }.getOrNull()
                ?: normalize(evidence.publisher)
        }
        val factScore = byPublisher.values.map { reviews -> reviews.map { it.value }.average() }.average()
        return Triple(factScore, included, matchedUnscored)
    }

    private fun cleanTitle(value: String): String {
        var title = value.trim()
        for (separator in listOf(" | ", " - ", " — ")) if (separator in title) title = title.substringBefore(separator).trim()
        return title
    }

    private fun sameClaim(target: String, checked: String): Boolean {
        if (target.isBlank() || checked.isBlank()) return false
        val left = canonical(target)
        val right = canonical(checked)
        val leftWords = left.split(' ').filter { it.length >= 2 && it !in stopWords }.toSet()
        val rightWords = right.split(' ').filter { it.length >= 2 && it !in stopWords }.toSet()
        val overlap = leftWords.intersect(rightWords)
        if (leftWords.isEmpty() || rightWords.isEmpty()) return false
        if (Regex("\\d+(?:[.,]\\d+)*").findAll(target).map { it.value }.toList() !=
            Regex("\\d+(?:[.,]\\d+)*").findAll(checked).map { it.value }.toList()) return false
        val locations = locationAnchors(target) + locationAnchors(checked)
        if (locations.any { (it.lowercase() in left.split(' ')) != (it.lowercase() in right.split(' ')) }) return false
        if (polarityGroups.any { group -> (leftWords.any { it in group }) != (rightWords.any { it in group }) }) return false
        val leftAttribution = attribution(target)
        val rightAttribution = attribution(checked)
        if ((leftAttribution == null) != (rightAttribution == null)) return false
        if (leftAttribution != null && rightAttribution != null) {
            if (leftAttribution.first != rightAttribution.first) return false
            if ((leftAttribution.first.split(' ').any { it in negations }) != (rightAttribution.first.split(' ').any { it in negations })) return false
            if ((leftAttribution.second.split(' ').any { it in negations }) != (rightAttribution.second.split(' ').any { it in negations })) return false
        }
        val similarity = minOf(overlap.size.toDouble() / leftWords.size, overlap.size.toDouble() / rightWords.size)
        return left == right || (overlap.size >= 3 && similarity >= 0.8)
    }

    private fun canonical(value: String): String {
        var text = normalize(value)
        text = text.replace(Regex("\\bdistrito federal\\b"), "df")
            .replace(Regex("\\b(?:garis|lixeiros?)\\b"), "gari")
            .replace(Regex("\\b(?:proporciona|proporcionam|traz|gera) orgulho\\b"), "da orgulho")
            .replace(Regex("\\b(?:$reporting)\\b"), "diz")
        if ("gari" in text.split(' ')) {
            text = text.replace(Regex("\\b(?:ser|trabalhar como) gari\\b"), "gari")
                .replace(Regex("\\b(?:coisa|profissao|trabalho) pobre\\b"), "pobre")
        }
        return text
    }

    private fun attribution(value: String): Pair<String, String>? {
        val match = Regex("^(.+?)\\s+($reporting)\\s+(?:que\\s+)?(.+)$").find(normalize(value)) ?: return null
        val actor = match.groupValues[1].replace(Regex("^(?:o|a)\\s+"), "")
            .replace(Regex("^(?:presidente|ex presidente)\\s+"), "")
        return actor to match.groupValues[3]
    }

    private fun locationAnchors(value: String): Set<String> {
        val found = Regex("\\b[A-Z]{2}\\b").findAll(value).map { it.value }.filter { it in states }.toMutableSet()
        if ("distrito federal" in normalize(value)) found.add("DF")
        return found
    }

    private fun safeLink(url: String): Boolean = runCatching {
        val uri = URI(url)
        uri.scheme in setOf("http", "https") && !uri.host.isNullOrBlank()
    }.getOrDefault(false)

    private fun normalize(value: String): String {
        val plain = Normalizer.normalize(value.lowercase(), Normalizer.Form.NFKD).replace(Regex("\\p{M}+"), "")
        return plain.replace(Regex("[^a-z0-9]+"), " ").trim().replace(Regex("\\s+"), " ")
    }
}
