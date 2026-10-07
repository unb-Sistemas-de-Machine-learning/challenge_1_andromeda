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
    val value: Double?,
    val title: String = "",
    val reviewDate: String = ""
)

data class RuleResult(val explanation: String, val evidence: List<FactEvidence>, val breakdown: ScoreBreakdown)

/** Public score and wording policy carried over from sdd_v1. */
object AnalysisRules {
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

    fun explain(title: String, url: String, document: Document, atlas: Set<String>, rawFacts: JSONObject,
                writingScore: Float?, atlasStatus: AtlasStatus = AtlasStatus.CURRENT,
                domainAgeDays: Int? = null): RuleResult {
        val domain = URI(url).host.lowercase().removePrefix("www.")
        val source = SourceCredibility.evaluate(document, url, atlas, atlasStatus, domainAgeDays)
        val recognized = source.signals.first().points > 0
        val institutional = listOf("gov.br", "edu.br", "jus.br", "leg.br", "mp.br")
            .any { domain == it || domain.endsWith(".$it") }
        val evaluated = evaluateReviews(title, rawFacts)
        val factScore = evaluated.factScore
        val scoredReviews = evaluated.scored
        val matchedUnscored = evaluated.matchedUnscored

        val breakdown = ScoreCalculator.calculate(factScore, source, writingScore?.toDouble())
        val score = breakdown.finalScore
        val band = when {
            score > 85 -> "alta"
            score > 70 -> "média"
            score > 40 -> "baixa"
            else -> "baixíssima"
        }

        val factual = when {
            factScore == null && matchedUnscored -> "Há fontes relacionadas, mas faltam dados para concluir."
            factScore == null -> "Não há checagem factual disponível."
            scoredReviews.all { it.value != null && it.value > 0.5 } -> "Há evidências favoráveis ao fato analisado."
            scoredReviews.all { it.value != null && it.value < 0.5 } -> "Há evidências contrárias ao fato analisado."
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
        } else if (breakdown.coverage < 100) {
            details.add("A avaliação é parcial.")
        }
        details.add(when (atlasStatus) {
            AtlasStatus.UNAVAILABLE -> "A base do Atlas da Notícia está indisponível no momento."
            AtlasStatus.BUNDLED -> if (recognized)
                "O veículo desta notícia foi encontrado na cópia local do Atlas da Notícia."
                else "O veículo desta notícia não foi encontrado na cópia local do Atlas da Notícia."
            AtlasStatus.CACHED, AtlasStatus.CURRENT -> if (recognized)
                "O veículo desta notícia foi encontrado no Atlas da Notícia."
                else "O veículo desta notícia não foi encontrado na base consultada do Atlas da Notícia."
        })
        if (institutional) details.add(if (domain == "gov.br" || domain.endsWith(".gov.br"))
            "Ponto positivo: o site verificado é um site oficial do governo."
            else "Ponto positivo: o site verificado possui um domínio institucional oficial.")
        if (writingScore == null) details.add("Análise da escrita indisponível.")
        else if (writingScore < 0.5f) details.add("A escrita apresentou sinais que exigem atenção.")

        // Only a same-claim, scored negative review can expose the evidence button.
        val linked = evaluated.relevant.filter { safeLink(it.url) }.distinctBy { it.url.trimEnd('/') }
        val modalEvidence = if (linked.any { it.value != null && it.value < 0.5 })
            linked.sortedWith(compareBy<FactEvidence> { it.value == null || it.value >= 0.5 }.thenBy { it.publisher })
        else emptyList()
        return RuleResult(details.joinToString(" "), modalEvidence, breakdown)
    }

    private data class EvaluatedReviews(
        val factScore: Double?,
        val scored: List<FactEvidence>,
        val matchedUnscored: Boolean,
        val relevant: List<FactEvidence>
    )

    private fun evaluateReviews(title: String, raw: JSONObject): EvaluatedReviews {
        val claims = raw.optJSONArray("claims") ?: return EvaluatedReviews(null, emptyList(), false, emptyList())
        val included = ArrayList<FactEvidence>()
        val seen = HashSet<String>()
        var matchedUnscored = false
        val target = cleanTitle(title)
        for (index in 0 until claims.length()) {
            val claim = claims.optJSONObject(index) ?: continue
            val claimText = claim.optString("text")
            val strictMatch = sameClaim(target, claimText)
            if (!strictMatch && !relatedClaim(target, claimText)) continue
            val reviews = claim.optJSONArray("claimReview") ?: continue
            if (strictMatch) matchedUnscored = true
            for (reviewIndex in 0 until reviews.length()) {
                val review = reviews.optJSONObject(reviewIndex) ?: continue
                val publisherObject = review.optJSONObject("publisher")
                val publisher = publisherObject?.optString("name").orEmpty()
                val link = review.optString("url")
                val rating = review.optString("textualRating")
                val value = ratings[normalize(rating)]
                val key = publisherObject?.optString("site")?.takeIf { it.isNotBlank() }
                    ?: runCatching { URI(link).host }.getOrNull() ?: publisher.takeIf { it.isNotBlank() } ?: continue
                val identity = if (safeLink(link)) link.trimEnd('/')
                    else "${normalize(key)}|${normalize(claimText)}|${review.optString("reviewDate")}|$rating"
                if (!seen.add(identity)) continue
                included.add(FactEvidence(claimText, publisher.ifBlank { key }, rating, link, value,
                    review.optString("title"), review.optString("reviewDate")))
            }
        }
        val scored = included.filter { it.value != null && sameClaim(target, it.claim) }
        if (scored.isEmpty()) return EvaluatedReviews(null, emptyList(), matchedUnscored, included)
        val byPublisher = scored.groupBy { evidence ->
            runCatching { URI(evidence.url).host?.lowercase()?.removePrefix("www.") }.getOrNull()
                ?: normalize(evidence.publisher)
        }
        val factScore = byPublisher.values.map { reviews -> reviews.mapNotNull { it.value }.average() }.average()
        return EvaluatedReviews(factScore, scored, matchedUnscored, included)
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

    // Broader match is only for links in the explanatory modal; it never affects the factual score.
    private fun relatedClaim(target: String, checked: String): Boolean {
        if (target.isBlank() || checked.isBlank()) return false
        if (Regex("\\d+(?:[.,]\\d+)*").findAll(target).map { it.value }.toList() !=
            Regex("\\d+(?:[.,]\\d+)*").findAll(checked).map { it.value }.toList()) return false
        if (locationAnchors(target) != locationAnchors(checked)) return false
        val left = canonical(target).split(' ').filter { it.length >= 2 && it !in stopWords }.toSet()
        val right = canonical(checked).split(' ').filter { it.length >= 2 && it !in stopWords }.toSet()
        val negativeParaphrases = setOf("menospreza", "desmerece", "humilha", "deprecia")
        if (left.any { it in negations } != right.any { it in negations } &&
            !((left.any { it in negations } && right.any { it in negativeParaphrases }) ||
                (right.any { it in negations } && left.any { it in negativeParaphrases }))) return false
        val shared = left.intersect(right) - setOf("diz")
        if (shared.size >= 3) return true
        val actor = attribution(target)?.first?.split(' ')?.lastOrNull() ?: return false
        val negative = setOf("nao", "pobre", "menospreza", "desmerece", "humilha", "deprecia")
        return actor in right && (shared - actor).isNotEmpty() &&
            left.any { it in negative } && right.any { it in negative }
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
