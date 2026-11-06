"""
main.py - FastAPI dengan UnB + OULAD data source
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone

from config import APP_NAME, APP_VERSION, CORS_ORIGINS
from database import engine, get_db, Base
from models import (
    Event, Forum, Quiz, Note, User,
    OuladVle, OuladAssessment, OuladStudent, OuladCourse, OuladRegistration,
)
from schemas import (
    EventBatch, ForumBatch, QuizBatch, NoteBatch, UserBatch,
    OuladVleBatch, OuladAssessmentBatch, OuladStudentBatch,
    OuladCourseBatch, OuladRegistrationBatch,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="API gateway untuk UnB + OULAD data",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================
@app.get("/")
def root():
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "datasets": {
            "UnB": ["events", "forum", "quiz", "notes", "users"],
            "OULAD": ["oulad_vle", "oulad_assessment", "oulad_students",
                      "oulad_courses", "oulad_registration"],
        },
        "endpoints_unb": [
            "POST /api/activities/batch",
            "POST /api/forum/batch",
            "POST /api/quiz/batch",
            "POST /api/notes/batch",
            "POST /api/users/batch",
        ],
        "endpoints_oulad": [
            "POST /api/oulad/vle/batch",
            "POST /api/oulad/assessment/batch",
            "POST /api/oulad/students/batch",
            "POST /api/oulad/courses/batch",
            "POST /api/oulad/registration/batch",
        ],
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        tables = {
            "events": db.query(func.count(Event.id)).scalar(),
            "forum": db.query(func.count(Forum.id)).scalar(),
            "quiz": db.query(func.count(Quiz.id)).scalar(),
            "notes": db.query(func.count(Note.id)).scalar(),
            "users": db.query(func.count(User.id)).scalar(),
            "oulad_vle": db.query(func.count(OuladVle.id)).scalar(),
            "oulad_assessment": db.query(func.count(OuladAssessment.id)).scalar(),
            "oulad_students": db.query(func.count(OuladStudent.id)).scalar(),
            "oulad_courses": db.query(func.count(OuladCourse.id)).scalar(),
            "oulad_registration": db.query(func.count(OuladRegistration.id)).scalar(),
        }
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "tables": tables,
            "total": sum(tables.values()),
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


# ============================================================
# UNB ENDPOINTS
# ============================================================
@app.post("/api/activities/batch", status_code=201)
def post_events(batch: EventBatch, db: Session = Depends(get_db)):
    try:
        items = [Event(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "inserted": len(items),
                "total": db.query(func.count(Event.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/forum/batch", status_code=201)
def post_forum(batch: ForumBatch, db: Session = Depends(get_db)):
    try:
        items = [Forum(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "inserted": len(items),
                "total": db.query(func.count(Forum.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/quiz/batch", status_code=201)
def post_quiz(batch: QuizBatch, db: Session = Depends(get_db)):
    try:
        items = [Quiz(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "inserted": len(items),
                "total": db.query(func.count(Quiz.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notes/batch", status_code=201)
def post_notes(batch: NoteBatch, db: Session = Depends(get_db)):
    try:
        items = [Note(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "inserted": len(items),
                "total": db.query(func.count(Note.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/users/batch", status_code=201)
def post_users(batch: UserBatch, db: Session = Depends(get_db)):
    try:
        items = [User(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "inserted": len(items),
                "total": db.query(func.count(User.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# OULAD ENDPOINTS
# ============================================================
@app.post("/api/oulad/vle/batch", status_code=201)
def post_oulad_vle(batch: OuladVleBatch, db: Session = Depends(get_db)):
    try:
        items = [OuladVle(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "source": "studentVle.csv",
                "inserted": len(items),
                "total": db.query(func.count(OuladVle.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oulad/assessment/batch", status_code=201)
def post_oulad_assessment(batch: OuladAssessmentBatch, db: Session = Depends(get_db)):
    try:
        items = [OuladAssessment(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "source": "studentAssessment.csv",
                "inserted": len(items),
                "total": db.query(func.count(OuladAssessment.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oulad/students/batch", status_code=201)
def post_oulad_students(batch: OuladStudentBatch, db: Session = Depends(get_db)):
    try:
        items = [OuladStudent(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "source": "studentInfo.csv",
                "inserted": len(items),
                "total": db.query(func.count(OuladStudent.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oulad/courses/batch", status_code=201)
def post_oulad_courses(batch: OuladCourseBatch, db: Session = Depends(get_db)):
    try:
        items = [OuladCourse(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "source": "courses.csv",
                "inserted": len(items),
                "total": db.query(func.count(OuladCourse.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oulad/registration/batch", status_code=201)
def post_oulad_registration(batch: OuladRegistrationBatch, db: Session = Depends(get_db)):
    try:
        items = [OuladRegistration(**e.dict()) for e in batch.events]
        db.add_all(items)
        db.commit()
        return {"status": "ok", "source": "studentRegistration.csv",
                "inserted": len(items),
                "total": db.query(func.count(OuladRegistration.id)).scalar()}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# STATS
# ============================================================
@app.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "unb": {
            "events": db.query(func.count(Event.id)).scalar(),
            "forum": db.query(func.count(Forum.id)).scalar(),
            "quiz": db.query(func.count(Quiz.id)).scalar(),
            "notes": db.query(func.count(Note.id)).scalar(),
            "users": db.query(func.count(User.id)).scalar(),
        },
        "oulad": {
            "vle": db.query(func.count(OuladVle.id)).scalar(),
            "assessment": db.query(func.count(OuladAssessment.id)).scalar(),
            "students": db.query(func.count(OuladStudent.id)).scalar(),
            "courses": db.query(func.count(OuladCourse.id)).scalar(),
            "registration": db.query(func.count(OuladRegistration.id)).scalar(),
        },
    }


# ============================================================
# KAFKA POLLING ENDPOINTS (UnB + OULAD)
# ============================================================
@app.get("/api/activities/kafka-format/since/{last_id}")
def get_events_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                     db: Session = Depends(get_db)):
    events = (db.query(Event)
              .filter(Event.id > last_id)
              .order_by(Event.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "events",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/oulad/vle/kafka-format/since/{last_id}")
def get_oulad_vle_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                        db: Session = Depends(get_db)):
    events = (db.query(OuladVle)
              .filter(OuladVle.id > last_id)
              .order_by(OuladVle.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_vle",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/oulad/assessment/kafka-format/since/{last_id}")
def get_oulad_assessment_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                               db: Session = Depends(get_db)):
    events = (db.query(OuladAssessment)
              .filter(OuladAssessment.id > last_id)
              .order_by(OuladAssessment.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_assessment",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/oulad/students/kafka-format/since/{last_id}")
def get_oulad_students_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                              db: Session = Depends(get_db)):
    events = (db.query(OuladStudent)
              .filter(OuladStudent.id > last_id)
              .order_by(OuladStudent.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_students",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/oulad/courses/kafka-format/since/{last_id}")
def get_oulad_courses_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                             db: Session = Depends(get_db)):
    events = (db.query(OuladCourse)
              .filter(OuladCourse.id > last_id)
              .order_by(OuladCourse.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_courses",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


@app.get("/api/oulad/registration/kafka-format/since/{last_id}")
def get_oulad_registration_kafka(last_id: int, limit: int = Query(100, ge=1, le=1000),
                                  db: Session = Depends(get_db)):
    events = (db.query(OuladRegistration)
              .filter(OuladRegistration.id > last_id)
              .order_by(OuladRegistration.id.asc())
              .limit(limit).all())
    next_last_id = events[-1].id if events else last_id
    return {
        "source": "oulad_registration",
        "last_id": last_id,
        "count": len(events),
        "next_last_id": next_last_id,
        "events": [e.to_dict() for e in events],
    }


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)