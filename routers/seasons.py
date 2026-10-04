from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from core.dependencies import get_current_user, require_admin
from schemas import SeasonCreate, SeasonResponse
from models import Season, User
from services.audit_service import log_action
from services.cache_service import cache_service

router = APIRouter(prefix="/seasons", tags=["Seasons"])


@router.post("/", status_code=201, response_model=SeasonResponse)
def create_season(
    body         : SeasonCreate,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    # only one active season at a time
    active = db.query(Season).filter(Season.is_active == True).first()
    if active:
        raise HTTPException(
            400,
            f"Season '{active.name}' is still active. End it first."
        )

    if db.query(Season).filter(Season.name == body.name).first():
        raise HTTPException(400, "Season name already exists")

    season = Season(
        name        = body.name,
        description = body.description,
        start_date  = body.start_date,
        end_date    = body.end_date,
        is_active   = True
    )
    db.add(season)

    log_action(
        db         = db,
        action     = "season.created",
        user_id    = current_user.id,
        entity     = "season",
        details    = {"name": body.name},
        ip_address = request.client.host
    )

    db.commit()
    db.refresh(season)
    return season


@router.put("/{season_id}/end")
def end_season(
    season_id    : int,
    request      : Request,
    current_user : User    = Depends(require_admin),
    db           : Session = Depends(get_db)
):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(404, "Season not found")
    if not season.is_active:
        raise HTTPException(400, "Season is already ended")

    # check all matches have results
    from models import Match
    unresolved = db.query(Match).filter(
        Match.season_id == season_id,
        Match.winner    == None,
        Match.status    != "cancelled"
    ).count()

    if unresolved > 0:
        raise HTTPException(
            400,
            f"{unresolved} matches still have no result. Resolve them first."
        )

    season.is_active = False

    log_action(
        db         = db,
        action     = "season.ended",
        user_id    = current_user.id,
        entity     = "season",
        entity_id  = season_id,
        ip_address = request.client.host
    )

    db.commit()

    # bust leaderboard cache
    cache_service.bust_leaderboard(season_id)
    cache_service.bust_alltime_leaderboard()

    return {"message": f"Season '{season.name}' ended successfully"}


@router.get("/", response_model=list[SeasonResponse])
def get_seasons(db: Session = Depends(get_db)):
    return db.query(Season).order_by(Season.start_date.desc()).all()


@router.get("/active", response_model=SeasonResponse)
def get_active_season(db: Session = Depends(get_db)):
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season:
        raise HTTPException(404, "No active season currently")
    return season


@router.get("/{season_id}", response_model=SeasonResponse)
def get_season(season_id: int, db: Session = Depends(get_db)):
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(404, "Season not found")
    return season
