package br.unb.andromeda.antesdecompartilhar

import kotlin.math.round

data class CriterionBreakdown(
    val symbol: String,
    val name: String,
    val score: Double?,
    val intendedWeight: Double,
    val effectiveWeight: Double?,
    val contribution: Double?
)

data class ScoreBreakdown(
    val criteria: List<CriterionBreakdown>,
    val sourceSignals: List<SourceSignal>,
    val sourceCoverage: Int,
    val coverage: Int,
    val formula: String,
    val scoreBeforeVeto: Double,
    val sourceVetoApplied: Boolean,
    val finalScore: Double
)

/** Same weighted available-criterion mean and source cap as sdd_v1 aggregation. */
object ScoreCalculator {
    fun calculate(fact: Double?, source: SourceAssessment, writing: Double?): ScoreBreakdown {
        val values = listOf(Triple("F", "Checagem factual", fact),
            Triple("C", "Credibilidade da fonte", source.score / 100.0),
            Triple("W", "Estilo de escrita", writing))
        val weights = listOf(0.65, 0.20, 0.15)
        val active = values.indices.filter { values[it].third != null }
        val denominator = active.sumOf { weights[it] }
        val criteria = values.indices.map { index ->
            val value = values[index].third
            val effective = if (value == null) null else weights[index] / denominator
            CriterionBreakdown(values[index].first, values[index].second, value,
                weights[index], effective, if (value == null) null else value * effective!! * 100)
        }
        val beforeVeto = round4(criteria.sumOf { it.contribution ?: 0.0 })
        val veto = source.veto
        val score = if (veto) minOf(beforeVeto, 35.0) else beforeVeto
        val numerator = active.joinToString(" + ") { "${"%.2f".format(java.util.Locale.US, weights[it])} × ${values[it].first}" }
        val baseFormula = "($numerator)" +
            if (denominator == 1.0) " × 100" else " / ${"%.2f".format(java.util.Locale.US, denominator)} × 100"
        val formula = if (veto) "mín(35, $baseFormula)" else baseFormula
        return ScoreBreakdown(criteria, source.signals, source.coverage, round(denominator * 100).toInt(),
            formula, beforeVeto, veto, score)
    }

    private fun round4(value: Double): Double = round(value * 10_000) / 10_000
}
