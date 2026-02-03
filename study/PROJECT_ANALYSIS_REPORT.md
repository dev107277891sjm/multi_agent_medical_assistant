# Multi-Agent Medical Assistant — Project Analysis Report

**Report Date:** January 30, 2025  
**Project:** Multi-Agent Medical Assistant (AI-powered medical diagnosis and assistance)  
**Version:** 2.0+

---

## 1. Executive Summary

The **Multi-Agent Medical Assistant** is an AI-powered chatbot that combines **multi-agent orchestration**, **RAG (Retrieval-Augmented Generation)**, **medical imaging analysis**, **web search**, and **human-in-the-loop validation** to support medical diagnosis, research, and patient interactions. The system is built with **FastAPI**, **LangGraph**, **LangChain**, **Qdrant**, **Docling**, and **PyTorch**-based computer vision models.

Key findings:
- **Architecture:** Central orchestrator (LangGraph) routes queries to specialized agents (Conversation, RAG, Web Search, Chest X-ray, Skin Lesion; Brain Tumor is stubbed).
- **RAG pipeline:** Docling parsing → LLM image summarization → semantic chunking → Qdrant hybrid (dense + BM25) → cross-encoder reranking → LLM response with source links.
- **Safety:** Input/output guardrails (LLM-based), confidence-based RAG→Web Search handoff, and human validation for imaging agents.
- **Deployment:** Docker, GitHub Actions CI for image build; requires Azure OpenAI, ElevenLabs, Tavily, HuggingFace, and optional Qdrant server.

---

## 2. Project Overview & Purpose

### 2.1 Goals

- Assist with **medical diagnosis**, **research**, and **patient interactions** via a single chat interface.
- Provide **accurate**, **reliable**, and **up-to-date** medical insights using:
  - Established medical literature (RAG over ingested PDFs).
  - Real-time web search when RAG confidence is low or information is insufficient.
  - Task-specific computer vision for chest X-ray (COVID/normal), skin lesion segmentation; brain tumor is planned.
- Ensure **safety** through guardrails and **human-in-the-loop** validation for imaging outputs.

### 2.2 Target Users

- Healthcare professionals (validation, reference lookup).
- Patients (general information, image upload for triage-style feedback).
- Learners (multi-agent RAG, LangGraph, medical AI patterns).

---

## 3. Architecture & Design

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI (app.py)                                 │
│  /chat | /upload | /validate | /transcribe | /generate-speech | /health      │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Agent Decision (agent_decision.py)                        │
│  LangGraph StateGraph: analyze_input → route_to_agent → [agents] →          │
│  check_validation → human_validation (optional) → apply_guardrails → END      │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Conversation │    │   RAG Agent  │    │ Web Search   │    │ Image Agents │
│    Agent     │    │ (MedicalRAG) │    │  Processor   │    │ Chest/Skin/   │
│              │    │              │    │   (Tavily)   │    │ Brain (TBD)   │
└──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                           │
                    ┌──────┴──────┐
                    │ Low conf /  │
                    │ insufficient│
                    │    info?    │
                    └──────┬──────┘
                           ▼
                    Web Search Processor
