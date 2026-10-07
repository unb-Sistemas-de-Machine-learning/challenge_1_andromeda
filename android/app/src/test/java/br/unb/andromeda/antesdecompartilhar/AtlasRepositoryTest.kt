package br.unb.andromeda.antesdecompartilhar

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class AtlasRepositoryTest {
    @Test fun acceptsOnlyActiveOnlineOfficialSiteChannels() {
        val rows = JSONArray()
            .put(row(1, "https://www.jornal.com.br/noticias"))
            .put(row(2, "https://facebook.com/veiculo"))
            .put(row(3, "https://outro.com.br", active = false))
            .put(row(4, "https://encerrado.com.br", closed = true))
            .put(row(5, "https://t.co/exemplo"))
            .put(row(6, "https://blogsite.com.br", wrongMedia = true))

        val domains = AtlasRepository.collectDomains(rows) { "https://destino.com.br/reportagem" }

        assertEquals(setOf("jornal.com.br", "destino.com.br"), domains)
    }

    @Test fun changedSchemaDoesNotPublishAnIncompleteCollection() {
        val rows = JSONArray().put(row(1, "https://jornal.com.br"))
            .put(JSONObject().put("id", 2).put("nome_veiculo", "Incompleto"))

        assertThrows(IllegalArgumentException::class.java) { AtlasRepository.collectDomains(rows) }
    }

    private fun row(id: Int, link: String, active: Boolean = true, closed: Boolean = false,
                    wrongMedia: Boolean = false): JSONObject {
        val channel = JSONObject().put("channel_id", 1).put("media_id", if (wrongMedia) id + 1 else id)
            .put("link", link).put("deleted_at", JSONObject.NULL)
            .put("channel", JSONObject().put("id", 1).put("name", "Site"))
        return JSONObject().put("id", id).put("nome_veiculo", "Veículo $id")
            .put("segmento", "Online").put("ativo", if (active) 1 else 0)
            .put("eh_jornal", 1).put("data_fechamento", if (closed) "2026-01-01" else JSONObject.NULL)
            .put("media_channels", JSONArray().put(channel))
    }
}
