"""Programmatic fixtures for resume-tailor tests.

No binary fixtures — every input is built in code so tests stay self-contained
and the fixtures evolve with the schema.
"""
from __future__ import annotations

import pytest


# ---------- JD text fixtures ----------

@pytest.fixture
def jd_text_typical() -> str:
    return """
Senior Backend Engineer
San Francisco, CA (Remote-friendly)

About the role
We're looking for a senior backend engineer to lead our payments platform.

What you'll do
- Design and build distributed services in Python and Go
- Lead a small team of 3-4 engineers through complex projects
- Partner with PMs and Designers on feature roadmap
- Improve system reliability and operational excellence

Required qualifications
- 5+ years backend engineering experience
- Strong Python or Go skills
- Experience with PostgreSQL or similar relational databases
- AWS or GCP production experience
- Comfortable mentoring junior engineers

Preferred qualifications
- Kafka or similar stream processing
- GraphQL API design
- Payments domain experience

Benefits
- Competitive comp
- Health/dental/vision
"""


@pytest.fixture
def jd_text_with_dealbreakers() -> str:
    return """
Staff Software Engineer

About: 10+ years experience required. US citizen with TS/SCI security clearance required.
Onsite 5 days per week. 25% travel. No sponsorship available.

Requirements:
- 10+ years building distributed systems
- Python, Go, or Rust
"""


@pytest.fixture
def jd_text_minimal() -> str:
    return "Junior Developer needed. 0-2 years experience. JavaScript and React."


# ---------- Inventory fixtures ----------

@pytest.fixture
def inventory_typical() -> dict:
    return {
        "_schema_version": "1.0",
        "candidate": {
            "name": "Alex Rivera",
            "email": "alex@example.com",
            "phone": "+1 555-555-1234",
            "location": "Austin, TX",
            "links": {"linkedin": "linkedin.com/in/alexrivera", "github": "github.com/alexrivera"},
        },
        "summary": "Backend engineer focused on payments and reliability.",
        "experiences": [
            {
                "company": "Acme Payments",
                "title": "Senior Backend Engineer",
                "location": "Remote",
                "start": "2022-03",
                "end": "Present",
                "context": "Payments team, ~80 engineers, $50M ARR.",
                "bullets": [
                    {
                        "text": "Led the migration of the orders service from REST to event-driven architecture using Kafka.",
                        "verbs": ["led", "migrated"],
                        "scope": {"team_size": 4, "scale": "$2M weekly volume", "duration": "6 months"},
                        "metrics": ["35%"],
                        "skills": ["Python", "Kafka", "PostgreSQL", "AWS"],
                        "tags": ["backend", "events"],
                    },
                    {
                        "text": "Reduced p99 latency 35% by adding a Redis read-through cache.",
                        "verbs": ["reduced"],
                        "scope": {"team_size": None, "scale": None, "duration": None},
                        "metrics": ["35%"],
                        "skills": ["Redis", "Python"],
                        "tags": ["performance"],
                    },
                    {
                        "text": "Mentored 3 junior engineers; 2 promoted within 18 months.",
                        "verbs": ["mentored"],
                        "scope": {"team_size": 3, "duration": "18 months"},
                        "metrics": [],
                        "skills": [],
                        "tags": ["leadership"],
                    },
                ],
            },
            {
                "company": "Beta Tech",
                "title": "Backend Engineer",
                "location": "Austin, TX",
                "start": "2019-06",
                "end": "2022-02",
                "context": "Series-B SaaS, ~40 engineers.",
                "bullets": [
                    {
                        "text": "Built a Python/FastAPI service for billing reconciliation, handling 200K req/day.",
                        "verbs": ["built"],
                        "scope": {"scale": "200K req/day"},
                        "metrics": ["200K"],
                        "skills": ["Python", "FastAPI", "PostgreSQL"],
                        "tags": ["backend"],
                    },
                ],
            },
        ],
        "education": [
            {"school": "UT Austin", "degree": "B.S.", "field": "Computer Science", "graduated": "2019"}
        ],
        "certifications": [],
        "skills": {
            "languages": ["Python", "Go", "TypeScript", "SQL"],
            "frameworks": ["FastAPI", "Django"],
            "databases": ["PostgreSQL", "Redis"],
            "cloud": ["AWS", "Docker", "Kubernetes"],
            "tools": ["Datadog"],
            "domains": ["Payments", "Distributed Systems"],
        },
        "projects": [],
    }


@pytest.fixture
def inventory_minimal() -> dict:
    return {
        "_schema_version": "1.0",
        "candidate": {"name": "Sam Lee", "email": "sam@example.com", "phone": "n/a", "location": "n/a", "links": {}},
        "summary": None,
        "experiences": [
            {
                "company": "Foo Inc",
                "title": "Engineer",
                "location": "Remote",
                "start": "2024-01",
                "end": "Present",
                "context": "",
                "bullets": [
                    {
                        "text": "Built React app for internal tool.",
                        "verbs": ["built"],
                        "scope": {},
                        "metrics": [],
                        "skills": ["React", "JavaScript"],
                        "tags": [],
                    }
                ],
            }
        ],
        "education": [],
        "certifications": [],
        "skills": {"languages": ["JavaScript"], "frameworks": ["React"]},
        "projects": [],
    }


# ---------- Tailored resume fixtures ----------

@pytest.fixture
def tailored_md_clean() -> str:
    """A tailored resume that traces fully to inventory_typical — should audit clean."""
    return """\
# Alex Rivera

Austin, TX | +1 555-555-1234 | alex@example.com | linkedin.com/in/alexrivera

## Summary

Senior backend engineer with payments and event-driven systems experience.

## Experience

### Acme Payments — Senior Backend Engineer
*Remote · Mar 2022 – Present*

- Led the migration of the orders service from REST to event-driven architecture using Kafka.
- Reduced p99 latency 35% by adding a Redis read-through cache.
- Mentored 3 junior engineers; 2 promoted within 18 months.

### Beta Tech — Backend Engineer
*Austin, TX · Jun 2019 – Feb 2022*

- Built a Python/FastAPI service for billing reconciliation, handling 200K req/day.

## Skills

**Languages:** Python, Go, SQL
**Databases:** PostgreSQL, Redis
**Cloud:** AWS

## Education

**B.S.**, Computer Science — UT Austin, 2019
"""


@pytest.fixture
def tailored_md_with_fabrication() -> str:
    """A tailored resume that fabricates: includes 50% (not in inventory),
    GraphQL (skill not in inventory), and a fictional Megacorp company."""
    return """\
# Alex Rivera

Austin, TX | +1 555-555-1234 | alex@example.com

## Experience

### Acme Payments — Senior Backend Engineer
*Remote · Mar 2022 – Present*

- Led the migration of the orders service from REST to event-driven architecture using Kafka.
- Improved performance by 50% with a comprehensive cache rewrite.
- Designed GraphQL APIs for the partner integration platform.

### Megacorp — Staff Engineer
*Anywhere · 2018 – 2022*

- Architected the payments platform for $1B in transactions.

## Skills

**Languages:** Python, Go, GraphQL, Rust
**Databases:** PostgreSQL, Redis, Cassandra

## Education

**B.S.**, Computer Science — UT Austin, 2019
"""
