package br.unb.andromeda.antesdecompartilhar

import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.URI
import java.net.URL
import java.time.Instant
import java.time.OffsetDateTime
import java.time.temporal.ChronoUnit

/** Reads the registration event from public RDAP; unavailable age has no invented value. */
class DomainAge {
    private val cache = HashMap<String, Pair<Long, Int?>>()

    fun days(url: String): Int? {
        val domain = registrableDomain(URI(url).host) ?: return null
        val cached = cache[domain]
        if (cached != null && System.currentTimeMillis() - cached.first <
            (if (cached.second == null) 3_600_000L else 86_400_000L)) return cached.second
        val age = runCatching {
            val endpoint = if (domain.endsWith(".br")) "https://rdap.registro.br/domain/"
                else "https://rdap.org/domain/"
            val events = JSONObject(readRdap(endpoint + domain)).getJSONArray("events")
            val registered = (0 until events.length()).mapNotNull { index ->
                val event = events.optJSONObject(index) ?: return@mapNotNull null
                if (event.optString("eventAction") != "registration") return@mapNotNull null
                runCatching { OffsetDateTime.parse(event.getString("eventDate")).toInstant() }.getOrNull()
            }.minOrNull() ?: return@runCatching null
            ChronoUnit.DAYS.between(registered, Instant.now()).takeIf { it >= 0 }?.toInt()
        }.getOrNull()
        cache[domain] = System.currentTimeMillis() to age
        return age
    }

    private fun readRdap(url: String): String {
        var current = URI(url)
        repeat(5) {
            require(current.scheme == "https" && !current.host.isNullOrBlank() &&
                !current.host.endsWith(".local") && !current.host.matches(Regex("[0-9.]+")))
            val connection = current.toURL().openConnection() as HttpURLConnection
            connection.connectTimeout = 6_000
            connection.readTimeout = 6_000
            connection.instanceFollowRedirects = false
            try {
                val status = connection.responseCode
                if (status in 300..399) {
                    current = current.resolve(connection.getHeaderField("Location") ?: error("Missing RDAP redirect"))
                } else {
                    require(status in 200..299)
                    val output = ByteArrayOutputStream()
                    connection.inputStream.use { input ->
                        val buffer = ByteArray(8192)
                        while (true) {
                            val count = input.read(buffer)
                            if (count < 0) break
                            require(output.size() + count <= 256_000)
                            output.write(buffer, 0, count)
                        }
                    }
                    return output.toString("UTF-8")
                }
            } finally {
                connection.disconnect()
            }
        }
        error("RDAP redirect limit exceeded")
    }

    companion object {
        internal fun registrableDomain(host: String?): String? {
            val labels = host?.lowercase()?.removePrefix("www.")?.split('.') ?: return null
            if (labels.size < 2 || labels.any { it.isBlank() }) return null
            val suffix = labels.takeLast(2).joinToString(".")
            val parts = if (suffix in setOf("com.br", "org.br", "net.br", "gov.br", "edu.br", "jus.br",
                    "leg.br", "mp.br", "co.uk", "org.uk") && labels.size >= 3) 3 else 2
            return labels.takeLast(parts).joinToString(".")
        }
    }
}
