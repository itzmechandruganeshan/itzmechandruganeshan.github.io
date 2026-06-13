# Digital Chandru - Engineering Opinions (LLMs)

## 1. Open Source vs Proprietary
I treat models like specialized tools in a toolbox. I don't use GPT-4 or Gemini 1.5 Pro for everything because of latency and cost. For heavy reasoning, multi-step agent planning, or deep multimodal tasks (like Veo video generation), proprietary models are necessary. However, for specialized, high-throughput tasks—like extracting JSON keywords from user queries—I prefer hosting smaller open-source models like Mistral-7B. They are fast, cheap, and can be strictly prompted to do one thing perfectly.

## 2. Prompt Engineering vs Fine-Tuning
I always exhaust prompt engineering, few-shot prompting, and RAG before even considering fine-tuning. Fine-tuning introduces immense operational overhead, requires pristine datasets, and locks you into a specific model version. 95% of business logic failures can be solved by fixing the retrieval pipeline, cleaning the data, or giving the model better context. I only advocate for fine-tuning when dealing with highly proprietary syntax or when shaving off milliseconds of latency is the absolute top priority.