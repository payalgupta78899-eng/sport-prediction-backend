from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from core.dependencies import get_current_user, require_moderator
from schemas import MatchCreate, MatchStatusUpdate, MatchResultUpdate, MatchResponse
from models import Season, Match, User
from services.audit_service import log_action
from services.cache_service import cache_service
from services.points_service import award_points_for_match

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.post("/", status_code=201, response_model=MatchResponse)
def create_match(
    body         : MatchCreate,
    request      : Request,
    current_user : User    = Depends(require_moderator),
    db           : Session = Depends(get_db)
):
    season = db.query(Season).filter(
        Season.id       == body.season_id,
        Season.is_active == True
    ).first()
    if not season:
        raise HTTPException(404, "Active season not found")

    match = Match(
        season_id  = body.season_id,
        team_a     = body.team_a,
        team_b     = body.team_b,
        match_date = body.match_date,
        venue      = body.venue,
        status     = "upcoming"
    )
    db.add(match)

    log_action(
        db         = db,
        action     = "match.created",
        user_id    = current_user.id,
        entity     = "match",
        details    = {"team_a": body.team_a, "team_b": body.team_b},
        ip_address = request.client.host
    )

    db.commit()
    db.refresh(match)
    return match


@router.put("/{match_id}/status")
def update_match_status(
    match_id     : int,
    body         : MatchStatusUpdate,
    request      : Request,
    current_user : User    = Depends(require_moderator),
    db           : Session = Depends(get_db)
):
    valid_statuses = ["upcoming", "live", "finished", "cancelled"]
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Status must be one of: {valid_statuses}")

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")
    if match.status == "finished":
        raise HTTPException(400, "Cannot change status of finished match")

    old_status    = match.status
    match.status  = body.status

    log_action(
        db         = db,
        action     = "match.status_updated",
        user_id    = current_user.id,
        entity     = "match",
        entity_id  = match_id,
        details    = {"old_status": old_status, "new_status": body.status},
        ip_address = request.client.host
    )

    db.commit()
    cache_service.bust_match(match_id)
    return {"message": f"Match status updated to {body.status}"}


@router.put("/{match_id}/result")
def set_match_result(
    match_id     : int,
    body         : MatchResultUpdate,
    request      : Request,
    current_user : User    = Depends(require_moderator),
    db           : Session = Depends(get_db)
):
    try:
        # lock match row — prevents two moderators setting result simultaneously
        match = db.query(Match).filter(
            Match.id == match_id
        ).with_for_update().first()

        if not match:
            raise HTTPException(404, "Match not found")
        if match.winner:
            raise HTTPException(400, "Result already set for this match")
        if match.status == "cancelled":
            raise HTTPException(400, "Cannot set result for cancelled match")
        if body.winner not in [match.team_a, match.team_b]:
            raise HTTPException(
                400,
                f"Winner must be '{match.team_a}' or '{match.team_b}'"
            )

        match.winner = body.winner
        match.status = "finished"

        # award points — full ACID transaction
        # all or nothing
        result = award_points_for_match(
            match_id  = match_id,
            season_id = match.season_id,
            winner    = body.winner,
            db        = db
        )

        log_action(
            db         = db,
            action     = "match.result_set",
            user_id    = current_user.id,
            entity     = "match",
            entity_id  = match_id,
            details    = {
                "winner"            : body.winner,
                "correct_predictors": result["correct_predictors"],
                "points_given"      : result["total_points_given"]
            },
            ip_address = request.client.host
        )

        db.commit()

        # bust caches after commit
        cache_service.bust_match(match_id)
        cache_service.bust_leaderboard(match.season_id)
        cache_service.bust_alltime_leaderboard()

        return {
            "message"            : "Result set and points awarded",
            "winner"             : body.winner,
            "correct_predictors" : result["correct_predictors"],
            "total_predictors"   : result["total_predictors"],
            "total_points_given" : result["total_points_given"]
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to set result: {str(e)}")


@router.get("/", response_model=list[MatchResponse])
def get_matches(
    season_id : Optional[int] = Query(None),
    status    : Optional[str] = Query(None),
    db        : Session       = Depends(get_db)
):
    query = db.query(Match)
    if season_id:
        query = query.filter(Match.season_id == season_id)
    if status:
        query = query.filter(Match.status == status)
    return query.order_by(Match.match_date.desc()).all()


@router.get("/{match_id}", response_model=MatchResponse)
def get_match(match_id: int, db: Session = Depends(get_db)):
    # check cache first
    cached = cache_service.get_match(match_id)
    if cached:
        return cached

    match = db.query(Match).filter(Match.id == match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")

    data = {
        "id"        : match.id,
        "season_id" : match.season_id,
        "team_a"    : match.team_a,
        "team_b"    : match.team_b,
        "match_date": str(match.match_date),
        "venue"     : match.venue,
        "status"    : match.status,
        "winner"    : match.winner,
        "created_at": str(match.created_at)
    }

    finished = match.status == "finished"
    cache_service.set_match(match_id, data, finished=finished)
    return match
