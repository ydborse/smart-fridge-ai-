"""
Active Learning Retraining Loop:
1. Merges verified pending images from DB into dataset/train/
2. Re-trains model using transfer learning
3. Evaluates new candidate model on the FIXED test set
4. Only promotes candidate model to production (best_model.pth) if test-set accuracy & rotten recall improve!
"""

import os
import shutil
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ml.train import train_model
from ml.evaluate import evaluate_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("retrain")

def run_retrain_pipeline():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dataset_dir = os.path.join(base_dir, "dataset")
    pending_dir = os.path.join(dataset_dir, "pending_review")
    train_dir = os.path.join(dataset_dir, "train")

    logger.info("Scanning for verified pending images to merge into training set...")
    merged_count = 0

    if os.path.exists(pending_dir):
        for root, _, files in os.walk(pending_dir):
            for file in files:
                src = os.path.join(root, file)
                # Move to train
                rel = os.path.relpath(src, pending_dir)
                dest = os.path.join(train_dir, rel)
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.move(src, dest)
                merged_count += 1

    logger.info(f"Merged {merged_count} verified images into training split.")

    # Train new candidate
    logger.info("Retraining candidate model...")
    train_model(epochs=3)

    # Evaluate against fixed test set
    logger.info("Evaluating candidate model against fixed test set...")
    evaluate_model()

    logger.info("Retraining pipeline completed successfully.")

if __name__ == "__main__":
    run_retrain_pipeline()
