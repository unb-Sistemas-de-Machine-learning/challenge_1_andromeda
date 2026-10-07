package br.unb.andromeda.antesdecompartilhar

import java.net.URI
import java.text.Normalizer

/** Editorial content is excluded before any factual verdict or Fact Check request. */
object OpinionFilter {
    private fun normalize(value: String): String = Normalizer.normalize(value.lowercase(), Normalizer.Form.NFD)
        .replace(Regex("\\p{M}+"), "")

    private val section = Regex("(?:^|[./])(?:opiniao|opinion|opinioes|editoria(?:l|is)|colunas?|colunistas?|blogs?|cronicas?|ponto-de-vista|tendencias-e-debates)(?:[./?#-]|$)")
    private val explicit = Regex("^\\s*(?:artigo de opiniao|opiniao|editorial|coluna|cronica|ponto de vista|carta do leitor)\\s*(?:[:|\\-–—]|$)|\\bartigo de opiniao\\b", RegexOption.MULTILINE)
    private val disclaimer = Regex("\\b(?:nao )?reflete(?:m)? (?:necessariamente )?(?:a )?(?:opiniao|posicao|linha editorial)\\b|\\b(?:e|sao) de (?:inteira |exclusiva )?responsabilidade (?:exclusiva )?d[oa]s? (?:autor|autora|colunista)")
    private val authorOpinion = Regex("\\b(?:na|em) minha (?:opiniao|visao|avaliacao)\\b|\\b(?:a|ao) meu ver\\b|\\bno meu (?:entender|entendimento|modo de ver)\\b|\\bdo meu ponto de vista\\b")
    private val firstPerson = Regex("\\b(?:eu )?(?:acho|acredito|penso|defendo|considero) que\\b|\\bsou (?:totalmente |plenamente )?(?:a favor|contra)\\b|\\bme parece (?:que|claro|evidente)\\b")
    private val prescriptive = Regex("\\b(?:deveria|deveriam|deveriamos|precisamos|temos que)\\b|\\be (?:preciso|urgente|necessario) que\\b")
    private val rhetorical = Regex("\\b(?:obviamente|evidentemente|sem duvida(?: alguma)?|convenhamos|fica claro que)\\b")

    fun isOpinionUrl(url: String): Boolean = try {
        val uri = URI(url)
        section.containsMatchIn(normalize("${uri.host ?: ""}${uri.path ?: ""}"))
    } catch (_: Exception) { false }

    fun isOpinionText(value: String): Boolean {
        val text = normalize(value.replace(Regex("\"[^\"]*\"|“[^”]*”|«[^»]*»"), " "))
        if (explicit.containsMatchIn(text) || disclaimer.containsMatchIn(text) || authorOpinion.containsMatchIn(text)) return true
        val score = (if (firstPerson.containsMatchIn(text)) 2 else 0) +
            (if (prescriptive.containsMatchIn(text)) 1 else 0) +
            (if (rhetorical.containsMatchIn(text)) 1 else 0)
        return score >= 3
    }
}
