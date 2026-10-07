package br.unb.andromeda.antesdecompartilhar

import android.content.Context
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.LongBuffer

/** Runs the bundled quantized model on device. No article text leaves this class. */
class BertimbauClassifier(private val context: Context) {
    data class Result(val writingScore: Float)

    private val vocabulary: Map<String, Int> by lazy {
        context.assets.open("model/vocab.txt").bufferedReader().useLines { lines ->
            lines.mapIndexed { index, token -> token to index }.toMap()
        }
    }

    private val session: OrtSession by lazy {
        val model = File(context.filesDir, "writing_bertimbau.int8.onnx")
        if (!model.exists() || model.length() != MODEL_BYTES) {
            context.assets.open("model/model.int8.onnx").use { input ->
                model.outputStream().use { output -> input.copyTo(output) }
            }
        }
        OrtEnvironment.getEnvironment().createSession(model.absolutePath)
    }

    fun classify(text: String): Result? = try {
        val segments = tokenize(text)
        require(segments.isNotEmpty())
        val environment = OrtEnvironment.getEnvironment()
        val shape = longArrayOf(1, MAX_TOKENS.toLong())
        var weightedScore = 0.0
        var totalCharacters = 0
        for (segment in segments) {
            val mask = LongArray(MAX_TOKENS) { if (it < segment.tokenCount) 1L else 0L }
            OnnxTensor.createTensor(environment, LongBuffer.wrap(segment.ids), shape).use { inputIds ->
                OnnxTensor.createTensor(environment, LongBuffer.wrap(mask), shape).use { attentionMask ->
                    OnnxTensor.createTensor(environment, LongBuffer.wrap(LongArray(MAX_TOKENS)), shape).use { tokenTypes ->
                        session.run(mapOf(
                            "input_ids" to inputIds,
                            "attention_mask" to attentionMask,
                            "token_type_ids" to tokenTypes
                        )).use { output ->
                            val logits = (output[0].value as Array<*>)[0] as FloatArray
                            val maximum = maxOf(logits[0], logits[1])
                            val a = kotlin.math.exp((logits[0] - maximum).toDouble())
                            val b = kotlin.math.exp((logits[1] - maximum).toDouble())
                            weightedScore += b / (a + b) * segment.characterCount
                            totalCharacters += segment.characterCount
                        }
                    }
                }
            }
        }
        Result((weightedScore / totalCharacters).toFloat())
    } catch (_: Exception) {
        null
    }

    private data class Segment(val ids: LongArray, val tokenCount: Int, val characterCount: Int)

    private fun tokenize(text: String): List<Segment> {
        val normalized = text.trim().replace(Regex("\\s+"), " ")
        val words = Regex("[\\p{L}\\p{N}_]+|[^\\s]").findAll(normalized)
        val result = ArrayList<Segment>()
        val pieces = ArrayList<Int>(MAX_TOKENS)
        pieces.add(vocabulary["[CLS]"] ?: 101)
        var previousEnd = 0
        var segmentEnd = 0
        fun finishSegment() {
            if (pieces.size <= 1) return
            pieces.add(vocabulary["[SEP]"] ?: 102)
            result.add(Segment(LongArray(MAX_TOKENS) { if (it < pieces.size) pieces[it].toLong() else 0L },
                pieces.size, segmentEnd - previousEnd))
            previousEnd = segmentEnd
            pieces.clear()
            pieces.add(vocabulary["[CLS]"] ?: 101)
        }
        for (word in words) {
            val value = word.value
            if (value.length > 100) {
                if (pieces.size >= MAX_TOKENS - 1) finishSegment()
                pieces.add(vocabulary["[UNK]"] ?: 100)
                segmentEnd = word.range.last + 1
                continue
            }
            var start = 0
            val wordPieces = ArrayList<Int>()
            while (start < value.length) {
                var end = value.length
                var found: Int? = null
                while (end > start) {
                    val candidate = (if (start == 0) "" else "##") + value.substring(start, end)
                    found = vocabulary[candidate]
                    if (found != null) break
                    end--
                }
                if (found == null) { wordPieces.clear(); wordPieces.add(vocabulary["[UNK]"] ?: 100); break }
                wordPieces.add(found)
                start = end
            }
            for (piece in wordPieces) {
                if (pieces.size >= MAX_TOKENS - 1) finishSegment()
                pieces.add(piece)
                segmentEnd = word.range.last + 1
            }
        }
        finishSegment()
        return result
    }

    companion object {
        private const val MAX_TOKENS = 512
        private const val MODEL_BYTES = 109713262L
    }
}
