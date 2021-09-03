"""Views for the stats app."""

import os
from datetime import datetime, timezone

from challenges.models import Score
from challenges.sql import get_incorrect_solve_counts, get_solve_counts
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Sum
from django_prometheus.exports import ExportToDjangoView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.views import APIView

from config import config
from core.response import FormattedResponse
from teams.models import UserIP
from stats.signals import correct_solve_count, member_count, solve_count, team_count
from teams.models import Team


@api_view(["GET"])
def countdown(request):
    """View to show the countdown for when registration opens, the event starts, and the event ends."""
    return FormattedResponse(
        {
            "countdown_timestamp": config.get("start_time"),
            "registration_open": config.get("register_start_time"),
            "competition_end": config.get("end_time"),
            "server_timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )


@api_view(["GET"])
def stats(request):
    """View to display some stats about the event."""
    users = get_user_model().objects.count()
    teams = Team.objects.count()
    if users > 0 and teams > 0:
        average = users / teams
    else:
        average = 0

    solve_count = sum(get_solve_counts().values())
    total_solve_count = solve_count + sum(get_incorrect_solve_counts().values())

    return FormattedResponse(
        {
            "user_count": users,
            "team_count": teams,
            "solve_count": total_solve_count,
            "correct_solve_count": solve_count,
            "avg_members": average,
        }
    )


@api_view(["GET"])
@permission_classes([IsAdminUser])
def full(request):
    """View to display full statistics to event admins."""
    challenge_data = {}
    correct_solve_counts = get_solve_counts()
    incorrect_solve_counts = get_incorrect_solve_counts()
    for challenge in correct_solve_counts:
        challenge_data[challenge] = {}
        challenge_data[challenge]["correct"] = correct_solve_counts.get(challenge, 0)
    for challenge in incorrect_solve_counts:
        if challenge not in challenge_data:
            challenge_data[challenge] = {}
        challenge_data[challenge]["incorrect"] = incorrect_solve_counts.get(challenge, 0)

    point_distribution = {}
    for team in Team.objects.all():
        if not point_distribution.get(team.points):
            point_distribution[team.points] = 0
        point_distribution[team.points] += 1

    return FormattedResponse(
        {
            "users": {
                "all": get_user_model().objects.count(),
                "confirmed": get_user_model().objects.filter(email_verified=True).count(),
            },
            "teams": Team.objects.count(),
            "ips": UserIP.objects.count(),
            "total_points": Score.objects.all().aggregate(Sum("points"))["points__sum"],
            "challenges": challenge_data,
            "team_point_distribution": point_distribution,
        }
    )


@api_view(["GET"])
@permission_classes((IsAdminUser,))
def version(request):
    """Get the current commit hash."""
    return FormattedResponse({"commit_hash": os.popen("git rev-parse HEAD").read().strip()})


class PrometheusMetricsView(APIView):
    """API endpoints related to prometheus."""

    permission_classes = [IsAdminUser]

    def get(self, request, format=None):
        """Get displayable statistics."""
        member_count.set(cache.get("member_count"))
        team_count.set(cache.get("team_count"))
        solve_count.set(cache.get("solve_count"))
        correct_solve_count.set(cache.get("correct_solve_count"))

        return ExportToDjangoView(request)