```

### 3.2 Entry Point & Request Flow

1. **User input** (text and/or image) → `app.py` → `process_query(query)` in `agent_decision.py`.
2. **State init:** `AgentState` with `messages`, `current_input`, `has_image`, `image_type`, etc.
3. **analyze_input:**  
   - If text: run **input guardrails**; if blocked → return guardrail message and bypass routing.  
   - If image: **ImageClassifier** (GPT-4o Vision) classifies as BRAIN MRI / CHEST X-RAY / SKIN LESION / OTHER / NON-MEDICAL.
4. **route_to_agent:** LLM (decision prompt) chooses agent from: CONVERSATION_AGENT, RAG_AGENT, WEB_SEARCH_PROCESSOR_AGENT, BRAIN_TUMOR_AGENT, CHEST_XRAY_AGENT, SKIN_LESION_AGENT. Low confidence → `needs_validation` (currently routed to RAG).
5. **Agent execution:**  
   - **Conversation:** Full history + user query → conversation LLM.  
   - **RAG:** Query expansion → hybrid retrieval (Qdrant) → rerank → response generation with sources; confidence and “insufficient information” drive handoff.  
   - **Web Search:** Query refinement from history → Tavily search → LLM summarization.  
   - **Chest X-ray:** DenseNet121 classifier → covid19 / normal.  
   - **Skin Lesion:** U-Net segmentation → mask overlay image saved.  
   - **Brain Tumor:** Placeholder (returns fixed message).
6. **check_validation:** If `needs_human_validation` (imaging agents) → **human_validation** node (append “Human Validation Required” to output).
7. **apply_guardrails:** Output guardrails (LLM-based sanitization); handle validation Yes/No from user.
8. **END:** Response returned to `app.py` and then to client.

### 3.3 State & Memory

- **AgentState** (LangGraph `MessagesState` extension): `messages`, `agent_name`, `current_input`, `has_image`, `image_type`, `output`, `needs_human_validation`, `retrieval_confidence`, `bypass_routing`, `insufficient_info`.
- **Memory:** `MemorySaver()` checkpointer with fixed `thread_id: "1"` — conversation history is persisted in state; truncated to `config.max_conversation_history` (20 messages) after each run.

---

## 4. Technology Stack

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI 0.115+, Uvicorn |
| **Orchestration** | LangGraph 0.3+, LangChain 0.3+ |
| **LLM / Embeddings** | Azure OpenAI (gpt-4o, text-embedding-ada-002) — configurable |
| **Document parsing** | Docling 2.x (PDF: text, tables, images; OCR, table structure) |
| **Vector DB** | Qdrant (local path `./data/qdrant_db` or server) |
| **RAG retrieval** | Dense (Azure embeddings) + Sparse (FastEmbed BM25) — hybrid |
| **Reranker** | sentence-transformers CrossEncoder (ms-marco-TinyBERT-L-6) |
| **Medical imaging** | PyTorch 2.7; DenseNet121 (chest X-ray), U-Net (skin lesion); Brain tumor TBD |
| **Image classification (type)** | GPT-4o Vision (ImageClassifier) |
| **Web search** | Tavily API (PubMed code present but commented) |
| **Speech** | ElevenLabs (transcribe + TTS) |
| **Guardrails** | LangChain prompts + same Azure LLM |
| **Frontend** | Single-page HTML/CSS/JS (Bootstrap, Font Awesome) |
| **Deployment** | Docker (Python 3.11-slim), GitHub Actions (build on main/PR) |

---

## 5. Component Analysis

### 5.1 Application Layer (`app.py`)

- **Endpoints:**  
  - `GET /` — serve `index.html`.  
  - `GET /health` — Docker health check.  
  - `POST /chat` — text query → `process_query(request.query)` → JSON `{ status, response, agent [, result_image ] }`.  
  - `POST /upload` — image + optional text → save to `uploads/backend`, `process_query({ "text", "image" })`, delete temp file, return same shape; skin lesion can add `result_image`.  
  - `POST /validate` — validation result + comments → re-run `process_query` with validation message.  
  - `POST /transcribe` — audio file → convert to MP3 (pydub) → ElevenLabs Scribe → `{ transcript }`.  
  - `POST /generate-speech` — text + voice_id → ElevenLabs TTS → MP3 file response.
- **Config:** `Config()` from `config.py`; max upload size, speech API key, etc.
- **Background:** Thread cleans `uploads/speech/*.mp3` every 5 minutes.
- **Static:** `/data`, `/uploads` mounted for frontend assets and generated images.

### 5.2 Agent Decision System (`agents/agent_decision.py`)

- **Graph:** `StateGraph(AgentState)` with nodes: analyze_input, route_to_agent, CONVERSATION_AGENT, RAG_AGENT, WEB_SEARCH_PROCESSOR_AGENT, BRAIN_TUMOR_AGENT, CHEST_XRAY_AGENT, SKIN_LESION_AGENT, check_validation, human_validation, apply_guardrails.
- **Decision model:** Single LLM call with structured prompt; output parsed as JSON `{ agent, reasoning, confidence }`. Threshold `CONFIDENCE_THRESHOLD = 0.85` for “needs_validation” branch (currently still maps to RAG).
- **Key logic:**  
  - Input guardrails before routing.  
  - Image type from ImageAnalysisAgent (Vision LLM).  
  - RAG → Web Search handoff when `retrieval_confidence < min_retrieval_confidence` or response contains “insufficient information” / “cannot answer” style phrases.  
  - Human validation only for imaging agents; validation text (Yes/No + comments) processed in apply_output_guardrails.

### 5.3 RAG Agent (`agents/rag_agent/`)

- **MedicalRAG** (`__init__.py`): Coordinates DocParser, ContentProcessor, VectorStore, Reranker, QueryExpander, ResponseGenerator.
- **Ingest pipeline:**  
  1. **MedicalDocParser** (`doc_parser.py`): Docling PDF → markdown + extracted images (saved under `parsed_content_dir`).  
  2. **ContentProcessor** (`content_processor.py`): LLM summarizes each image; document markdown with image placeholders replaced by summaries; LLM-based semantic chunking (respecting structure).  
  3. **VectorStore** (`vectorstore_qdrant.py`): Chunks embedded (dense + sparse); stored in Qdrant collection `medical_assistance_rag`; doc store in `./data/docs_db` (LocalFileStore).  
- **Query pipeline:**  
  1. **QueryExpander** (`query_expander.py`): LLM expands query with medical terms (optional expansion).  
  2. **VectorStore.load_vectorstore()** → hybrid retrieval (top_k=5).  
  3. **Reranker** (`reranker.py`): CrossEncoder rerank → top 3; extracts image paths from chunks for source links.  
  4. **ResponseGenerator** (`response_generator.py`): Builds prompt with context + table instructions + “answer only from context”; computes confidence (e.g. from retrieval scores); appends source/doc links and image refs when `include_sources=True`.
- **Config:** Chunk size/overlap, top_k, reranker model, `min_retrieval_confidence` (0.40), context limits, multiple Azure LLM instances (chunker, summarizer, response generator).

### 5.4 Image Analysis Agent (`agents/image_analysis_agent/`)

- **ImageClassifier** (`image_classifier.py`): Uses Azure Vision LLM to classify upload as BRAIN MRI SCAN / CHEST X-RAY / SKIN LESION / OTHER / NON-MEDICAL (for routing).
- **ChestXRayClassification** (`chest_xray_agent/covid_chest_xray_inference.py`): DenseNet121, 150×150 input, classes `['covid19', 'normal']`; weights from `config.medical_cv.chest_xray_model_path`.
- **SkinLesionSegmentation** (`skin_lesion_agent/skin_lesion_inference.py`): U-Net; loads checkpoint (with optional download); outputs segmentation mask overlay saved to `uploads/skin_lesion_output/segmentation_plot.png`.
- **Brain tumor:** `brain_tumor_agent` present; inference not wired (placeholder in agent_decision).

### 5.5 Web Search Processor Agent (`agents/web_search_processor_agent/`)

- **WebSearchProcessorAgent** → **WebSearchProcessor** → **WebSearchAgent** (Tavily).  
- Flow: Build prompt from query + chat history → LLM to get search query → Tavily search → LLM to summarize results into medical response.  
- PubMed integration is commented out.

### 5.6 Guardrails (`agents/guardrails/local_guardrails.py`)

- **Input:** Single LLM prompt; labels SAFE vs “UNSAFE: reason”; blocks PII, harmful content, prompt injection, off-topic, etc.  
- **Output:** LLM revises model response for safety/medical appropriateness; validation Yes/No handled in agent_decision (apply_output_guardrails).  
- Implemented with LangChain chains (prompt | llm | StrOutputParser).

### 5.7 Configuration (`config.py`)

- Central **Config** aggregates: AgentDecision, Conversation, WebSearch, RAG, MedicalCV, Speech, Validation, API, UI.
- **RAG:** Qdrant paths, collection name, chunk size/overlap, embedding dimension, top_k, reranker model, `min_retrieval_confidence`, context limits, multiple Azure LLM temps.  
- **Medical CV:** Paths for brain tumor, chest X-ray, skin lesion models; one shared LLM for medical CV.  
- **Validation:** Per-agent `require_validation` (True for all imaging agents).  
- **API:** Host, port, max image upload size (5 MB).  
- All secrets and endpoints from environment (`.env`).

---

## 6. Data Flow & Key Workflows

### 6.1 Text-Only Chat

User → `/chat` → `process_query(query)` → analyze_input (guardrails) → route_to_agent (LLM) → Conversation / RAG / Web Search → check_validation → apply_guardrails → response.  
RAG branch may hand off to Web Search if confidence low or “insufficient information” detected.

### 6.2 Image Upload

User → `/upload` (image + optional text) → file saved → `process_query({ "text", "image" })` → analyze_input (Vision classifies image type) → route_to_agent → CHEST_XRAY / SKIN_LESION / BRAIN_TUMOR → check_validation → human_validation (append validation UI text) → apply_guardrails → response; skin lesion also returns `result_image` URL.

### 6.3 Human Validation

Frontend shows “Human Validation Required” and Yes/No + comments. User submits → `/validate` → `process_query("Validation result: Yes/No ...")` → same graph; apply_output_guardrails interprets validation and returns confirmation or “further review” message.

### 6.4 RAG Data Ingestion

`ingest_rag_data.py` parses CLI `--file` or `--dir`, builds MedicalRAG(config), and calls `ingest_file` / `ingest_directory`. Each file: Docling parse → image summaries → formatted doc → semantic chunks → vector store + doc store. Raw PDFs live in `data/raw`; parsed images in `data/parsed_docs`; Qdrant in `data/qdrant_db`; doc store in `data/docs_db`.

---

## 7. File Structure Summary

```
multi_agent_medical_assistant/
├── app.py                    # FastAPI app, /chat, /upload, /validate, /transcribe, /generate-speech
├── config.py                 # Central config (Azure, RAG, CV, speech, validation, API)
├── ingest_rag_data.py        # CLI ingestion into RAG (--file / --dir)
├── requirements.txt          # Python deps (FastAPI, LangChain, Docling, PyTorch, Qdrant, etc.)
├── Dockerfile                # Python 3.11-slim, ffmpeg, OpenCV deps, HEALTHCHECK
├── .github/workflows/        # Docker image build on main/PR
├── agents/
│   ├── agent_decision.py     # LangGraph orchestration, routing, all agent nodes
│   ├── guardrails/
│   │   └── local_guardrails.py  # Input/output LLM guardrails
│   ├── image_analysis_agent/
│   │   ├── image_classifier.py  # Vision LLM image type classification
│   │   ├── chest_xray_agent/    # DenseNet121 COVID/normal
│   │   ├── skin_lesion_agent/   # U-Net segmentation + model_download
│   │   └── brain_tumor_agent/   # Placeholder
│   ├── rag_agent/
│   │   ├── __init__.py       # MedicalRAG class
│   │   ├── doc_parser.py     # Docling PDF parsing
│   │   ├── content_processor.py # Image summarization, chunking
│   │   ├── vectorstore_qdrant.py # Qdrant hybrid + doc store
│   │   ├── query_expander.py
│   │   ├── reranker.py       # CrossEncoder rerank + image paths
│   │   └── response_generator.py # LLM response + confidence + sources
│   └── web_search_processor_agent/
│       ├── web_search_agent.py   # Tavily (PubMed commented)
│       ├── web_search_processor.py
│       └── tavily_search.py
├── templates/
│   └── index.html            # Single-page UI (chat, upload, voice, validation)
├── data/
│   ├── raw/                  # Ingested PDFs
│   ├── parsed_docs/         # Extracted images
│   ├── qdrant_db/           # Local Qdrant
│   └── docs_db/             # Chunk doc store
├── uploads/                  # Backend/frontend images, skin output, speech
├── sample_images/            # Demo chest X-ray and skin lesion images
└── assets/                   # Flowcharts, logo, demo video
```

---

## 8. API & Environment

### 8.1 Required Environment Variables

- **Azure OpenAI:** `deployment_name`, `model_name`, `azure_endpoint`, `openai_api_key`, `openai_api_version` (and matching for embedding deployment).
- **ElevenLabs:** `ELEVEN_LABS_API_KEY`.
- **Tavily:** `TAVILY_API_KEY`.
- **HuggingFace:** `HUGGINGFACE_TOKEN` (reranker).
- **Qdrant (optional):** `QDRANT_URL`, `QDRANT_API_KEY` when using server instead of local path.

### 8.2 API Endpoints Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | / | Serve chat UI |
| GET | /health | Health check |
| POST | /chat | Text query → agent response |
| POST | /upload | Image (+ text) → analysis + optional result_image |
| POST | /validate | Validation result for human-in-the-loop |
| POST | /transcribe | Audio → transcript (ElevenLabs) |
| POST | /generate-speech | Text → MP3 (ElevenLabs) |

---

## 9. Deployment

- **Docker:** Dockerfile installs ffmpeg, OpenCV/system libs, pip deps; CMD `python app.py`; HEALTHCHECK on `/health`; port 8000.
- **Ingestion in container:** `docker exec ... python ingest_rag_data.py --file ./data/raw/...` or `--dir ./data/raw`.
- **CI:** `.github/workflows/docker-image.yml` builds image on push/PR to `main`.

---

## 10. Strengths

- **Clear separation:** Orchestration (LangGraph), RAG, imaging, web search, guardrails are modular.
- **RAG quality:** Docling + semantic chunking + hybrid retrieval + reranker + source links and image refs.
- **Safety:** Input/output guardrails and human validation for imaging.
- **Confidence handoff:** RAG → Web Search on low confidence or “insufficient information” reduces hallucination risk.
- **Single codebase:** Backend, agents, and config in one repo with documented setup (README, agents/README).

---

## 11. Recommendations & Notes

1. **Brain tumor agent:** Implement real inference and wire in `agent_decision.py`; currently placeholder.
2. **Conversation history:** Thread ID is fixed (`"1"`); consider per-user/session thread_id for multi-user.
3. **Guardrails:** Input guardrails include many “ask for X” rules (sources, DOI, etc.) that might block legitimate citation requests; consider narrowing to clearly unsafe categories.
4. **PubMed:** Uncomment and configure if PubMed is desired alongside Tavily.
5. **Testing:** Add unit tests for agent routing, RAG retrieval, and guardrails.
6. **Config typo:** `AgentDecisoinConfig` in config.py could be renamed to `AgentDecisionConfig`.

---

## 12. References

- **Project README:** Installation, features, tech stack, usage.  
- **agents/README.md:** Human-in-the-loop flow, RAG citations (papers and documents).  
- **Flowcharts:** `assets/final_medical_assistant_flowchart_light_rounded.png` and related Mermaid/assets.

---

*End of report.*
