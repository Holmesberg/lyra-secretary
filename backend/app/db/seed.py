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
        # fitness
        {"keyword": "gym", "category": "fitness"},
        {"keyword": "workout", "category": "fitness"},
        {"keyword": "run", "category": "fitness"},
        {"keyword": "walk", "category": "fitness"},
        {"keyword": "sport", "category": "fitness"},
        # academic
        {"keyword": "lecture", "category": "academic"},
        {"keyword": "class", "category": "academic"},
        {"keyword": "course", "category": "academic"},
        {"keyword": "CSE", "category": "academic"},
        {"keyword": "PHM", "category": "academic"},
        # study
        {"keyword": "study", "category": "study"},
        {"keyword": "review", "category": "study"},
        {"keyword": "read", "category": "study"},
        {"keyword": "homework", "category": "study"},
        {"keyword": "assignment", "category": "study"},
        {"keyword": "problem set", "category": "study"},
        # development
        {"keyword": "code", "category": "development"},
        {"keyword": "debug", "category": "development"},
        {"keyword": "build", "category": "development"},
        {"keyword": "implement", "category": "development"},
        {"keyword": "fix", "category": "development"},
        {"keyword": "feature", "category": "development"},
        {"keyword": "Lyra", "category": "development"},
        # meeting
        {"keyword": "meeting", "category": "meeting"},
        {"keyword": "call", "category": "meeting"},
        {"keyword": "sync", "category": "meeting"},
        {"keyword": "standup", "category": "meeting"},
        # prayer
        {"keyword": "prayer", "category": "prayer"},
        {"keyword": "Fajr", "category": "prayer"},
        {"keyword": "Dhuhr", "category": "prayer"},
        {"keyword": "Asr", "category": "prayer"},
        {"keyword": "Maghrib", "category": "prayer"},
        {"keyword": "Isha", "category": "prayer"},
        {"keyword": "Taraweeh", "category": "prayer"},
        # self_reflection
        {"keyword": "planning", "category": "self_reflection"},
        {"keyword": "reflection", "category": "self_reflection"},
        {"keyword": "journal", "category": "self_reflection"},
        # network
        {"keyword": "interview", "category": "network"},
        {"keyword": "LinkedIn", "category": "network"},
        {"keyword": "network", "category": "network"},
        # other
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
