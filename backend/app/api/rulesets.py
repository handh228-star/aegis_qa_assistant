from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.models.database import get_db
from app.models.qa_ruleset import QARuleSet

router = APIRouter(prefix="/rulesets", tags=["rulesets"])


class RuleSetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    service_type: Optional[str] = None
    tree_rules: Optional[str] = None
    tc_rules: Optional[str] = None


class RuleSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    service_type: Optional[str] = None
    tree_rules: Optional[str] = None
    tc_rules: Optional[str] = None
    is_default: Optional[bool] = None


class RuleSetResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    service_type: Optional[str]
    tree_rules: Optional[str]
    tc_rules: Optional[str]
    is_default: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/", response_model=List[RuleSetResponse])
def list_rulesets(db: Session = Depends(get_db)):
    return db.query(QARuleSet).order_by(QARuleSet.is_default.desc(), QARuleSet.created_at.asc()).all()


@router.get("/{ruleset_id}", response_model=RuleSetResponse)
def get_ruleset(ruleset_id: int, db: Session = Depends(get_db)):
    rs = db.query(QARuleSet).filter(QARuleSet.id == ruleset_id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="룰셋을 찾을 수 없습니다")
    return rs


@router.post("/", response_model=RuleSetResponse)
def create_ruleset(data: RuleSetCreate, db: Session = Depends(get_db)):
    rs = QARuleSet(**data.model_dump())
    db.add(rs)
    db.commit()
    db.refresh(rs)
    return rs


@router.put("/{ruleset_id}", response_model=RuleSetResponse)
def update_ruleset(ruleset_id: int, data: RuleSetUpdate, db: Session = Depends(get_db)):
    rs = db.query(QARuleSet).filter(QARuleSet.id == ruleset_id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="룰셋을 찾을 수 없습니다")

    update_data = {k: v for k, v in data.model_dump().items() if v is not None}

    # 기본값으로 설정 시 기존 기본값 해제
    if update_data.get("is_default"):
        db.query(QARuleSet).filter(QARuleSet.id != ruleset_id).update({"is_default": False})

    for key, value in update_data.items():
        setattr(rs, key, value)

    rs.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rs)
    return rs


@router.delete("/{ruleset_id}")
def delete_ruleset(ruleset_id: int, db: Session = Depends(get_db)):
    rs = db.query(QARuleSet).filter(QARuleSet.id == ruleset_id).first()
    if not rs:
        raise HTTPException(status_code=404, detail="룰셋을 찾을 수 없습니다")
    if rs.is_system:
        raise HTTPException(status_code=400, detail="시스템 기본 룰셋은 삭제할 수 없습니다")
    db.delete(rs)
    db.commit()
    return {"message": "삭제되었습니다"}
