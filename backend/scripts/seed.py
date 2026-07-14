"""Create tables and seed reference data (HCPs + materials).

Run:  python -m scripts.seed      (from the backend/ directory)
Safe to re-run: it clears and re-seeds the reference tables.
"""
import sys
import os

# allow "python -m scripts.seed" and "python scripts/seed.py"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import Base, engine, SessionLocal
from app import models  # noqa: F401  (registers models on Base)


HCPS = [
    {"name": "Dr. Smith", "specialty": "Oncology", "institution": "City Hospital"},
    {"name": "Dr. John", "specialty": "Cardiology", "institution": "Central Clinic"},
    {"name": "Dr. Lee", "specialty": "Neurology", "institution": "Metro Medical Center"},
    {"name": "Dr. Sharma", "specialty": "Endocrinology", "institution": "Sunrise Hospital"},
    {"name": "Dr. Patel", "specialty": "Immunology", "institution": "Riverside Health"},
]

MATERIALS = [
    {"name": "Product X Brochure", "type": "brochure", "product": "Product X"},
    {"name": "OncoBoost Phase III PDF", "type": "pdf", "product": "OncoBoost"},
    {"name": "Product X Sample Pack", "type": "sample", "product": "Product X"},
    {"name": "CardioSafe Brochure", "type": "brochure", "product": "CardioSafe"},
    {"name": "NeuroCalm Sample", "type": "sample", "product": "NeuroCalm"},
]


def main():
    print("Creating tables (if not present)...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Clearing existing reference data...")
        # order matters due to FKs
        db.query(models.InteractionMaterial).delete()
        db.query(models.Interaction).delete()
        db.query(models.Material).delete()
        db.query(models.HCP).delete()
        db.commit()

        print("Seeding HCPs...")
        for h in HCPS:
            db.add(models.HCP(**h))

        print("Seeding materials...")
        for m in MATERIALS:
            db.add(models.Material(**m))

        db.commit()

        n_hcp = db.query(models.HCP).count()
        n_mat = db.query(models.Material).count()
        print(f"Done. Seeded {n_hcp} HCPs and {n_mat} materials.")
    finally:
        db.close()


if __name__ == "__main__":
    main()