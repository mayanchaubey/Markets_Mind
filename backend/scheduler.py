import schedule
import time
from rag_pipeline.pipeline_runner import run_full_pipeline

def job():
    print("Running daily pipeline...")
    print("Fetching fresh NSE, SEBI, BSE, ET Markets data...")
    run_full_pipeline(use_pinecone=False)  # change to True on demo day
    print("Pipeline complete. Chroma DB updated.")

# Schedule to run every day at 8:00 AM
schedule.every().day.at("08:00").do(job)

print("Scheduler is running. Pipeline will trigger daily at 8 AM.")
print("Keep this terminal open in the background.")
print("Press Ctrl+C to stop.")

while True:
    schedule.run_pending()
    time.sleep(60)  # checks every 60 seconds if it's time to run


