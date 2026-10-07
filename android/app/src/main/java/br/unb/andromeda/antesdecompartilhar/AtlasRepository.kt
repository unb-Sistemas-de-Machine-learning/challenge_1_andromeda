package br.unb.andromeda.antesdecompartilhar

import android.content.Context
import android.os.SystemClock
import android.util.AtomicFile
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.net.HttpURLConnection
import java.net.IDN
import java.net.URI
import java.net.URL
import java.nio.charset.StandardCharsets
import java.time.Instant
import java.time.ZoneId

enum class AtlasStatus { CURRENT, CACHED, BUNDLED, UNAVAILABLE }
data class AtlasSnapshot(val domains: Set<String>, val status: AtlasStatus)

/** Refreshes the Atlas index on the device. Analysis only reads this local index. */
class AtlasRepository(private val context: Context) {
    private val cache = AtomicFile(context.filesDir.resolve("atlas-domains-cache.json"))
    private val preferences = context.getSharedPreferences("atlas_refresh", Context.MODE_PRIVATE)

    @Synchronized
    fun refreshIfNeeded(): AtlasSnapshot {
        val now = System.currentTimeMillis()
        val saved = readCache()
        val lastAttempt = preferences.getLong("last_attempt", 0L)
        val sameDay = saved != null && Instant.ofEpochMilli(saved.first).atZone(SAO_PAULO).toLocalDate() ==
            Instant.ofEpochMilli(now).atZone(SAO_PAULO).toLocalDate()
        if (sameDay || (lastAttempt > 0 && now - lastAttempt in 0 until RETRY_DELAY_MS)) return snapshot(saved, now)

        preferences.edit().putLong("last_attempt", now).apply()
        try {
            val deadline = SystemClock.elapsedRealtime() + SYNC_BUDGET_MS
            val token = JSONObject(get("$BASE/auth/dummy-jwt", null, 16_384, deadline)).getString("access_token")
            require(token.isNotBlank()) { "Atlas authentication unavailable" }
            val definitions = JSONArray(get("$BASE/data/analytic/definitions", token, 128_000, deadline))
            val fields = (0 until definitions.length()).map { definitions.optString(it) }.toSet()
            require(fields.containsAll(REQUIRED_FIELDS)) { "Atlas definitions changed" }
            val rows = JSONArray(get("$BASE/data/analytic?ativo=1&segmento=Online&field[]=id&field[]=nome_veiculo&field[]=segmento&field[]=ativo&field[]=eh_jornal&field[]=data_fechamento",
                token, 32 * 1024 * 1024, deadline))
            val domains = collectDomains(rows) { shortUrl -> resolveShortener(shortUrl, deadline) }
            val baseline = saved?.second?.size ?: bundled()?.second?.size ?: 0
            require(domains.isNotEmpty() && (baseline == 0 || domains.size >= baseline / 2)) {
                "Atlas collection unexpectedly small"
            }
            val payload = JSONObject().put("version", 2).put("fetched_at", now)
                .put("domains", JSONArray(domains.sorted())).toString().toByteArray(StandardCharsets.UTF_8)
            val stream = cache.startWrite()
            try {
                stream.write(payload)
                cache.finishWrite(stream)
            } catch (error: Exception) {
                cache.failWrite(stream)
                throw error
            }
            return AtlasSnapshot(domains, AtlasStatus.CURRENT)
        } catch (_: Exception) {
            return snapshot(saved, now)
        }
    }

    private fun snapshot(saved: Pair<Long, Set<String>>?, now: Long): AtlasSnapshot {
        if (saved != null && now - saved.first in 0..MAX_AGE_MS) {
            val status = if (Instant.ofEpochMilli(saved.first).atZone(SAO_PAULO).toLocalDate() ==
                Instant.ofEpochMilli(now).atZone(SAO_PAULO).toLocalDate()) AtlasStatus.CURRENT else AtlasStatus.CACHED
            return AtlasSnapshot(saved.second, status)
        }
        val embedded = bundled()
        return if (embedded == null || now - embedded.first !in 0..MAX_AGE_MS)
            AtlasSnapshot(emptySet(), AtlasStatus.UNAVAILABLE)
            else AtlasSnapshot(embedded.second, AtlasStatus.BUNDLED)
    }

    private fun readCache(): Pair<Long, Set<String>>? = runCatching {
        val json = JSONObject(cache.openRead().bufferedReader().use { it.readText() })
        require(json.getInt("version") == 2)
        val fetchedAt = json.getLong("fetched_at")
        require(fetchedAt > 0 && fetchedAt <= System.currentTimeMillis())
        val domains = readDomains(json.getJSONArray("domains"))
        require(domains.isNotEmpty())
        fetchedAt to domains
    }.getOrNull()

    private fun bundled(): Pair<Long, Set<String>>? = runCatching {
        val json = JSONObject(context.assets.open("atlas-domains.json").bufferedReader().use { it.readText() })
        val exportedAt = Instant.parse(json.getString("exported_at")).toEpochMilli()
        val domains = readDomains(json.getJSONArray("domains"))
        require(domains.isNotEmpty())
        exportedAt to domains
    }.getOrNull()

