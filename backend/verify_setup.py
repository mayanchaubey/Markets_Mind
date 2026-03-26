"""
MarketMind AI — Setup Verification Script
Run this first to verify all dependencies and download BGE model.
"""
import sys
import os

print("="*60)
print("MarketMind AI — Setup Verification")
print("="*60)

# Step 1 — Check Python version
print(f"\n[1] Python version: {sys.version}")
if sys.version_info < (3, 10):
    print("❌ Python 3.10+ required")
    sys.exit(1)
else:
    print("✅ Python version OK")

# Step 2 — Check all imports
print("\n[2] Checking dependencies...")
deps = [
    ("langchain", "langchain"),
    ("langchain_core", "langchain-core"),
    ("langchain_community", "langchain-community"),
    ("langchain_huggingface", "langchain-huggingface"),
    ("langchain_chroma", "langchain-chroma"),
    ("langchain_pinecone", "langchain-pinecone"),
    ("sentence_transformers", "sentence-transformers"),
    ("torch", "torch"),
    ("transformers", "transformers"),
    ("chromadb", "chromadb"),
    ("pinecone", "pinecone-client"),
    ("groq", "groq"),
    ("fastapi", "fastapi"),
    ("uvicorn", "uvicorn"),
    ("dotenv", "python-dotenv"),
    ("feedparser", "feedparser"),
    ("pandas", "pandas"),
    ("yfinance", "yfinance"),
    ("bs4", "beautifulsoup4"),
    ("youtube_transcript_api", "youtube-transcript-api"),
    ("schedule", "schedule"),
    ("numpy", "numpy"),
    ("tqdm", "tqdm"),
    ("lxml", "lxml"),
    ("html5lib", "html5lib"),
]

missing = []
for module, package in deps:
    try:
        __import__(module)
        print(f"  ✅ {package}")
    except ImportError:
        print(f"  ❌ {package} — MISSING")
        missing.append(package)

if missing:
    print(f"\n❌ Missing packages: {', '.join(missing)}")
    print("Run: pip install " + " ".join(missing))
    sys.exit(1)
else:
    print("\n✅ All dependencies installed")

# Step 3 — Check .env file
print("\n[3] Checking .env file...")
from dotenv import load_dotenv
load_dotenv()

required_keys = [
    "PINECONE_API_KEY",
    "PINECONE_INDEX",
    "GROQ_API_KEY",
    "GROQ_MODEL",
    "VECTOR_STORE",
    "EMBEDDING_MODEL",
    "HF_HOME",
]

missing_keys = []
for key in required_keys:
    val = os.getenv(key)
    if not val:
        print(f"  ❌ {key} — NOT SET")
        missing_keys.append(key)
    else:
        masked = val[:6] + "..." if len(val) > 6 else "***"
        print(f"  ✅ {key} = {masked}")

if missing_keys:
    print(f"\n❌ Missing .env keys. Copy .env.template to .env and fill them in.")
    sys.exit(1)
else:
    print("\n✅ All .env keys present")

# Step 4 — Check HF_HOME has space and download BGE model
print("\n[4] Checking BGE model...")
hf_home = os.getenv("HF_HOME", "")
if hf_home:
    os.makedirs(hf_home, exist_ok=True)
    import shutil
    free_gb = shutil.disk_usage(hf_home).free / (1024**3)
    print(f"  HF_HOME: {hf_home}")
    print(f"  Free space: {free_gb:.1f} GB")
    if free_gb < 0.5:
        print("  ❌ Less than 500MB free — BGE model needs ~438MB")
        sys.exit(1)

print("  Downloading/verifying BGE model (first time takes ~5 min)...")
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    model = HuggingFaceEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    # Quick test embed
    test = model.embed_query("test")
    assert len(test) == 768, f"Expected 768 dims, got {len(test)}"
    print("  ✅ BGE model loaded and working (768 dims)")
except Exception as e:
    print(f"  ❌ BGE model failed: {e}")
    sys.exit(1)

# Step 5 — Check Pinecone connection
print("\n[5] Checking Pinecone connection...")
try:
    from pinecone import Pinecone
    pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
    index_name = os.getenv("PINECONE_INDEX", "marketmind")
    index = pc.Index(index_name)
    stats = index.describe_index_stats()
    vector_count = stats.get("total_vector_count", 0)
    print(f"  ✅ Pinecone connected — index '{index_name}' has {vector_count} vectors")
    if vector_count == 0:
        print("  ⚠️  Index is empty — get the API keys from your teammate who ran the pipeline")
except Exception as e:
    print(f"  ❌ Pinecone connection failed: {e}")
    sys.exit(1)

# Step 6 — Check Groq connection
print("\n[6] Checking Groq connection...")
try:
    from groq import Groq
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile"),
        messages=[{"role": "user", "content": "Say OK"}],
        max_tokens=5,
    )
    print(f"  ✅ Groq connected — model responding")
except Exception as e:
    print(f"  ❌ Groq connection failed: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("✅ ALL CHECKS PASSED — Ready to build Stage 3")
print("="*60)