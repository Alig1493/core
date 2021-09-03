"""Base class for points plugins."""

import abc
import time

from django.db.models import F, Sum
from django.utils import timezone

from challenges.models import Score, Solve
from config import config
from core.base import Plugin
from hint.models import HintUse


class PointsPlugin(Plugin, abc.ABC):
    """Base class for points plugins."""

    plugin_type = "points"
    recalculate_type = "none"

    def __init__(self, challenge):
        """Set the challenge the plugin is calculating points for."""
        self.challenge = challenge

    @abc.abstractmethod
    def get_points(self, team, flag, solves, *args, **kwargs):
        """Return the amount of points a solve is worth."""
        pass

    def recalculate(self, teams, users, solves, *args, **kwargs):
        """Recalculate the amount of points a solve is worth."""
        pass

    def score(self, user, team, flag, solves, *args, **kwargs):
        """Score a solve for a user/team."""
        challenge = self.challenge
        points = self.get_points(team, flag, solves.count())

        deducted = HintUse.objects.filter(team=team, challenge=challenge).aggregate(points=Sum(F("hint__penalty")))
        deducted = 0 if deducted["points"] is None else deducted["points"]
        deducted = min(points, deducted)

        scored = config.get("end_time") >= time.time() and config.get("enable_scoring")
        score = Score(
            team=team,
            reason="challenge",
            points=points,
            penalty=deducted,
            leaderboard=scored,
            user=user,
            tiebreaker=challenge.tiebreaker,
        )
        score.save()

        solve = Solve(
            team=team,
            solved_by=user,
            challenge=challenge,
            first_blood=challenge.first_blood is None,
            flag=flag,
            score=score,
        )
        solve.save()

        user.points += points - deducted
        team.points += points - deducted
        if scored:
            user.leaderboard_points += points - deducted
            team.leaderboard_points += points - deducted
            if score.tiebreaker:
                user.last_score = timezone.now()
                team.last_score = timezone.now()

        return solve

    def register_incorrect_attempt(self, user, team, flag, solves, *args, **kwargs):
        """Register an incorrect solve for a team/user."""
        if config.get("enable_track_incorrect_submissions"):
            Solve(team=team, solved_by=user, challenge=self.challenge, flag=flag, correct=False, score=None).save()
