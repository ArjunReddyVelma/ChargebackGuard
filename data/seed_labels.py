import os
import csv
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models import TestLabel

LABELS_CSV = os.path.join(os.path.dirname(__file__), "synthetic_labels.csv")

def seed_test_labels():
    Base.metadata.create_all(bind=engine)
    if not os.path.exists(LABELS_CSV):
        print(f"Labels file {LABELS_CSV} does not exist yet.")
        return

    db: Session = SessionLocal()
    try:
        with open(LABELS_CSV, "r") as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                tx_id = row["transaction_id"]
                is_fraud = (row["is_fraud"].lower() == "true")
                
                existing = db.query(TestLabel).filter(TestLabel.transaction_id == tx_id).first()
                if not existing:
                    db.add(TestLabel(transaction_id=tx_id, is_fraud=is_fraud))
                    count += 1
            db.commit()
            print(f"Seeded {count} test ground truth labels into database.")
    finally:
        db.close()

if __name__ == "__main__":
    seed_test_labels()
