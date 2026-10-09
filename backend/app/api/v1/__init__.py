from fastapi import APIRouter

from app.api.v1 import (
    alerts,
    analytics,
    applications,
    auth,
    calendar_suggestions,
    career_goals,
    command_center,
    contacts,
    cover_letters,
    deal_breakers,
    discovery_sources,
    emails,
    follow_ups,
    insights,
    integrations,
    interview_kits,
    jobs,
    leads,
    matches,
    notifications,
    outreach_drafts,
    practice,
    profile,
    resumes,
    star_stories,
    tailor_runs,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(career_goals.router)
api_router.include_router(deal_breakers.router)
api_router.include_router(resumes.router)
api_router.include_router(jobs.router)
api_router.include_router(leads.router)
api_router.include_router(discovery_sources.router)
api_router.include_router(matches.router)
api_router.include_router(applications.router)
api_router.include_router(notifications.router)
api_router.include_router(alerts.router)
api_router.include_router(tailor_runs.router)
api_router.include_router(cover_letters.router)
api_router.include_router(interview_kits.router)
api_router.include_router(practice.router)
api_router.include_router(star_stories.router)
api_router.include_router(insights.router)
api_router.include_router(command_center.router)
api_router.include_router(contacts.router)
api_router.include_router(follow_ups.router)
api_router.include_router(outreach_drafts.router)
api_router.include_router(integrations.router)
api_router.include_router(emails.router)
api_router.include_router(calendar_suggestions.router)
api_router.include_router(analytics.router)
