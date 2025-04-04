# clients/iass_back_emprendemy/webhook.py
import logging
import json
import uuid
from fastapi import APIRouter, HTTPException
import traceback
from core.utils.supabase_client import supabase


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

SMTP_PORT = 465  # Explicitly set port for SSL


db = None
message_buffer_manager = None
context = None
courses_cache = None
instructions_cache = None


# ------------------------------------------------------------------------
# MANAGES EMPRENDEMY DATA (esto es para Emprendemy exclusivamente)
# ------------------------------------------------------------------------


@router.get("/wabas/{waba_id}/settings")
async def get_settings(waba_id: str):
    try:
        response = (
            supabase.table("empre_settings")
            .select("*")
            .eq("waba_id", waba_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else {"instructions": ""}
    except Exception as e:
        print(f"Error getting settings: {e}")
        return {"instructions": ""}


@router.post("/wabas/{waba_id}/settings")
async def update_waba_settings(waba_id: str, settings: dict) -> dict:
    try:
        data = {"waba_id": waba_id, "instructions": settings.get("instructions", "")}
        response = supabase.table("empre_settings").insert(data).execute()
        await instructions_cache.update_instructions(
            waba_id, settings.get("instructions", "")
        )
        return {"status": "success", "data": response.data[0]}
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wabas/{waba_id}/courses")
async def get_courses(waba_id: str):
    try:
        cached_courses = courses_cache.get_courses(waba_id)
        if cached_courses:
            # Ensure consistent format when returning from cache
            return [
                {
                    "course_id": cid,
                    "title": data.get("title"),
                    "instructor": data.get("instructor"),
                }
                for cid, data in cached_courses.items()
            ]

        response = (
            supabase.table("empre_courses")
            .select("course_id, title, instructor")
            .eq("waba_id", waba_id)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wabas/{waba_id}/courses")
async def create_course(waba_id: str, course_data: dict):
    try:
        if "course_id" not in course_data:
            course_id = str(uuid.uuid4())[:8]
            course_data["course_id"] = course_id

        course_data["waba_id"] = waba_id

        duration = course_data.get("duration")
        if duration is not None:
            try:
                duration = int(duration)
                if duration > 2147483647:
                    duration = 2147483647
                elif duration < -2147483648:
                    duration = -2147483648
            except (ValueError, TypeError):
                duration = None

        clean_data = {
            "course_id": course_data["course_id"],
            "waba_id": waba_id,
            "title": str(course_data.get("title", "")),
            "brief": str(course_data.get("brief", "")),
            "preview": str(course_data.get("preview", "")),
            "duration": course_data.get("duration"),
            "instructor": str(course_data.get("instructor", "")),
            "instructor_bio": str(course_data.get("instructor_bio", "")),
            "description": str(course_data.get("description", "")),
            "selling_description": str(course_data.get("selling_description", "")),
            "requirements": str(course_data.get("requirements", "")),
            "learning_objectives": json.dumps(
                course_data.get("learning_objectives", [])
            ),
            "reviews": json.dumps(course_data.get("reviews", [])),
            "units": json.dumps(course_data.get("units", [])),
        }

        print("Cleaned data:", clean_data)

        response = supabase.table("empre_courses").insert(clean_data).execute()
        print("Supabase response:", response)

        courses_cache.update_course(waba_id, clean_data["course_id"], clean_data)

        return response.data[0]
    except Exception as e:
        print(f"Error creating course: {str(e)}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to create course: {str(e)}"
        )


@router.get("/wabas/{waba_id}/courses/{course_id}")
async def get_course(waba_id: str, course_id: str):
    try:
        # Validate inputs
        if not waba_id or not course_id or course_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid waba_id or course_id")

        response = (
            supabase.table("empre_courses")
            .select("*")
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Course not found")

        return response.data
    except Exception as e:
        print(f"Error getting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/wabas/{waba_id}/courses/{course_id}")
async def update_course(waba_id: str, course_id: str, course_data: dict):
    try:
        update_data = {
            "title": course_data.get("title"),
            "brief": course_data.get("brief"),
            "preview": course_data.get("preview"),
            "duration": course_data.get("duration"),
            "instructor": course_data.get("instructor"),
            "instructor_bio": course_data.get("instructor_bio"),
            "description": course_data.get("description"),
            "selling_description": course_data.get("selling_description"),
            "requirements": course_data.get("requirements"),
            "learning_objectives": course_data.get("learning_objectives"),
            "reviews": course_data.get("reviews"),
            "units": course_data.get("units"),
            "waba_id": waba_id,
        }

        clean_data = {k: v for k, v in update_data.items() if v is not None}

        response = (
            supabase.table("empre_courses")
            .update(clean_data)
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .execute()
        )

        courses_cache.update_course(waba_id, course_id, clean_data)

        return response.data[0]
    except Exception as e:
        print(f"Error updating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wabas/{waba_id}/courses/{course_id}")
async def delete_course(waba_id: str, course_id: str):
    try:
        print(f"Deleting course {course_id} from WABA {waba_id}")

        response = (
            supabase.table("empre_courses")
            .delete()
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .execute()
        )

        # Also remove from cache
        courses_cache.delete_course(waba_id, course_id)

        return {"status": "success", "message": f"Course {course_id} deleted"}
    except Exception as e:
        print(f"Error deleting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
