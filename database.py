from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///audit.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    action = Column(String(50))       # "onboard" or "offboard"
    target_upn = Column(String(255))
    department = Column(String(50))
    status = Column(String(20))       # "success" or "failed"
    detail = Column(Text)             # error message if failed


Base.metadata.create_all(engine)


def log_action(action, target_upn, department, status, detail=""):
    with SessionLocal() as db:
        db.add(AuditLog(
            action=action,
            target_upn=target_upn,
            department=department,
            status=status,
            detail=detail,
        ))
        db.commit()


def get_logs(limit=100):
    with SessionLocal() as db:
        rows = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "timestamp": r.timestamp.isoformat(),
                "action": r.action,
                "target_upn": r.target_upn,
                "department": r.department,
                "status": r.status,
                "detail": r.detail,
            }
            for r in rows
        ]