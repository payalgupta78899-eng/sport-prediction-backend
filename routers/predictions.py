from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db
from core.dependencies import get_current_user
from schemas import PredictionCreate, PredictionResponse
from models import Match, Prediction, Season, User
from services.audit_service import log_action

router = APIRouter(prefix="/predictions", tags=["Predictions"])


@router.post("/", status_code=201, response_model=PredictionResponse)
def submit_prediction(
    body         : PredictionCreate,
    request      : Request,
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    # get match and validate
    match = db.query(Match).filter(Match.id == body.match_id).first()
    if not match:
        raise HTTPException(404, "Match not found")

    if match.status != "upcoming":
        raise HTTPException(
            400,
            f"Predictions closed. Match is {match.status}."
        )

    # verify season is active
    season = db.query(Season).filter(
        Season.id       == match.season_id,
        Season.is_active == True
    ).first()
    if not season:
        raise HTTPException(400, "Season is not active")

    # validate predicted winner
    if body.predicted_winner not in [match.team_a, match.team_b]:
        raise HTTPException(
            400,
            f"Predicted winner must be '{match.team_a}' or '{match.team_b}'"
        )

    # check duplicate prediction
    existing = db.query(Prediction).filter(
        Prediction.user_id  == current_user.id,
        Prediction.match_id == body.match_id
    ).first()
    if existing:
        raise HTTPException(400, "You have already predicted this match")

    prediction = Prediction(
        user_id          = current_user.id,
        match_id         = body.match_id,
        predicted_winner = body.predicted_winner
    )
    db.add(prediction)

    log_action(
        db         = db,
        action     = "prediction.submitted",
        user_id    = current_user.id,
        entity     = "prediction",
        details    = {
            "match_id"        : body.match_id,
            "predicted_winner": body.predicted_winner
        },
        ip_address = request.client.host
    )

    db.commit()
    db.refresh(prediction)
    return prediction


@router.get("/mine", response_model=list[PredictionResponse])
def my_predictions(
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    return db.query(Prediction).filter(
        Prediction.user_id == current_user.id
    ).order_by(Prediction.created_at.desc()).all()


@router.get("/mine/season/{season_id}", response_model=list[PredictionResponse])
def my_predictions_by_season(
    season_id    : int,
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    return db.query(Prediction).join(
        Match, Match.id == Prediction.match_id
    ).filter(
        Prediction.user_id == current_user.id,
        Match.season_id    == season_id
    ).order_by(Prediction.created_at.desc()).all()
