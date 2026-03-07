<br />

Built to refine the performance and reliability of the Gemini 3 Pro series,
Gemini 3.1 Pro Preview provides better thinking, improved token
efficiency, and a more grounded, factually consistent experience. It's optimized
for software engineering behavior and usability, as well as agentic workflows
requiring precise tool usage and reliable multi-step execution across real-world
domains.
[Try in Google AI Studio](https://aistudio.google.com/prompts/new_chat?model=gemini-3.1-pro-preview)

## Documentation

Visit the [Gemini 3 Developer Guide](https://ai.google.dev/gemini-api/docs/gemini-3) page for full
coverage of features and capabilities.

## gemini-3.1-pro-preview

| Property | Description |
|---|---|
| Model code | `gemini-3.1-pro-preview` |
| Supported data types | **Inputs** Text, Image, Video, Audio, and PDF **Output** Text |
| Token limits^[\[\*\]](https://ai.google.dev/gemini-api/docs/tokens)^ | **Input token limit** 1,048,576 **Output token limit** 65,536 |
| Capabilities | **Audio generation** Not supported **Batch API** Supported **Caching** Supported **Code execution** Supported **File search** Supported (AI Studio only) **Function calling** Supported **Grounding with Google Maps** Not supported **Image generation** Not supported **Live API** Not supported **Search grounding** Supported **Structured outputs** Supported **Thinking** Supported **URL context** Supported |
| Versions | Read the [model version patterns](https://ai.google.dev/gemini-api/docs/models/gemini#model-versions) for more details. - Preview: `gemini-3.1-pro-preview` - Preview: `gemini-3.1-pro-preview-customtools` \* |
| Latest update | February 2026 |
| Knowledge cutoff | January 2025 |

#### gemini-3.1-pro-preview-customtools

\* *For those building with a mix of bash and custom tools, Gemini 3.1 Pro Preview
comes with a separate endpoint available via the API called
`gemini-3.1-pro-preview-customtools`. This endpoint is better at prioritizing
your custom tools (for example `view_file` or `search_code`).*

*Note that while `gemini-3.1-pro-preview-customtools` is optimized for agentic
workflows that use custom tools and bash, you may see quality fluctuations in
some use cases which don't benefit from such tools.*

Last week, we released a major update to Gemini 3 Deep Think to solve modern challenges across science, research and engineering. Today, we’re releasing the upgraded core intelligence that makes those breakthroughs possible: Gemini 3.1 Pro. We are shipping 3.1 Pro across our consumer and developer products to bring this progress in intelligence to your everyday applications.

Starting today, 3.1 Pro is rolling out:

For developers in preview via the Gemini API in Google AI Studio, Gemini CLI, our agentic development platform Google Antigravity and Android Studio
For enterprises in Vertex AI and Gemini Enterprise
For consumers via the Gemini app and NotebookLM
Building on the Gemini 3 series, 3.1 Pro represents a step forward in core reasoning. 3.1 Pro is a smarter, more capable baseline for complex problem-solving. This is reflected in our progress on rigorous benchmarks. On ARC-AGI-2, a benchmark that evaluates a model’s ability to solve entirely new logic patterns, 3.1 Pro achieved a verified score of 77.1%. This is more than double the reasoning performance of 3 Pro.

Side-by-side comparison of different benchmarks for AI models.
Intelligence applied
3.1 Pro is designed for tasks where a simple answer isn’t enough, taking advanced reasoning and making it useful for your hardest challenges. This improved intelligence can help in practical applications — whether you’re looking for a clear, visual explanation of a complex topic, a way to synthesize data into a single view, or bringing a creative project to life.



Code-based animation: 3.1 Pro can generate website-ready, animated SVGs directly from a text prompt. Because these are built in pure code rather than pixels, they remain crisp at any scale and maintain incredibly small file sizes compared to traditional video.




Jump to position 1
Jump to position 2
Jump to position 3
Jump to position 4
What’s next
Since releasing Gemini 3 Pro in November, your feedback and the pace of progress have driven these rapid improvements. We are releasing 3.1 Pro in preview today to validate these updates and continue to make further advancements in areas such as ambitious agentic workflows before we make it generally available soon.

Starting today, Gemini 3.1 Pro in the Gemini app is rolling out with higher limits for users with the Google AI Pro and Ultra plans. 3.1 Pro is also now available on NotebookLM exclusively for Pro and Ultra users. And developers and enterprises can access 3.1 Pro now in preview in the Gemini API via AI Studio, Antigravity, Vertex AI, Gemini Enterprise, Gemini CLI and Android Studio.

We can’t wait to see what you build and discover with it.

Gemini 3.1 Flash-Lite: Built for intelligence at scale
Mar 03, 2026

7 min read

Get best-in-class intelligence for your highest-volume workloads.

T
The Gemini Team
 Read AI-generated summary 
Share
Gemini 3.1 Flash Lite logo

Listen to article 
3:18 minutes
Today, we're introducing Gemini 3.1 Flash-Lite, our fastest and most cost-efficient Gemini 3 series model. Built for high-volume developer workloads at scale, 3.1 Flash-Lite delivers high quality for its price and model tier.

Starting today, 3.1 Flash-Lite is rolling out in preview to developers via the Gemini API in Google AI Studio and for enterprises via Vertex AI.

Cost-efficiency without compromise
Priced at just $0.25/1M input tokens and $1.50/1M output tokens, 3.1 Flash-Lite delivers enhanced performance at a fraction of the cost of larger models. It outperforms 2.5 Flash with a 2.5X faster Time to First Answer Token and 45% increase in output speed, according to the Artificial Analysis benchmark while maintaining similar or better quality. This low latency is needed for high-frequency workflows, making it an ideal model for developers to build responsive, real-time experiences.

The image shows two bar charts titled "Speed & Cost Efficiency," comparing the "Output speed (higher is better)" and "Price (lower is better)" of Gemini 3.1 Flash-Lite against several other models, including Gemini 2.5 Flash-Lite, GPT-5 mini, Claude 4.5 Haiku, and Grok 4.1 Fast.

Gemini 3.1 Flash-Lite outperforms 2.5 Flash in speed and quality.

3.1 Flash-Lite achieves an impressive Elo score of 1432 on the Arena.ai Leaderboard and outperforms other models of similar tier across reasoning and multimodal understanding benchmarks, including 86.9% on GPQA Diamond and 76.8% on MMMU Pro–even surpassing larger Gemini models from prior generations like 2.5 Flash.

The image displays a comparison table of several AI models, including "Gemini 3.1 Flash-Lite," "Gemini 2.5 Dynamic," "Gemini 2.5 Flash-Lite," "GPT-5 mini," "Claude 4.5 Haiku," and "Grok 4.1 Fast," across various metrics such as input/output price, output speed, and different academic, reasoning, and factual benchmarks.
Adaptive intelligence at scale for developers
Beyond its raw performance, Gemini 3.1 Flash-Lite comes standard with thinking levels in AI Studio and Vertex AI, giving developers the control and flexibility to select how much the model “thinks” for a task, which is critical for managing high-frequency workloads. 3.1 Flash-Lite can tackle tasks at scale, like high-volume translation and content moderation, where cost is a priority. And it can also handle more complex workloads where more in-depth reasoning is needed, like generating user interfaces and dashboards, creating simulations or following instructions.



3.1 Flash-Lite instantly fills an e-commerce wireframe with hundreds of products in different categories.




Jump to position 1
Jump to position 2
Jump to position 3
Jump to position 4
Early-access developers on AI Studio and Vertex AI, and companies like Latitude, Cartwheel and Whering are already using 3.1 Flash-Lite to solve complex problems at scale. Early testers highlighted 3.1 Flash-Lite’s efficiency and reasoning capabilities, saying it can handle complex inputs with the precision of a larger-tier model, plus follow instructions and maintain adherence.