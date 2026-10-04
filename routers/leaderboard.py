from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional

from database import get_db
from core.dependencies import get_current_user
from models import User, UserSeasonPoints, Season
from services.cache_service import cache_service

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/season/{season_id}")
def season_leaderboard(
    season_id : int,
    limit     : int     = Query(10, ge=1, le=100),
    db        : Session = Depends(get_db)
):
    # check cache first
    if limit == 10:  # only cache default limit
        cached = cache_service.get_leaderboard(season_id)
        if cached:
            return {"source": "cache", "data": cached}

    # verify season exists
    season = db.query(Season).filter(Season.id == season_id).first()
    if not season:
        raise HTTPException(404, "Season not found")

    results = db.query(
        User.username,
        UserSeasonPoints.total_points,
        UserSeasonPoints.correct_predictions,
        UserSeasonPoints.total_predictions,
        UserSeasonPoints.current_streak,
        UserSeasonPoints.best_streak
    ).join(
        User, User.id == UserSeasonPoints.user_id
    ).filter(
        UserSeasonPoints.season_id == season_id,
        User.is_banned             == False,
        User.is_active             == True
    ).order_by(
        UserSeasonPoints.total_points.desc(),
        UserSeasonPoints.correct_predictions.desc()
        # secondary sort by correct predictions
        # if two users have same points
    ).limit(limit).all()

    data = [
        {
            "rank"               : i + 1,
            "username"           : r[0],
            "total_points"       : r[1],
            "correct_predictions": r[2],
            "total_predictions"  : r[3],
            "accuracy"           : round(
                (r[2] / r[3] * 100) if r[3] > 0 else 0, 1
            ),
            "current_streak"     : r[4],
            "best_streak"        : r[5]
        }
        for i, r in enumerate(results)
    ]

    if limit == 10:
        cache_service.set_leaderboard(season_id, data)

    return {
        "season" : season.name,
        "source" : "db",
        "data"   : data
    }


@router.get("/alltime")
def alltime_leaderboard(
    limit : int     = Query(10, ge=1, le=100),
    db    : Session = Depends(get_db)
):
    if limit == 10:
        cached = cache_service.get_alltime_leaderboard()
        if cached:
            return {"source": "cache", "data": cached}

    results = db.query(
        User.username,
        func.sum(UserSeasonPoints.total_points).label("total_points"),
        func.sum(UserSeasonPoints.correct_predictions).label("correct"),
        func.sum(UserSeasonPoints.total_predictions).label("total"),
        func.max(UserSeasonPoints.best_streak).label("best_streak")
    ).join(
        User, User.id == UserSeasonPoints.user_id
    ).filter(
        User.is_banned == False,
        User.is_active == True
    ).group_by(
        User.id, User.username
    ).order_by(
        func.sum(UserSeasonPoints.total_points).desc()
    ).limit(limit).all()

    data = [
        {
            "rank"               : i + 1,
            "username"           : r[0],
            "total_points"       : r[1],
            "correct_predictions": r[2],
            "total_predictions"  : r[3],
            "accuracy"           : round(
                (r[2] / r[3] * 100) if r[3] > 0 else 0, 1
            ),
            "best_streak"        : r[4]
        }
        for i, r in enumerate(results)
    ]

    if limit == 10:
        cache_service.set_alltime_leaderboard(data)

    return {"source": "db", "data": data}


@router.get("/my-stats")
def my_stats(
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    # get active season
    season = db.query(Season).filter(Season.is_active == True).first()
    if not season:
        raise HTTPException(404, "No active season")

    user_season = db.query(UserSeasonPoints).filter(
        UserSeasonPoints.user_id   == current_user.id,
        UserSeasonPoints.season_id == season.id
    ).first()

    if not user_season:
        return {
            "season"             : season.name,
            "total_points"       : 0,
            "correct_predictions": 0,
            "total_predictions"  : 0,
            "accuracy"           : 0.0,
            "current_streak"     : 0,
            "best_streak"        : 0,
            "rank"               : None
        }

    # calculate rank
    rank = db.query(UserSeasonPoints).filter(
        UserSeasonPoints.season_id   == season.id,
        UserSeasonPoints.total_points > user_season.total_points
    ).count() + 1

    return {
        "season"             : season.name,
        "total_points"       : user_season.total_points,
        "correct_predictions": user_season.correct_predictions,
        "total_predictions"  : user_season.total_predictions,
        "accuracy"           : round(
            (user_season.correct_predictions /
             user_season.total_predictions * 100)
            if user_season.total_predictions > 0 else 0, 1
        ),
        "current_streak"     : user_season.current_streak,
        "best_streak"        : user_season.best_streak,
        "rank"               : rank
    }
