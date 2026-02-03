# Study Folder — Multi-Agent Medical Assistant

This folder contains analysis and documentation produced from a detailed review of the **Multi-Agent Medical Assistant** project.

## Contents

| File | Description |
|------|-------------|
| **PROJECT_ANALYSIS_REPORT.md** | Full project analysis: architecture, components, data flow, tech stack, file structure, API, deployment, strengths, and recommendations. |

## Quick Summary

- **Purpose:** AI-powered medical chatbot with multi-agent orchestration, RAG, medical imaging (chest X-ray, skin lesion), web search, and human-in-the-loop validation.
- **Stack:** FastAPI, LangGraph, LangChain, Qdrant, Docling, PyTorch (DenseNet121, U-Net), Azure OpenAI, ElevenLabs, Tavily.
- **Entry:** `app.py` → `agent_decision.process_query()` → LangGraph workflow → specialized agents.
- **Report:** See `PROJECT_ANALYSIS_REPORT.md` for the complete study.
