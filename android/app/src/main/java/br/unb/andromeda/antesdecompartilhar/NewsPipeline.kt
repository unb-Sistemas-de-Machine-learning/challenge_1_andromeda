package br.unb.andromeda.antesdecompartilhar

import android.content.Context
import org.json.JSONObject
import org.jsoup.Jsoup
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URLEncoder
import java.nio.charset.StandardCharsets
import java.text.Normalizer

data class ArticleCandidate(val title: String, val url: String, val publisher: String)
data class AnalysisResult(val title: String, val url: String, val explanation: String)

class NewsPipeline(private val context: Context) {
    private val model = BertimbauClassifier(context)
    private val atlasDomains: Set<String> by lazy {
        val data = context.assets.open("atlas-domains.json").bufferedReader().use { it.readText() }
        val array = JSONObject(data).getJSONArray("domains")
        buildSet { for (index in 0 until array.length()) add(array.getString(index)) }
    }

    fun normalizeArticleUrl(value: String): String {
        val candidate = value.trim().let { if (it.startsWith("http://") || it.startsWith("https://")) it else "https://$it" }
        val uri = URI(candidate)
        require(uri.scheme == "https" && !uri.host.isNullOrBlank() && uri.userInfo == null) {
            "Use um link HTTPS válido da reportagem."
        }
        require(uri.host.contains('.') && uri.host.length <= 253) { "Confira o endereço da reportagem." }
        require(!uri.host.endsWith(".local") && !uri.host.matches(Regex("[0-9.]+"))) {
            "Use o endereço público de um veículo de notícias."
        }
        return uri.toASCIIString()
    }

    fun searchByTitle(title: String): List<ArticleCandidate> {
        val query = URLEncoder.encode(title, "UTF-8")
        val endpoint = "https://api.gdeltproject.org/api/v2/doc/doc?query=$query&mode=artlist&format=json&maxrecords=20&sort=datedesc"
        val articles = JSONObject(get(endpoint, 1_000_000)).optJSONArray("articles") ?: return emptyList()
        val candidates = ArrayList<ArticleCandidate>()
        val seen = HashSet<String>()
        for (index in 0 until articles.length()) {
            val item = articles.optJSONObject(index) ?: continue
            val titleFound = item.optString("title").trim()
            val rawUrl = item.optString("url")
            if (titleFound.isBlank() || OpinionFilter.isOpinionText(titleFound)) continue
            val url = try { normalizeArticleUrl(rawUrl) } catch (_: Exception) { continue }
            if (OpinionFilter.isOpinionUrl(url) || !seen.add(url)) continue
            candidates.add(ArticleCandidate(titleFound, url, URI(url).host.removePrefix("www.")))
            if (candidates.size == 8) break
        }
        return candidates
    }

    fun analyze(url: String): AnalysisResult {
        require(!OpinionFilter.isOpinionUrl(url)) { "Artigos de opinião não recebem veredito factual." }
        val html = get(url, 3_000_000)
        val document = Jsoup.parse(html, url)
        document.select("script, style, nav, footer, aside").remove()
        val title = (document.selectFirst("meta[property=og:title]")?.attr("content")
            ?.takeIf { it.isNotBlank() } ?: document.title()).replace(Regex("\\s+"), " ").trim()
        val container = document.selectFirst("article") ?: document.selectFirst("main") ?: document.body()
        val text = container.select("p").joinToString(" ") { it.text() }.replace(Regex("\\s+"), " ").trim()
        require(title.isNotBlank() && text.length >= 120) { "A reportagem não pôde ser extraída para análise." }
        require(!OpinionFilter.isOpinionText(title) && !OpinionFilter.isOpinionText(text.take(2_000))) {
            "Esta página parece ser opinião ou editorial e não será avaliada como notícia."
        }

        val domain = URI(url).host.lowercase().removePrefix("www.")
        val sourceText = when {
            domain.endsWith(".gov.br") -> "Ponto positivo: o site verificado é um site oficial do governo."
            atlasDomains.contains(domain) -> "O veículo aparece no Atlas da Notícia; isso não confirma os fatos da reportagem."
            else -> "O veículo desta notícia não pôde ser consultado na base de veículos."
        }
        val checks = factChecks(title)
        val matched = matchReviews(title, checks)
        val checkText = if (matched.isEmpty()) "Não há checagem factual disponível para esta notícia."
            else "Checagens relacionadas encontradas: ${matched.take(3).joinToString("; ")}."
        val writing = model.classify(text)
        val writingText = if (writing == null) "O modelo local de escrita não pôde ser executado neste dispositivo."
            else "O modelo local encontrou ${writing.label}; esse sinal isolado não comprova veracidade."
        val explanation = "Confiabilidade parcial. $checkText A avaliação considera sinais da fonte e do texto; não confirma os fatos da notícia. $sourceText $writingText"
        return AnalysisResult(title, url, explanation)
    }

