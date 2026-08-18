"""
Seeds CognoDB with a small graph of fictional board games, mechanics, themes,
and designers.

Usage:
    python seed_data.py
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("COGNODB_URI")
USER = os.getenv("COGNODB_USER")
PASSWORD = os.getenv("COGNODB_PASSWORD")

# ---------------------------------------------------------------------------
# Seed data: fictional games, deliberately overlapping in mechanics/themes/
# designers so the multi-hop recommendation queries have something to find.
# ---------------------------------------------------------------------------
GAMES = [
    {
        "name": "Starforge Dominion",
        "year_published": 2019,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 90,
        "mechanics": ["Worker Placement", "Deck Building"],
        "themes": ["Sci-Fi", "Economic"],
        "designer": "Elin Voss",
    },
    {
        "name": "Crimson Harvest",
        "year_published": 2017,
        "min_players": 2,
        "max_players": 5,
        "play_time_minutes": 60,
        "mechanics": ["Worker Placement", "Set Collection"],
        "themes": ["Economic", "Fantasy"],
        "designer": "Elin Voss",
    },
    {
        "name": "Shattered Reliquary",
        "year_published": 2021,
        "min_players": 1,
        "max_players": 4,
        "play_time_minutes": 75,
        "mechanics": ["Deck Building", "Cooperative"],
        "themes": ["Fantasy", "Horror"],
        "designer": "Tomas Reyk",
    },
    {
        "name": "Ashen Tides",
        "year_published": 2020,
        "min_players": 2,
        "max_players": 6,
        "play_time_minutes": 120,
        "mechanics": ["Area Control", "Set Collection"],
        "themes": ["Fantasy", "War"],
        "designer": "Marguerite Lowe",
    },
    {
        "name": "Neon Syndicate",
        "year_published": 2022,
        "min_players": 3,
        "max_players": 5,
        "play_time_minutes": 45,
        "mechanics": ["Bluffing", "Hand Management"],
        "themes": ["Sci-Fi", "Crime"],
        "designer": "Tomas Reyk",
    },
    {
        "name": "The Hollow Court",
        "year_published": 2018,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 90,
        "mechanics": ["Bluffing", "Area Control"],
        "themes": ["Fantasy", "Political"],
        "designer": "Marguerite Lowe",
    },
    {
        "name": "Ironclad Frontier",
        "year_published": 2016,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 100,
        "mechanics": ["Worker Placement", "Area Control"],
        "themes": ["Economic", "War"],
        "designer": "Priya Nandakumar",
    },
    {
        "name": "Whispering Marsh",
        "year_published": 2023,
        "min_players": 1,
        "max_players": 4,
        "play_time_minutes": 50,
        "mechanics": ["Cooperative", "Hand Management"],
        "themes": ["Horror", "Fantasy"],
        "designer": "Priya Nandakumar",
    },
    {
        "name": "Sable & Steel",
        "year_published": 2019,
        "min_players": 2,
        "max_players": 2,
        "play_time_minutes": 40,
        "mechanics": ["Hand Management", "Bluffing"],
        "themes": ["Political", "War"],
        "designer": "Elin Voss",
    },
    {
        "name": "Colony Zero",
        "year_published": 2021,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 110,
        "mechanics": ["Worker Placement", "Deck Building"],
        "themes": ["Sci-Fi", "Cooperative Survival"],
        "designer": "Tomas Reyk",
    },
    {
        "name": "Gilded Serpent",
        "year_published": 2015,
        "min_players": 3,
        "max_players": 6,
        "play_time_minutes": 60,
        "mechanics": ["Set Collection", "Bluffing"],
        "themes": ["Economic", "Political"],
        "designer": "Marguerite Lowe",
    },
    {
        "name": "Deepwake Chronicles",
        "year_published": 2022,
        "min_players": 1,
        "max_players": 5,
        "play_time_minutes": 130,
        "mechanics": ["Cooperative", "Area Control"],
        "themes": ["Horror", "Sci-Fi"],
        "designer": "Priya Nandakumar",
    },
    {
        "name": "Thornwatch Keep",
        "year_published": 2020,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 80,
        "mechanics": ["Deck Building", "Area Control"],
        "themes": ["Fantasy", "War"],
        "designer": "Elin Voss",
    },
    {
        "name": "Static Horizon",
        "year_published": 2023,
        "min_players": 2,
        "max_players": 4,
        "play_time_minutes": 55,
        "mechanics": ["Hand Management", "Deck Building"],
        "themes": ["Sci-Fi", "Economic"],
        "designer": "Tomas Reyk",
    },
    {
        "name": "Blackmire Bargain",
        "year_published": 2017,
        "min_players": 3,
        "max_players": 5,
        "play_time_minutes": 65,
        "mechanics": ["Bluffing", "Set Collection"],
        "themes": ["Fantasy", "Political"],
        "designer": "Priya Nandakumar",
    },
    {
        "name": "Wraithbound Legacy",
        "year_published": 2018,
        "min_players": 1,
        "max_players": 4,
        "play_time_minutes": 95,
        "mechanics": ["Cooperative", "Deck Building"],
        "themes": ["Horror", "Fantasy"],
        "designer": "Marguerite Lowe",
    },
]


def seed(driver):
    with driver.session() as session:
        # Constraints -> uniqueness + fast lookups on MERGE
        session.run(
            "CREATE CONSTRAINT game_name IF NOT EXISTS "
            "FOR (g:Game) REQUIRE g.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT mechanic_name IF NOT EXISTS "
            "FOR (m:Mechanic) REQUIRE m.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT theme_name IF NOT EXISTS "
            "FOR (t:Theme) REQUIRE t.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT designer_name IF NOT EXISTS "
            "FOR (d:Designer) REQUIRE d.name IS UNIQUE"
        )

        # Bulk load via UNWIND, all parameterized (no string concatenation)
        session.run(
            """
            UNWIND $games AS game
            MERGE (g:Game {name: game.name})
            SET g.year_published = game.year_published,
                g.min_players = game.min_players,
                g.max_players = game.max_players,
                g.play_time_minutes = game.play_time_minutes

            MERGE (d:Designer {name: game.designer})
            MERGE (g)-[:DESIGNED_BY]->(d)

            WITH g, game
            UNWIND game.mechanics AS mechanic_name
            MERGE (m:Mechanic {name: mechanic_name})
            MERGE (g)-[:HAS_MECHANIC]->(m)

            WITH g, game
            UNWIND game.themes AS theme_name
            MERGE (t:Theme {name: theme_name})
            MERGE (g)-[:HAS_THEME]->(t)
            """,
            games=GAMES,
        )

    print(f"Seeded {len(GAMES)} games with mechanics, themes, and designers.")


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()
        seed(driver)
    finally:
        driver.close()


if __name__ == "__main__":
    main()
