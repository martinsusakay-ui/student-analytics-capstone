"""
schemas.py - Pydantic schemas untuk UnB + OULAD
"""

from pydantic import BaseModel
from typing import List, Optional


# ============================================================
# UNB SCHEMAS
# ============================================================

class EventCreate(BaseModel):
    sequence: int
    user_hash: str
    courseid: int
    component: str
    eventname: str
    action: str
    target: str
    timecreated: int
    event_time: str
    ingested_at: str
    bot_name: str
    source: str


class EventBatch(BaseModel):
    events: List[EventCreate]


class ForumCreate(BaseModel):
    sequence: int
    user_hash: str
    courseid: int
    timecreated: int
    tamanho_mensagem: int
    event_time: str
    ingested_at: str
    bot_name: str
    source: str


class ForumBatch(BaseModel):
    events: List[ForumCreate]


class QuizCreate(BaseModel):
    sequence: int
    user_hash: str
    quiz: int
    attempt: int
    timestart: int
    timefinish: int
    sumgrades: Optional[float] = 0.0
    duration_seconds: int
    ingested_at: str
    bot_name: str
    source: str


class QuizBatch(BaseModel):
    events: List[QuizCreate]


class NoteCreate(BaseModel):
    sequence: int
    user_hash: str
    itemname: str
    finalgrade: Optional[float] = 0.0
    timemodified: float
    ingested_at: str
    bot_name: str
    source: str


class NoteBatch(BaseModel):
    events: List[NoteCreate]


class UserCreate(BaseModel):
    sequence: int
    user_hash: str
    city: Optional[str] = ""
    country: Optional[str] = ""
    lang: Optional[str] = ""
    inscricao_time: int
    roleid: int
    ingested_at: str
    bot_name: str
    source: str


class UserBatch(BaseModel):
    events: List[UserCreate]


# ============================================================
# OULAD SCHEMAS
# ============================================================

class OuladVleCreate(BaseModel):
    sequence: int
    code_module: str
    code_presentation: str
    id_student: int
    id_site: int
    date: int
    sum_click: int
    ingested_at: str
    bot_name: str
    source: str


class OuladVleBatch(BaseModel):
    events: List[OuladVleCreate]


class OuladAssessmentCreate(BaseModel):
    sequence: int
    id_assessment: int
    id_student: int
    date_submitted: int
    is_banked: int
    score: Optional[float] = 0.0
    ingested_at: str
    bot_name: str
    source: str


class OuladAssessmentBatch(BaseModel):
    events: List[OuladAssessmentCreate]


class OuladStudentCreate(BaseModel):
    sequence: int
    code_module: str
    code_presentation: str
    id_student: int
    gender: Optional[str] = ""
    region: Optional[str] = ""
    highest_education: Optional[str] = ""
    imd_band: Optional[str] = ""
    age_band: Optional[str] = ""
    num_of_prev_attempts: int = 0
    studied_credits: int = 0
    disability: Optional[str] = ""
    final_result: Optional[str] = ""
    ingested_at: str
    bot_name: str
    source: str


class OuladStudentBatch(BaseModel):
    events: List[OuladStudentCreate]


class OuladCourseCreate(BaseModel):
    sequence: int
    code_module: str
    code_presentation: str
    module_presentation_length: int
    ingested_at: str
    bot_name: str
    source: str


class OuladCourseBatch(BaseModel):
    events: List[OuladCourseCreate]


class OuladRegistrationCreate(BaseModel):
    sequence: int
    code_module: str
    code_presentation: str
    id_student: int
    date_registration: int
    date_unregistration: Optional[int] = 0
    ingested_at: str
    bot_name: str
    source: str


class OuladRegistrationBatch(BaseModel):
    events: List[OuladRegistrationCreate]