    private fun get(url: String, token: String?, maxBytes: Int, deadline: Long): String {
        val connection = URL(url).openConnection() as HttpURLConnection
        connection.instanceFollowRedirects = false
        val remaining = (deadline - SystemClock.elapsedRealtime()).coerceAtMost(20_000L).toInt()
        require(remaining > 0) { "Atlas refresh timed out" }
        connection.connectTimeout = remaining
        connection.readTimeout = remaining
        connection.setRequestProperty("User-Agent", "Andromeda-Atlas-Android/1.0")
        if (token != null) connection.setRequestProperty("Authorization", "Bearer $token")
        try {
            require(connection.responseCode in 200..299) { "Atlas request failed" }
            val output = ByteArrayOutputStream()
            connection.inputStream.use { input ->
                val buffer = ByteArray(8192)
                while (true) {
                    require(SystemClock.elapsedRealtime() < deadline) { "Atlas refresh timed out" }
                    val count = input.read(buffer)
                    if (count < 0) break
                    require(output.size() + count <= maxBytes) { "Atlas response too large" }
                    output.write(buffer, 0, count)
                }
            }
            return output.toString(StandardCharsets.UTF_8.name())
        } finally {
            connection.disconnect()
        }
    }

    private fun resolveShortener(url: String, deadline: Long): String? = runCatching {
        var current = URI(url)
        repeat(5) {
            require(current.scheme == "https" && publicHost(current.host) != null)
            val connection = current.toURL().openConnection() as HttpURLConnection
            connection.instanceFollowRedirects = false
            val remaining = (deadline - SystemClock.elapsedRealtime()).coerceAtMost(10_000L).toInt()
            require(remaining > 0)
            connection.connectTimeout = remaining
            connection.readTimeout = remaining
            try {
                val code = connection.responseCode
                if (code in 300..399) {
                    current = current.resolve(connection.getHeaderField("Location") ?: error("Missing redirect"))
                } else {
                    require(code in 200..299)
                    return@runCatching current.toString()
                }
            } finally {
                connection.disconnect()
            }
        }
        null
    }.getOrNull()

    companion object {
        private const val BASE = "https://api.atlas.jor.br/api/v1"
        private const val SYNC_BUDGET_MS = 120_000L
        private const val RETRY_DELAY_MS = 60 * 60 * 1000L
        private const val MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000L
        private val SAO_PAULO = ZoneId.of("America/Sao_Paulo")
        private val REQUIRED_FIELDS = setOf("id", "nome_veiculo", "segmento", "ativo", "eh_jornal", "data_fechamento")
        private val SHORTENERS = setOf("t.co", "bit.ly", "tinyurl.com", "goo.gl", "ow.ly", "is.gd", "buff.ly", "cutt.ly", "linktr.ee")
        private val SHARED = setOf("facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com", "youtu.be", "tiktok.com", "telegram.me", "t.me", "whatsapp.com", "wa.me", "blogspot.com", "wordpress.com", "wixsite.com", "medium.com", "substack.com", "sites.google.com", "github.io", "netlify.app", "vercel.app", "google.com")

        internal fun collectDomains(rows: JSONArray, resolve: (String) -> String? = { null }): Set<String> {
            require(rows.length() in 1..100_000) { "Invalid Atlas collection size" }
            val domains = HashSet<String>()
            var shorteners = 0
            for (index in 0 until rows.length()) {
                val row = rows.getJSONObject(index)
                require(REQUIRED_FIELDS.all { row.has(it) } && row.has("media_channels")) { "Atlas schema changed" }
                require(row.getInt("id") > 0 && row.getString("nome_veiculo").isNotBlank()) { "Atlas identity changed" }
                if (row.optString("ativo") != "1" || !row.optString("segmento").equals("Online", true) ||
                    !row.isNull("data_fechamento")) continue
                val channels = row.getJSONArray("media_channels")
                for (channelIndex in 0 until channels.length()) {
                    val channel = channels.getJSONObject(channelIndex)
                    val type = channel.optJSONObject("channel") ?: continue
                    if (channel.optInt("channel_id") != 1 || type.optInt("id") != 1 ||
                        type.optString("name") != "Site" ||
                        (channel.has("deleted_at") && !channel.isNull("deleted_at")) ||
                        (channel.has("media_id") && channel.optInt("media_id") != row.getInt("id"))) continue
                    val raw = channel.optString("link")
                    val candidate = if (raw.contains("://")) raw else "https://$raw"
                    val initial = runCatching { publicHost(URI(candidate).host) }.getOrNull() ?: continue
                    val official = if (initial in SHORTENERS && shorteners++ < 20) resolve(candidate) else candidate
                    val host = runCatching { publicHost(URI(official).host) }.getOrNull() ?: continue
                    if (SHARED.none { host == it || host.endsWith(".$it") } && host !in SHORTENERS) domains.add(host)
                }
            }
            require(domains.isNotEmpty()) { "Atlas collection has no usable sites" }
            return domains
        }

        private fun readDomains(array: JSONArray): Set<String> = buildSet {
            for (index in 0 until array.length()) {
                val host = publicHost(array.optString(index)) ?: continue
                if (SHARED.none { host == it || host.endsWith(".$it") } && host !in SHORTENERS) add(host)
            }
        }

        private fun publicHost(value: String?): String? {
            val raw = value?.lowercase() ?: return null
            val host = runCatching { IDN.toASCII(raw).removePrefix("www.") }.getOrNull() ?: return null
            if (host.length > 253 || !host.contains('.') || host.endsWith(".local") || host == "localhost" ||
                host.matches(Regex("[0-9.]+")) || ':' in host ||
                !host.matches(Regex("[a-z0-9.-]+"))) return null
            return host
        }
    }
}
