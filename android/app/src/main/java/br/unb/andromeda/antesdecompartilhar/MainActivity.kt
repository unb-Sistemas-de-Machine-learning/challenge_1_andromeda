package br.unb.andromeda.antesdecompartilhar

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.Uri
import android.os.Bundle
import android.view.View
import android.view.WindowInsets
import android.view.inputmethod.InputMethodManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var pipeline: NewsPipeline
    private lateinit var content: LinearLayout
    private var mode = Mode.TITLE
    private var value = ""
    private var candidates = emptyList<ArticleCandidate>()
    private var message = ""
    private var busy = false

    private enum class Mode { TITLE, URL }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        pipeline = NewsPipeline(this)
        window.statusBarColor = Color.rgb(11, 38, 49)
        window.navigationBarColor = Color.rgb(246, 249, 247)
        val scroll = ScrollView(this).apply { setBackgroundColor(Color.rgb(246, 249, 247)) }
        content = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(28), dp(24), dp(28))
        }
        scroll.addView(content)
        scroll.setOnApplyWindowInsetsListener { _, insets ->
            val top = if (android.os.Build.VERSION.SDK_INT >= 30) insets.getInsets(WindowInsets.Type.systemBars()).top else insets.systemWindowInsetTop
            val bottom = if (android.os.Build.VERSION.SDK_INT >= 30) insets.getInsets(WindowInsets.Type.systemBars()).bottom else insets.systemWindowInsetBottom
            content.setPadding(dp(24), dp(28) + top, dp(24), dp(28) + bottom)
            insets
        }
        setContentView(scroll)
        renderEntry()
    }

    override fun onDestroy() {
        worker.shutdownNow()
        super.onDestroy()
    }

    private fun renderHeader() {
        content.removeAllViews()
        content.addView(label("◈  Antes de compartilhar", 18f, Color.rgb(13, 54, 66), true))
        space(36)
    }

    private fun renderEntry() {
        renderHeader()
        content.addView(label("VERIFIQUE COM CALMA", 12f, Color.rgb(37, 110, 98), true))
        space(10)
        content.addView(label("Qual notícia você leu?", 30f, Color.rgb(11, 38, 49), true))
        space(10)
        content.addView(label("Encontre a reportagem pelo título ou use o link que você já tem.", 16f, Color.rgb(76, 94, 99)))
        space(24)
        val tabs = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL }
        tabs.addView(action("Tenho o título", mode == Mode.TITLE, 1f) {
            value = ""; message = ""; mode = Mode.TITLE; renderEntry()
        })
        tabs.addView(action("Tenho o link", mode == Mode.URL, 1f) {
            value = ""; message = ""; mode = Mode.URL; renderEntry()
        })
        content.addView(tabs)
        space(28)
        content.addView(label(if (mode == Mode.TITLE) "Título da notícia" else "Link da reportagem", 15f, Color.rgb(11, 38, 49), true))
        space(8)
        val input = EditText(this).apply {
            setSingleLine(true)
            setText(value)
            hint = if (mode == Mode.TITLE) "Digite o título que você lembra" else "https://site.com.br/noticia"
            textSize = 16f
            setPadding(dp(14), dp(12), dp(14), dp(12))
            background = rounded(Color.WHITE, Color.rgb(180, 198, 199))
            inputType = android.text.InputType.TYPE_CLASS_TEXT or
                (if (mode == Mode.URL) android.text.InputType.TYPE_TEXT_VARIATION_URI else 0)
        }
        content.addView(input, LinearLayout.LayoutParams(-1, dp(54)))
        space(18)
        content.addView(action(if (mode == Mode.TITLE) "Buscar notícia" else "Analisar notícia", true) {
            value = input.text.toString().trim()
            hideKeyboard(input)
            if (mode == Mode.TITLE) search() else analyzeLink()
        })
        if (message.isNotBlank()) { space(18); content.addView(feedback(message)) }
        scopeNote()
    }

    private fun search() {
        if (value.length !in 12..180 || value.split(Regex("\\s+")).size < 3) {
            message = "Digite pelo menos três palavras do título, com 12 a 180 caracteres."
            renderEntry(); return
        }
        if (OpinionFilter.isOpinionText(value)) {
            message = "Esse título parece ser de opinião ou editorial. Procure uma reportagem factual."
            renderEntry(); return
        }
        runTask("Buscando reportagens", { pipeline.searchByTitle(value) }) { found ->
            candidates = found
            message = if (found.isEmpty()) "Nenhuma reportagem correspondente foi encontrada. Tente outro título ou cole o link." else ""
            renderChoices()
        }
    }

    private fun analyzeLink() {
        val url = try { pipeline.normalizeArticleUrl(value) } catch (error: Exception) {
            message = error.message ?: "Confira o link da reportagem."
            renderEntry(); return
        }
        if (OpinionFilter.isOpinionUrl(url)) {
            message = "Este link aponta para opinião, coluna ou editorial e não será avaliado como notícia."
            renderEntry(); return
        }
        analyze(url)
    }

    private fun renderChoices() {
        renderHeader()
        content.addView(action("← Voltar à busca", false) { message = ""; renderEntry() })
        space(20)
        content.addView(label("Escolha a reportagem", 28f, Color.rgb(11, 38, 49), true))
        space(8)
        content.addView(label("Confirme o título e o veículo antes de analisar. A busca não confirma os fatos.", 15f, Color.rgb(76, 94, 99)))
        space(20)
        for (candidate in candidates) {
            content.addView(action("${candidate.title}\n${candidate.publisher}", false) { analyze(candidate.url) })
            space(10)
        }
        if (message.isNotBlank()) content.addView(feedback(message))
        scopeNote()
    }

    private fun analyze(url: String) {
        runTask("Analisando a notícia", { pipeline.analyze(url) }) { result -> renderResult(result) }
    }

    private fun renderResult(result: AnalysisResult) {
        renderHeader()
        content.addView(label("RESULTADO DA ANÁLISE", 12f, Color.rgb(37, 110, 98), true))
        space(10)
        content.addView(label("Por que esta notícia recebeu esta avaliação?", 28f, Color.rgb(11, 38, 49), true))
        space(20)
        content.addView(label(result.title, 18f, Color.rgb(11, 38, 49), true))
        space(18)
        content.addView(label(result.explanation, 16f, Color.rgb(24, 57, 62)).apply {
            setPadding(dp(18), dp(18), dp(18), dp(18))
            background = rounded(Color.WHITE, Color.rgb(194, 214, 209))
        })
        space(8)
        content.addView(label("Resumo baseado nos critérios da análise.", 13f, Color.rgb(91, 107, 111)))
        if (result.evidence.isNotEmpty()) {
            space(18)
            content.addView(action("Ver checagens relacionadas", false) {
                showEvidence(result.evidence)
            })
        }
        space(18)
        content.addView(action("Abrir reportagem original", false) {
            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(result.url)))
        })
        space(10)
        content.addView(action("Analisar outra notícia", true) {
            mode = Mode.TITLE; value = ""; message = ""; candidates = emptyList(); renderEntry()
        })
        scopeNote()
    }

    private fun showEvidence(evidence: List<FactEvidence>) {
        val ink = Color.rgb(11, 38, 49)
        val muted = Color.rgb(58, 79, 83)
        val dialog = AlertDialog.Builder(this).create()
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), dp(22), dp(20), dp(20))
            background = rounded(Color.rgb(246, 249, 247), Color.rgb(194, 214, 209))
        }
        root.addView(label("Checagens relacionadas", 22f, ink, true))
        root.addView(label("${evidence.size} ${if (evidence.size == 1) "checagem encontrada" else "checagens encontradas"}", 16f, muted, true))
        root.addView(View(this), LinearLayout.LayoutParams(1, dp(10)))
        root.addView(label("Leia cada veredito e abra a checagem completa para conferir o contexto.", 16f, muted))
        root.addView(View(this), LinearLayout.LayoutParams(1, dp(18)))
        val list = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }
        for (review in evidence) {
            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(dp(16), dp(18), dp(16), dp(16))
                background = rounded(Color.WHITE, Color.rgb(185, 207, 202))
            }
            card.addView(label(review.publisher, 19f, ink, true))
            if (review.title.isNotBlank()) {
                card.addView(View(this), LinearLayout.LayoutParams(1, dp(8)))
                card.addView(label(review.title, 17f, ink, true))
            }
            if (review.reviewDate.length >= 10) {
                card.addView(View(this), LinearLayout.LayoutParams(1, dp(8)))
                val date = review.reviewDate.take(10)
                val readableDate = if (date.matches(Regex("\\d{4}-\\d{2}-\\d{2}")))
                    "${date.substring(8, 10)}/${date.substring(5, 7)}/${date.substring(0, 4)}" else date
                card.addView(label("Publicada em $readableDate", 15f, muted))
            }
            card.addView(View(this), LinearLayout.LayoutParams(1, dp(12)))
            card.addView(label("VEREDITO", 13f, Color.rgb(37, 110, 98), true))
            card.addView(label(review.verdict.ifBlank { "Não informado" }, 18f, ink, true))
            card.addView(View(this), LinearLayout.LayoutParams(1, dp(12)))
            card.addView(label("AFIRMAÇÃO CHECADA", 13f, Color.rgb(37, 110, 98), true))
            card.addView(label(review.claim, 16f, ink))
            card.addView(View(this), LinearLayout.LayoutParams(1, dp(16)))
            card.addView(action("Ler checagem completa ↗", true, onClick = {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(review.url)))
            }).apply {
                textSize = 16f
                setTypeface(null, Typeface.BOLD)
            })
            list.addView(card, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
        }
        val scroll = ScrollView(this).apply {
            addView(list)
            isVerticalScrollBarEnabled = true
        }
        val maxListHeight = (resources.displayMetrics.heightPixels * 0.52f).toInt()
        root.addView(scroll, LinearLayout.LayoutParams(-1, minOf(dp(evidence.size * 260), maxListHeight)))
        root.addView(View(this), LinearLayout.LayoutParams(1, dp(8)))
        root.addView(action("Fechar", false) { dialog.dismiss() })
        dialog.setView(root)
        dialog.show()
        dialog.window?.setBackgroundDrawableResource(android.R.color.transparent)
        dialog.window?.setLayout((resources.displayMetrics.widthPixels * 0.92f).toInt(), -2)
    }

    private fun <T> runTask(title: String, task: () -> T, complete: (T) -> Unit) {
        if (busy) return
        busy = true
        renderHeader()
        content.addView(label(title, 28f, Color.rgb(11, 38, 49), true))
        space(12)
        content.addView(label("Isso pode levar alguns instantes.", 16f, Color.rgb(76, 94, 99)))
        worker.execute {
            try {
                val result = task()
                runOnUiThread { busy = false; complete(result) }
            } catch (error: Exception) {
                runOnUiThread {
                    busy = false
                    message = error.message ?: "Não foi possível concluir a análise. Verifique a conexão e tente novamente."
                    if (mode == Mode.TITLE && candidates.isNotEmpty()) renderChoices() else renderEntry()
                }
            }
        }
    }

    private fun label(text: String, size: Float, color: Int, bold: Boolean = false): TextView = TextView(this).apply {
        this.text = text
        textSize = size
        setTextColor(color)
        if (bold) setTypeface(null, Typeface.BOLD)
        setLineSpacing(dp(3).toFloat(), 1f)
    }

    private fun feedback(text: String): TextView = label(text, 15f, Color.rgb(135, 47, 39)).apply {
        setPadding(dp(12), dp(12), dp(12), dp(12))
        background = rounded(Color.rgb(255, 238, 235), Color.rgb(234, 180, 174))
    }

    private fun action(text: String, primary: Boolean, weight: Float = 0f, onClick: () -> Unit): Button = Button(this).apply {
        this.text = text
        textSize = 15f
        isAllCaps = false
        setTextColor(if (primary) Color.WHITE else Color.rgb(13, 54, 66))
        background = rounded(if (primary) Color.rgb(13, 91, 82) else Color.WHITE, Color.rgb(171, 199, 194))
        setOnClickListener { onClick() }
        if (weight > 0f) layoutParams = LinearLayout.LayoutParams(0, dp(52), weight)
        else layoutParams = LinearLayout.LayoutParams(-1, -2)
        minHeight = dp(50)
    }

    private fun rounded(fill: Int, border: Int) = GradientDrawable().apply {
        setColor(fill)
        cornerRadius = dp(12).toFloat()
        setStroke(dp(1), border)
    }

    private fun scopeNote() {
        space(30)
        content.addView(label("A avaliação pode ser parcial e não substitui a leitura das fontes. Artigos de opinião não recebem veredito factual.", 13f, Color.rgb(91, 107, 111)))
    }

    private fun space(height: Int) { content.addView(View(this), LinearLayout.LayoutParams(1, dp(height))) }
    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
    private fun hideKeyboard(view: View) { (getSystemService(INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(view.windowToken, 0) }
}
