import httpx
import html
import asyncio
from dataclasses import dataclass, field
import logging
import json
import smtplib
from typing import Dict, Any, List, Optional, Literal, Union, Tuple, Set
from string import Template

import uuid
from fastapi import APIRouter, Request, BackgroundTasks, Response, HTTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from enum import Enum
from cachetools import TTLCache
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel
import os
import traceback


from app.services.whatsapp import (
    get_media_whatsapp_url,
    send_contact_message_to_wa,
    send_text_response_to_wa,
)
from app.services.openai import convert_audio_to_text
from app.services.supabase import upload_to_supabase_audio_bucket
from app.utils.blocked_numbers import is_number_blocked
from app.utils.helpers import WABAConfig, get_waba_config, InstructionsStrategy
from app.core.config import Settings, settings
from app.utils.supabase_client import supabase

# from loguru import logger
from dateutil.relativedelta import relativedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

SMTP_PORT = 465  # Explicitly set port for SSL

db = None
message_buffer_manager = None
context = None
courses_cache = None
instructions_cache = None
