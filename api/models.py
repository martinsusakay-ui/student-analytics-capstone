"""
models.py - SQLAlchemy models untuk UnB + OULAD
"""

from sqlalchemy import Column, Integer, BigInteger, String, Float, Index
from database import Base


# ============================================================
# UNB DATASET (5 tabel)
# ============================================================

class Event(Base):
    """Log interaksi UnB."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)
    courseid = Column(Integer, nullable=False, index=True)
    component = Column(String(50))
    eventname = Column(String(255), index=True)
    action = Column(String(50))
    target = Column(String(50))
    timecreated = Column(BigInteger, index=True)
    event_time = Column(String(50))
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Forum(Base):
    """Partisipasi forum UnB."""
    __tablename__ = "forum"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)
    courseid = Column(Integer, nullable=False, index=True)
    timecreated = Column(BigInteger, index=True)
    tamanho_mensagem = Column(Integer)
    event_time = Column(String(50))
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Quiz(Base):
    """Percobaan kuis UnB."""
    __tablename__ = "quiz"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)
    quiz = Column(Integer, nullable=False, index=True)
    attempt = Column(Integer)
    timestart = Column(BigInteger, index=True)
    timefinish = Column(BigInteger)
    sumgrades = Column(Float)
    duration_seconds = Column(Integer)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Note(Base):
    """Nilai aktivitas UnB."""
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)
    itemname = Column(String(255), index=True)
    finalgrade = Column(Float)
    timemodified = Column(Float, index=True)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class User(Base):
    """Data pengguna UnB."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    user_hash = Column(String(64), nullable=False, index=True)
    city = Column(String(100))
    country = Column(String(50))
    lang = Column(String(20), index=True)
    inscricao_time = Column(BigInteger, index=True)
    roleid = Column(Integer, index=True)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ============================================================
# OULAD DATASET (5 tabel)
# ============================================================

class OuladVle(Base):
    """Log interaksi VLE OULAD (file terbesar: 10,6 juta baris)."""
    __tablename__ = "oulad_vle"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    code_module = Column(String(10), nullable=False, index=True)
    code_presentation = Column(String(10), nullable=False, index=True)
    id_student = Column(Integer, nullable=False, index=True)
    id_site = Column(Integer, nullable=False, index=True)
    date = Column(Integer, index=True)
    sum_click = Column(Integer)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    __table_args__ = (
        Index('idx_oulad_vle_student_module', 'id_student', 'code_module'),
        Index('idx_oulad_vle_date', 'date'),
    )
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OuladAssessment(Base):
    """Nilai tugas OULAD."""
    __tablename__ = "oulad_assessment"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    id_assessment = Column(Integer, nullable=False, index=True)
    id_student = Column(Integer, nullable=False, index=True)
    date_submitted = Column(Integer, index=True)
    is_banked = Column(Integer)
    score = Column(Float)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OuladStudent(Base):
    """Demografi mahasiswa OULAD."""
    __tablename__ = "oulad_students"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    code_module = Column(String(10), nullable=False, index=True)
    code_presentation = Column(String(10), nullable=False, index=True)
    id_student = Column(Integer, nullable=False, index=True)
    gender = Column(String(5))
    region = Column(String(100))
    highest_education = Column(String(100))
    imd_band = Column(String(20))
    age_band = Column(String(20))
    num_of_prev_attempts = Column(Integer)
    studied_credits = Column(Integer)
    disability = Column(String(5))
    final_result = Column(String(20), index=True)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OuladCourse(Base):
    """Info kursus OULAD."""
    __tablename__ = "oulad_courses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    code_module = Column(String(10), nullable=False, index=True)
    code_presentation = Column(String(10), nullable=False, index=True)
    module_presentation_length = Column(Integer)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class OuladRegistration(Base):
    """Pendaftaran mahasiswa OULAD."""
    __tablename__ = "oulad_registration"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    sequence = Column(BigInteger, nullable=False)
    code_module = Column(String(10), nullable=False, index=True)
    code_presentation = Column(String(10), nullable=False, index=True)
    id_student = Column(Integer, nullable=False, index=True)
    date_registration = Column(Integer, index=True)
    date_unregistration = Column(Integer)
    ingested_at = Column(String(50))
    bot_name = Column(String(50))
    source = Column(String(50))
    
    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}