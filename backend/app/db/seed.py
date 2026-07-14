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
        {"keyword": "lectures", "category": "academic"},
        {"keyword": "lec", "category": "academic"},
        {"keyword": "class", "category": "academic"},
        {"keyword": "course", "category": "academic"},
        {"keyword": "lab", "category": "academic"},
        {"keyword": "labs", "category": "academic"},
        {"keyword": "tutorial", "category": "academic"},
        {"keyword": "tutorials", "category": "academic"},
        {"keyword": "tut", "category": "academic"},
        {"keyword": "section", "category": "academic"},
        {"keyword": "practical", "category": "academic"},
        {"keyword": "CSE", "category": "academic"},
        {"keyword": "PHM", "category": "academic"},
        # study
        {"keyword": "study", "category": "study"},
        {"keyword": "review", "category": "study"},
        {"keyword": "revision", "category": "study"},
        {"keyword": "revise", "category": "study"},
        {"keyword": "rev", "category": "study"},
        {"keyword": "read", "category": "study"},
        {"keyword": "reading", "category": "study"},
        {"keyword": "slides", "category": "study"},
        {"keyword": "practice", "category": "study"},
        {"keyword": "solve", "category": "study"},
        {"keyword": "homework", "category": "study"},
        {"keyword": "assignment", "category": "study"},
        {"keyword": "sheet", "category": "study"},
        {"keyword": "problem set", "category": "study"},
        # development
        {"keyword": "code", "category": "development"},
        {"keyword": "debug", "category": "development"},
        {"keyword": "build", "category": "development"},
        {"keyword": "implement", "category": "development"},
        {"keyword": "fix", "category": "development"},
        {"keyword": "feature", "category": "development"},
        {"keyword": "LyraOS", "category": "development"},
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
        # planning (Apr 21: un-merged from self_reflection — Path B commits
        # to engineering planning as a habit; reflection/journal keywords
        # stay pointing here since "thinking about next steps" is the
        # dominant behavior the category now anchors. Dedicated
        # journaling/self_reflection will be a separate category when
        # n=50 data shows it's a real sub-behavior, not before.)
        {"keyword": "plan", "category": "planning"},
        {"keyword": "planning", "category": "planning"},
        {"keyword": "brain dump", "category": "planning"},
        {"keyword": "brainstorm", "category": "planning"},
        {"keyword": "schedule", "category": "planning"},
        {"keyword": "outline", "category": "planning"},
        {"keyword": "agenda", "category": "planning"},
        {"keyword": "roadmap", "category": "planning"},
        {"keyword": "priorities", "category": "planning"},
        {"keyword": "weekly review", "category": "planning"},
        {"keyword": "reflection", "category": "planning"},
        {"keyword": "journal", "category": "planning"},
        {"keyword": "calibration", "category": "planning"},
        {"keyword": "friction", "category": "planning"},
        {"keyword": "idea", "category": "planning"},
        {"keyword": "refinement", "category": "planning"},
        # network
        {"keyword": "interview", "category": "network"},
        {"keyword": "LinkedIn", "category": "network"},
        {"keyword": "network", "category": "network"},
        # other
        {"keyword": "lunch", "category": "personal"},
        {"keyword": "dinner", "category": "personal"},
        # health (operator vocabulary additions, Apr 8)
        {"keyword": "sleep", "category": "health"},
        # development extensions (Apr 8)
        {"keyword": "swe", "category": "development"},
        {"keyword": "debugging", "category": "development"},
        # work fallback (Apr 8)
        {"keyword": "quick", "category": "work"},
        {"keyword": "unplanned", "category": "work"},
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
