# clients/iass_back_emprendemy/services/extensions.py
import logging
from core.utils.supabase_client import supabase

logger = logging.getLogger(__name__)


class InstructionsCache:
    def __init__(self):
        self._cache = {}  # waba_id -> instructions mapping
        self.initialize_cache()

    def initialize_cache(self):
        """Load all WABA instructions when server starts"""
        try:
            response = supabase.table("empre_settings").select("*").execute()
            for record in response.data:
                self._cache[record["waba_id"]] = record["instructions"]
            logger.info(f"Initialized instructions cache for {len(self._cache)} WABAs")
        except Exception as e:
            logger.error(f"Error initializing instructions cache: {e}")

    def get_instructions(self, waba_id: str) -> str:
        """Get cached instructions for a WABA"""
        return self._cache.get(waba_id, "")

    async def update_instructions(self, waba_id: str, instructions: str):
        """Update cache when instructions are updated in DB"""
        self._cache[waba_id] = instructions
        logger.info(f"Updated cache for WABA {waba_id}")


class CoursesCache:
    def __init__(self):
        self._cache = {}  # waba_id -> {course_id -> content} mapping
        self.initialize_cache()

    def initialize_cache(self):
        """Load all courses grouped by waba_id"""
        try:
            response = supabase.table("empre_courses").select("*").execute()
            for record in response.data:
                waba_id = record["waba_id"]
                course_id = record["course_id"]

                # Initialize waba_id dict if not exists
                if waba_id not in self._cache:
                    self._cache[waba_id] = {}

                self._cache[waba_id][course_id] = {
                    "id": course_id,
                    "title": record["title"],
                    "brief": record["brief"],
                    "preview": record["preview"],
                    "duration": record["duration"],
                    "instructor": record["instructor"],
                    "instructor_bio": record["instructor_bio"],
                    "description": record["description"],
                    "requirements": record["requirements"],
                    "learning_objectives": record["learning_objectives"],
                    "reviews": record["reviews"],
                    "units": record["units"],
                    "selling_description": record[
                        "selling_description"
                    ],  # Agregar este campo
                }
            logger.info(f"Initialized courses cache for {len(self._cache)} WABAs")
        except Exception as e:
            logger.error(f"Error initializing courses cache: {e}")

    def refresh_cache(self):
        """Reload all cache data from DB"""
        self._cache = {}
        self.initialize_cache()

    def get_courses(self, waba_id: str, force_refresh: bool = False) -> dict:
        """Get all cached courses for a WABA"""
        if force_refresh:
            self.refresh_cache()
        return self._cache.get(waba_id, {})

    def get_course(
        self, waba_id: str, course_id: str, force_refresh: bool = False
    ) -> dict:
        """Get specific course from cache"""
        if force_refresh:
            self.refresh_cache()
        return self._cache.get(waba_id, {}).get(course_id, {})

    def update_course(self, waba_id: str, course_id: str, content: dict):
        """Update cache when course is updated"""
        if waba_id not in self._cache:
            self._cache[waba_id] = {}
        self._cache[waba_id][course_id] = content
        logger.info(f"Updated cache for course {course_id} in WABA {waba_id}")

    def delete_course(self, waba_id: str, course_id: str):
        """Remove course from cache"""
        if waba_id in self._cache and course_id in self._cache[waba_id]:
            del self._cache[waba_id][course_id]
            logger.info(f"Deleted course {course_id} from WABA {waba_id} cache")
