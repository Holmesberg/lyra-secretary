"""Database seeder for initial data."""
import logging
from datetime import datetime
from app.db.session import SessionLocal
from app.db.models import CategoryMapping

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed():
    """Seed initial database static records."""
    db = SessionLocal()
    
    seeds = [
        {"keyword": "gym", "category": "health"},
        {"keyword": "workout", "category": "health"},
        {"keyword": "study", "category": "deep_work"},
        {"keyword": "learning", "category": "deep_work"},
        {"keyword": "code", "category": "deep_work"},
        {"keyword": "meeting", "category": "meetings"},
        {"keyword": "call", "category": "meetings"},
        {"keyword": "lunch", "category": "personal"},
        {"keyword": "dinner", "category": "personal"},
    ]
    
    try:
        added = 0
        for item in seeds:
            exists = db.query(CategoryMapping).filter_by(keyword=item["keyword"]).first()
            if not exists:
                mapping = CategoryMapping(
                    keyword=item["keyword"],
                    category=item["category"],
                    confidence=0.9,
                    last_used=datetime.utcnow()
                )
                db.add(mapping)
                added += 1
                
        if added > 0:
            db.commit()
            logger.info(f"Successfully seeded {added} CategoryMappings.")
        else:
            logger.info("CategoryMappings already seeded, no action taken.")
            
    except Exception as e:
        logger.error(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
