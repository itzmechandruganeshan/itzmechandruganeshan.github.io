export const resumeData = {
    name: "Chandru Ganeshan",
    title: "AI/ML Engineer",
    contact: {
        email: "chandruganeshan24@gmail.com",
        phone: "+91 9087535918",
        linkedin: "https://linkedin.com/in/chandru-g24",
        location: "Coimbatore, India",
    },
    summary:
        "AI/ML Engineer specializing in **GenAI, RAG Systems, & Healthcare ML**. Experienced in designing and deploying **production-grade GenAI and machine learning systems**. Specialized in **LLM-powered applications, semantic search**, and **agent-based architectures** used in real-world environments.",
    experience: [
        {
            company: "Cloudside Technologies",
            role: "AI / ML Engineer",
            period: "01/2025 - Present",
            location: "Coimbatore",
            achievements: [
                "Architected an **agent-orchestrated financial chatbot** enabling natural-language queries over structured financial data.",
                "Designed routing logic across **FAQ retrieval, SQL generation, analytics**, and **forecasting agents**.",
                "Designed a modular multi-agent system automating **lead generation, enrichment**, and **multi-channel outreach workflows**.",
            ],
        },
        {
            company: "ISPG Technologies",
            role: "GenAI / ML Engineer Intern",
            period: "05/2024 - 12/2024",
            location: "Kochi",
            achievements: [
                "Independently architected and deployed a **production-grade RAG-based semantic search system** for automotive parts discovery.",
                "Built an end-to-end **semantic product search engine** supporting complex natural language queries with pricing constraints.",
                "Processed 10,000+ product category hierarchies with precomputed BERT embeddings, achieving **100% precision** by eliminating false-positive results.",
            ],
        },
        {
            company: "Microbiological Laboratory Pvt Ltd (MLRS)",
            role: "Data Scientist Intern",
            period: "01/2024 - 04/2024",
            location: "Coimbatore",
            achievements: [
                "Architected and developed an end-to-end ML system to automate **meningoencephalitis pathogen detection** from RTPCR data.",
                "Engineered **signal-processing pipelines** for HRM curves and amplification cycles with feature extraction and ML classification.",
                "Reduced diagnostic interpretation time from hours to minutes, enabling labs to process **100+ samples per day**.",
            ],
        },
    ],
    education: [
        {
            degree: "M.Sc. Data Analytics",
            institution: "Bharathiar University",
            period: "06/2022 - 06/2024",
        },
        {
            degree: "B.Sc. Statistics",
            institution: "Government Arts College",
            period: "06/2019 - 05/2022",
        },
    ],
    projects: [
        {
            name: "Tpay - AI-Powered Financial Chatbot",
            period: "01/2025 – Present",
            company: "Cloudside Technologies",
            description:
                "Engineered an **agent-orchestrated financial chatbot** for autonomous customer query handling.",
            summary:
                "Designed routing logic across FAQ retrieval, SQL generation, analytics, and forecasting agents within a single conversational flow. Implemented multilingual semantic search (English and Arabic) using FAISS.",
            impact: [
                "Enabled natural-language queries over structured financial data without SQL knowledge.",
                "Built natural language-to-SQL pipelines executing dynamic queries on BigQuery.",
                "Enabled multi-company data isolation and context-aware querying across 15+ financial categories.",
            ],
            skills: ["Python", "FastAPI", "LangChain", "Vertex AI", "BigQuery"],
        },
        {
            name: "Marketing & Sales Agent - In3",
            period: "01/2025 – Present",
            company: "Cloudside Technologies",
            description:
                "Developing an **Autonomous Sales & Marketing Agent** using **LLM-driven workflows**.",
            summary:
                "Designed a modular multi-agent system automating lead generation, enrichment, and multi-channel outreach workflows. Built and iterated specialized agents for marketing and campaign execution.",
            impact: [
                "Automated lead generation, enrichment, and multi-channel outreach workflows.",
                "Integrated CRM APIs and deployed containerized services with a UI for campaign management.",
                "Built and iterated 5+ specialized agents for marketing, sales, and campaign execution.",
            ],
            skills: ["Python", "Gemini LLM", "Vertex AI", "Docker", "Streamlit", "Google ADK"],
        },
        {
            name: "Semantic Product Search Engine - PNG Jewellery",
            period: "07/2024 - 09/2024",
            company: "ISPG Technologies",
            description:
                "Built an end-to-end **semantic product search engine** supporting complex queries.",
            summary:
                "Implemented embedding-based similarity matching, NLP-driven price extraction, and relevancy validation logic. Processed 10,000+ product category hierarchies with precomputed BERT embeddings.",
            impact: [
                "Achieved 100% precision by eliminating false-positive results.",
                "Reduced latency by ~40%.",
                "Supported complex natural language queries with pricing constraints.",
            ],
            skills: ["Python", "FastAPI", "Sentence Transformers", "spaCy", "Docker"],
        },
        {
            name: "Production Semantic Search Engine - Mopare",
            period: "08/2024 - 10/2024",
            company: "ISPG Technologies",
            description:
                "Architected and deployed a **production-grade RAG-based semantic search system**.",
            summary:
                "Indexed millions of products with vehicle fitment compatibility data using transformer embeddings and parallel vector search for automotive parts discovery.",
            impact: [
                "Achieved sub-500ms query latency through concurrent processing and optimized routing logic.",
                "Indexed millions of products with vehicle fitment compatibility data.",
                "Deployed containerized FastAPI services on Kubernetes with Jenkins-based CI/CD pipelines.",
            ],
            skills: ["Python", "FastAPI", "Sentence Transformers", "Docker", "AWS Bedrock"],
        },
        {
            name: "PyMLRS - ML-Based Pathogen Detection System",
            period: "01/2024 - 04/2024",
            company: "MLRS",
            description:
                "Developed an **end-to-end ML system** to automate meningoencephalitis pathogen detection.",
            summary:
                "Engineered signal-processing pipelines for HRM curves and amplification cycles. Published as a production-ready PyPI package for healthcare workflows.",
            impact: [
                "Reduced diagnostic interpretation time from hours to minutes.",
                "Enabled labs to process 100+ samples per day.",
                "Supported detection of 8 clinical pathogens with automated, clinical-grade PDF diagnostic reports.",
            ],
            github: "https://pypi.org/project/PyMLRS/",
            skills: ["Python", "SciPy", "NumPy", "Pandas", "Scikit-learn"],
        },
        {
            name: "Rextractor (Open Source)",
            period: "2024",
            company: "Open Source",
            description:
                "Tool for parsing proprietary RT-PCR.rex files into structured datasets.",
            summary:
                "Developed an open-source tool for parsing proprietary RT-PCR.rex files into structured datasets, facilitating research and data extraction.",
            impact: [
                "Enabled extraction and standardizing of complex RT-PCR data.",
                "Facilitated reproducible research through structured data outputs.",
            ],
            github: "https://github.com/itzmechandruganeshan/REXTRACTOR",
            skills: ["Python", "Data Processing", "Parsing"],
        }
    ],
    skills: {
        core: [
            "Python",
            "Machine Learning",
            "Deep Learning",
            "Generative AI",
            "Agentic AI",
            "RAG Pipelines",
            "Semantic Search",
            "Vector Embeddings"
        ],
        frameworks: [
            "LangChain",
            "LangGraph",
            "Google ADK",
            "TensorFlow",
            "Scikit-Learn",
            "Sentence Transformers",
            "spaCy"
        ],
        cloud_devops: [
            "Google Cloud Platform",
            "Vertex AI",
            "BigQuery",
            "Docker",
            "Kubernetes",
            "AWS Bedrock"
        ],
        databases: ["FAISS"],
        tools: ["FastAPI", "Flask", "Streamlit", "Pandas", "NumPy", "SciPy", "Matplotlib", "Plotly"],
    },
};
