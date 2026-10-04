from sqlalchemy.orm import Session
from models import Prediction, UserSeasonPoints, Match

POINTS_CONFIG = {
    "correct_prediction" : 10,
    "streak_3_bonus"     : 5,
    "streak_5_bonus"     : 15,
    "streak_10_bonus"    : 30,
}


def get_real_streak(
    user_id         : int,
    current_pred_id : int,
    season_id       : int,
    db              : Session
) -> int:
    """
    Get REAL consecutive correct streak.
    Fetches predictions in order and stops at first wrong one.
    Only counts within current season.
    """
    recent = db.query(Prediction).join(
        Match, Match.id == Prediction.match_id
    ).filter(
        Prediction.user_id == user_id,
        Prediction.id      != current_pred_id,
        Prediction.is_correct.isnot(None),  # only decided predictions
        Match.season_id    == season_id     # current season only
    ).order_by(
        Prediction.id.desc()
    ).limit(15).all()

    streak = 0
    for pred in recent:
        if pred.is_correct:
            streak += 1
        else:
            break  # wrong prediction — streak broken, stop counting

    return streak


def calculate_points(streak: int) -> int:
    """Calculate total points including streak bonus"""
    points = POINTS_CONFIG["correct_prediction"]

    if streak >= 9:    # 10th correct in a row
        points += POINTS_CONFIG["streak_10_bonus"]
    elif streak >= 4:  # 5th correct in a row
        points += POINTS_CONFIG["streak_5_bonus"]
    elif streak >= 2:  # 3rd correct in a row
        points += POINTS_CONFIG["streak_3_bonus"]

    return points


def award_points_for_match(
    match_id  : int,
    season_id : int,
    winner    : str,
    db        : Session
) -> dict:
    """
    Award points to all correct predictors for a match.
    Full ACID transaction — all or nothing.
    Returns summary of what happened.
    """
    correct_predictions = db.query(Prediction).filter(
        Prediction.match_id         == match_id,
        Prediction.predicted_winner == winner
    ).all()

    all_predictions = db.query(Prediction).filter(
        Prediction.match_id == match_id
    ).all()

    total_awarded = 0

    # mark ALL predictions for this match as decided
    for pred in all_predictions:
        pred.is_correct = (pred.predicted_winner == winner)

    # award points to correct predictors
    for pred in correct_predictions:
        streak        = get_real_streak(pred.user_id, pred.id, season_id, db)
        points        = calculate_points(streak)
        pred.points_earned = points
        total_awarded += points

        # get or create UserSeasonPoints record
        user_season = db.query(UserSeasonPoints).filter(
            UserSeasonPoints.user_id   == pred.user_id,
            UserSeasonPoints.season_id == season_id
        ).with_for_update().first()

        new_streak = streak + 1  # current correct prediction extends streak

        if user_season:
            user_season.total_points        += points
            user_season.correct_predictions += 1
            user_season.total_predictions   += 1
            user_season.current_streak       = new_streak
            user_season.best_streak          = max(
                user_season.best_streak, new_streak
            )
        else:
            user_season = UserSeasonPoints(
                user_id             = pred.user_id,
                season_id           = season_id,
                total_points        = points,
                correct_predictions = 1,
                total_predictions   = 1,
                current_streak      = new_streak,
                best_streak         = new_streak
            )
            db.add(user_season)

    # update total predictions for wrong predictors
    wrong_predictions = [p for p in all_predictions if p.predicted_winner != winner]
    for pred in wrong_predictions:
        user_season = db.query(UserSeasonPoints).filter(
            UserSeasonPoints.user_id   == pred.user_id,
            UserSeasonPoints.season_id == season_id
        ).with_for_update().first()

        if user_season:
            user_season.total_predictions += 1
            user_season.current_streak     = 0  # reset streak on wrong
        else:
            user_season = UserSeasonPoints(
                user_id             = pred.user_id,
                season_id           = season_id,
                total_points        = 0,
                correct_predictions = 0,
                total_predictions   = 1,
                current_streak      = 0,
                best_streak         = 0
            )
            db.add(user_season)

    return {
        "correct_predictors" : len(correct_predictions),
        "total_predictors"   : len(all_predictions),
        "total_points_given" : total_awarded
    }