    private fun factChecks(title: String): JSONObject {
        require(BuildConfig.FACTCHECK_PROXY_TOKEN.isNotBlank()) {
            "Configure FACTCHECK_PROXY_TOKEN ao gerar o APK."
        }
        val connection = (java.net.URL("${BuildConfig.FACTCHECK_BACKEND_URL}/fact-check").openConnection() as HttpURLConnection)
        connection.requestMethod = "POST"
        connection.connectTimeout = 10_000
        connection.readTimeout = 20_000
        connection.doOutput = true
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
        connection.setRequestProperty("Authorization", "Bearer ${BuildConfig.FACTCHECK_PROXY_TOKEN}")
        val request = JSONObject().put("query", title.take(300)).put("pageSize", 10).put("languageCode", "pt")
        try {
            connection.outputStream.use { it.write(request.toString().toByteArray(StandardCharsets.UTF_8)) }
            if (connection.responseCode !in 200..299) throw IllegalStateException("O serviço de Fact Check não respondeu (${connection.responseCode}).")
            return JSONObject(readLimited(connection, 1_000_000))
        } finally { connection.disconnect() }
    }

    private fun matchReviews(title: String, payload: JSONObject): List<String> {
        val titleWords = words(title)
        val claims = payload.optJSONArray("claims") ?: return emptyList()
        val matches = ArrayList<Pair<Double, String>>()
        for (index in 0 until claims.length()) {
            val claim = claims.optJSONObject(index) ?: continue
            val claimWords = words(claim.optString("text"))
            val overlap = titleWords.intersect(claimWords).size.toDouble()
            val similarity = if (titleWords.isEmpty() || claimWords.isEmpty()) 0.0
                else overlap / titleWords.union(claimWords).size
            if (similarity < 0.20) continue
            val reviews = claim.optJSONArray("claimReview") ?: continue
            for (reviewIndex in 0 until reviews.length()) {
                val review = reviews.optJSONObject(reviewIndex) ?: continue
                val publisher = review.optJSONObject("publisher")?.optString("name").orEmpty()
                val rating = review.optString("textualRating")
                if (publisher.isNotBlank()) matches.add(similarity to "$publisher: ${rating.ifBlank { "avaliação publicada" }}")
            }
        }
        return matches.sortedByDescending { it.first }.map { it.second }.distinct()
    }

    private fun words(value: String): Set<String> {
        val plain = Normalizer.normalize(value.lowercase(), Normalizer.Form.NFD).replace(Regex("\\p{M}+"), "")
        return Regex("[a-z0-9]{3,}").findAll(plain).map { it.value }.filterNot { it in STOP_WORDS }.toSet()
    }

    private fun get(url: String, maxBytes: Int): String {
        val connection = (java.net.URL(url).openConnection() as HttpURLConnection)
        connection.connectTimeout = 10_000
        connection.readTimeout = 20_000
        connection.instanceFollowRedirects = true
        connection.setRequestProperty("User-Agent", "AntesDeCompartilhar/1.0 (Android)")
        try {
            if (connection.responseCode !in 200..299) throw IllegalStateException("Não foi possível acessar a reportagem ou a busca (${connection.responseCode}).")
            return readLimited(connection, maxBytes)
        } finally { connection.disconnect() }
    }

    private fun readLimited(connection: HttpURLConnection, maxBytes: Int): String {
        val output = ByteArrayOutputStream()
        connection.inputStream.use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                require(output.size() + count <= maxBytes) { "O conteúdo recebido é grande demais para análise." }
                output.write(buffer, 0, count)
            }
        }
        return output.toString(StandardCharsets.UTF_8.name())
    }

    companion object {
        private val STOP_WORDS = setOf("para", "com", "uma", "das", "dos", "que", "por", "nos", "nas", "sobre", "como", "tem", "mais")
    }
}
