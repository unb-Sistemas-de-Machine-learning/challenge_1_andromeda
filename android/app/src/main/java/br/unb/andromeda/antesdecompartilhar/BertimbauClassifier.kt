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
        val ids = tokenize(text)
        val mask = LongArray(MAX_TOKENS) { if (it < ids.second) 1L else 0L }
        val types = LongArray(MAX_TOKENS)
        val environment = OrtEnvironment.getEnvironment()
        val shape = longArrayOf(1, MAX_TOKENS.toLong())
        OnnxTensor.createTensor(environment, LongBuffer.wrap(ids.first), shape).use { inputIds ->
            OnnxTensor.createTensor(environment, LongBuffer.wrap(mask), shape).use { attentionMask ->
                OnnxTensor.createTensor(environment, LongBuffer.wrap(types), shape).use { tokenTypes ->
                    session.run(mapOf(
                        "input_ids" to inputIds,
                        "attention_mask" to attentionMask,
                        "token_type_ids" to tokenTypes
                    )).use { output ->
                        val logits = (output[0].value as Array<*>)[0] as FloatArray
                        val maximum = maxOf(logits[0], logits[1])
                        val a = kotlin.math.exp((logits[0] - maximum).toDouble())
                        val b = kotlin.math.exp((logits[1] - maximum).toDouble())
                        // The pinned sdd_v1 model maps index 0 to Fake and index 1 to True.
                        Result((b / (a + b)).toFloat())
                    }
                }
            }
        }
    } catch (_: Exception) {
        null
    }

    private fun tokenize(text: String): Pair<LongArray, Int> {
        val words = Regex("[\\p{L}\\p{N}_]+|[^\\s]").findAll(text.take(20_000)).map { it.value }.toList()
        val pieces = ArrayList<Int>(MAX_TOKENS)
        pieces.add(vocabulary["[CLS]"] ?: 101)
        for (word in words) {
            if (pieces.size >= MAX_TOKENS - 1) break
            if (word.length > 100) { pieces.add(vocabulary["[UNK]"] ?: 100); continue }
            var start = 0
            val wordPieces = ArrayList<Int>()
            while (start < word.length) {
                var end = word.length
                var found: Int? = null
                while (end > start) {
                    val candidate = (if (start == 0) "" else "##") + word.substring(start, end)
                    found = vocabulary[candidate]
                    if (found != null) break
                    end--
                }
                if (found == null) { wordPieces.clear(); wordPieces.add(vocabulary["[UNK]"] ?: 100); break }
                wordPieces.add(found)
                start = end
            }
            for (piece in wordPieces) {
                if (pieces.size >= MAX_TOKENS - 1) break
                pieces.add(piece)
            }
        }
        pieces.add(vocabulary["[SEP]"] ?: 102)
        return LongArray(MAX_TOKENS) { if (it < pieces.size) pieces[it].toLong() else 0L } to pieces.size
    }

    companion object {
        private const val MAX_TOKENS = 256
        private const val MODEL_BYTES = 109713262L
    }
}
