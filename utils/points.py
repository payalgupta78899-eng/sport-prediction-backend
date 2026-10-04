from sqlalchemy.orm import Session
from core.config import settings


def get_current_streak(
    user_id         : int,
    current_pred_id : int,
    season_id       : int,
    db              : Session
) -> int:
    """
    Calculate REAL consecutive correct prediction streak.

    Fetches last 10 predictions in order (most recent first)
    within current season only.
    Stops counting as soon as a wrong prediction is found.

    This prevents fake streaks where wrong predictions
    in between are ignored.
    """
    from models.game import Prediction, Match

    # fetch last 10 predictions for this user in THIS season
    # ordered by most recent first
    # excluding current prediction being processed
    recent = db.query(Prediction).join(
        Match, Match.id == Prediction.match_id
    ).filter(
        Prediction.user_id == user_id,
        Prediction.id      != current_pred_id,
        Match.season_id    == season_id,        # same season only
        Match.winner       != None,             # finished matches only
        Prediction.is_correct != None           # result processed only
    ).order_by(
        Prediction.id.desc()                    # most recent first
    ).limit(10).all()

    # count consecutive correct predictions
    # stop immediately on wrong prediction
    streak = 0
    for pred in recent:
        if pred.is_correct:
            streak += 1
        else:
            break   # streak broken

    return streak


def calculate_points(streak: int) -> dict:
    """
    Calculate points and bonus based on streak.
    Returns base points + bonus + total.
    """
    base   = settings.POINTS_CORRECT_PREDICTION
    bonus  = 0
    reason = "correct prediction"

    if streak >= 9:   # 10 in a row (9 before + current)
        bonus  = settings.POINTS_STREAK_10_BONUS
        reason = "10-streak bonus"
    elif streak >= 4:  # 5 in a row (4 before + current)
        bonus  = settings.POINTS_STREAK_5_BONUS
        reason = "5-streak bonus"
    elif streak >= 2:  # 3 in a row (2 before + current)
        bonus  = settings.POINTS_STREAK_3_BONUS
        reason = "3-streak bonus"

    return {
        "base"       : base,
        "bonus"      : bonus,
        "total"      : base + bonus,
        "streak"     : streak + 1,  # include current
        "bonus_reason": reason
    }


def update_user_season_points(
    user_id       : int,
    season_id     : int,
    points_earned : int,
    is_correct    : bool,
    new_streak    : int,
    db            : Session
) -> None:
    """
    Update or create UserSeasonPoints record.
    Called inside a transaction — no commit here.
    """
    from models.game import UserSeasonPoints

    user_season = db.query(UserSeasonPoints).filter(
        UserSeasonPoints.user_id   == user_id,
        UserSeasonPoints.season_id == season_id
    ).with_for_update().first()
    # with_for_update() locks row to prevent race condition

    if user_season:
        user_season.total_predictions   += 1
        if is_correct:
            user_season.total_points        += points_earned
            user_season.correct_predictions += 1
            user_season.current_streak       = new_streak
            if new_streak > user_season.best_streak:
                user_season.best_streak = new_streak
        else:
            user_season.current_streak = 0
    else:
        # first prediction this season — create fresh record
        user_season = UserSeasonPoints(
            user_id             = user_id,
            season_id           = season_id,
            total_points        = points_earned if is_correct else 0,
            correct_predictions = 1 if is_correct else 0,
            total_predictions   = 1,
            current_streak      = new_streak if is_correct else 0,
            best_streak         = new_streak if is_correct else 0
        )
        db.add(user_season)
