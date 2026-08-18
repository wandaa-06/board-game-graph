"""
Core Cypher queries for the Board Game Recommendation Graph.
Run this standalone to sanity-check each query against the seeded data
before wiring them into the Flask app.

Usage:
    python queries.py
"""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()

URI = os.getenv("COGNODB_URI")
USER = os.getenv("COGNODB_USER")
PASSWORD = os.getenv("COGNODB_PASSWORD")


# ---------------------------------------------------------------------------
# Query 1: Multi-hop recommendation (2 hops)
# "Given a game, find other games that share at least 2 mechanics with it."
# Path: Game -> HAS_MECHANIC -> Mechanic <- HAS_MECHANIC <- Game
# ---------------------------------------------------------------------------
def recommend_by_shared_mechanics(driver, game_name, min_shared=2):
    query = """
    MATCH (g:Game {name: $game_name})-[:HAS_MECHANIC]->(m:Mechanic)
          <-[:HAS_MECHANIC]-(other:Game)
    WHERE other.name <> $game_name
    WITH other, collect(m.name) AS shared_mechanics, count(m) AS shared_count
    WHERE shared_count >= $min_shared
    RETURN other.name AS recommended_game,
           shared_mechanics,
           shared_count
    ORDER BY shared_count DESC
    """
    with driver.session() as session:
        result = session.run(
            query, game_name=game_name, min_shared=min_shared
        )
        return [record.data() for record in result]


# ---------------------------------------------------------------------------
# Query 2: Variable-length path between two games (SQL-awkward)
# "How are two games connected through shared mechanics, themes, or
# designers, within N hops?" This kind of flexible-depth traversal needs
# recursive CTEs in SQL; in Cypher it's a single pattern.
# ---------------------------------------------------------------------------
def shortest_connection(driver, game_a, game_b, max_hops=4):
    query = """
    MATCH path = shortestPath(
        (a:Game {name: $game_a})-[*..%d]-(b:Game {name: $game_b})
    )
    RETURN [node IN nodes(path) |
                coalesce(node.name, labels(node)[0])] AS path_nodes,
           length(path) AS hops
    """ % max_hops
    with driver.session() as session:
        result = session.run(query, game_a=game_a, game_b=game_b)
        record = result.single()
        return record.data() if record else None


# ---------------------------------------------------------------------------
# Query 3: Designer's "range" — designers who've worked across many themes
# (a simple aggregation query, useful for a designer profile page)
# ---------------------------------------------------------------------------
def designer_theme_range(driver, designer_name):
    query = """
    MATCH (d:Designer {name: $designer_name})<-[:DESIGNED_BY]-(g:Game)
          -[:HAS_THEME]->(t:Theme)
    RETURN d.name AS designer,
           collect(DISTINCT t.name) AS themes_covered,
           count(DISTINCT g) AS games_designed
    """
    with driver.session() as session:
        result = session.run(query, designer_name=designer_name)
        record = result.single()
        return record.data() if record else None


# ---------------------------------------------------------------------------
# Query 4: List all games (for the browse/home page), optionally filtered
# by mechanic and/or theme.
# ---------------------------------------------------------------------------
def list_games(driver, mechanic=None, theme=None):
    query = """
    MATCH (g:Game)
    OPTIONAL MATCH (g)-[:HAS_MECHANIC]->(m:Mechanic)
    OPTIONAL MATCH (g)-[:HAS_THEME]->(t:Theme)
    OPTIONAL MATCH (g)-[:DESIGNED_BY]->(d:Designer)
    WITH g, collect(DISTINCT m.name) AS mechanics,
            collect(DISTINCT t.name) AS themes,
            d.name AS designer
    WHERE ($mechanic IS NULL OR $mechanic IN mechanics)
      AND ($theme IS NULL OR $theme IN themes)
    RETURN g.name AS name,
           g.year_published AS year_published,
           g.min_players AS min_players,
           g.max_players AS max_players,
           g.play_time_minutes AS play_time_minutes,
           mechanics,
           themes,
           designer
    ORDER BY g.name
    """
    with driver.session() as session:
        result = session.run(query, mechanic=mechanic, theme=theme)
        return [record.data() for record in result]


# ---------------------------------------------------------------------------
# Query 5: Full detail for a single game, including its 1-hop mechanic/theme/
# designer neighbors (used to draw the "connection web" on the game page).
# ---------------------------------------------------------------------------
def get_game(driver, game_name):
    query = """
    MATCH (g:Game {name: $game_name})
    OPTIONAL MATCH (g)-[:HAS_MECHANIC]->(m:Mechanic)
    OPTIONAL MATCH (g)-[:HAS_THEME]->(t:Theme)
    OPTIONAL MATCH (g)-[:DESIGNED_BY]->(d:Designer)
    RETURN g.name AS name,
           g.year_published AS year_published,
           g.min_players AS min_players,
           g.max_players AS max_players,
           g.play_time_minutes AS play_time_minutes,
           collect(DISTINCT m.name) AS mechanics,
           collect(DISTINCT t.name) AS themes,
           d.name AS designer
    """
    with driver.session() as session:
        result = session.run(query, game_name=game_name)
        record = result.single()
        return record.data() if record else None


# ---------------------------------------------------------------------------
# Query 6: Distinct mechanics / themes, used to populate filter dropdowns.
# ---------------------------------------------------------------------------
def list_mechanics(driver):
    with driver.session() as session:
        result = session.run("MATCH (m:Mechanic) RETURN m.name AS name ORDER BY name")
        return [record["name"] for record in result]


def list_themes(driver):
    with driver.session() as session:
        result = session.run("MATCH (t:Theme) RETURN t.name AS name ORDER BY name")
        return [record["name"] for record in result]


def list_designers(driver):
    with driver.session() as session:
        result = session.run("MATCH (d:Designer) RETURN d.name AS name ORDER BY name")
        return [record["name"] for record in result]


def main():
    driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
    try:
        driver.verify_connectivity()

        print("\n--- Query 1: Games sharing 2+ mechanics with 'Starforge Dominion' ---")
        for row in recommend_by_shared_mechanics(driver, "Starforge Dominion"):
            print(row)

        print("\n--- Query 2: Shortest connection between 'Whispering Marsh' and 'Sable & Steel' ---")
        print(shortest_connection(driver, "Whispering Marsh", "Sable & Steel"))

        print("\n--- Query 3: Theme range for designer 'Elin Voss' ---")
        print(designer_theme_range(driver, "Elin Voss"))

    finally:
        driver.close()


if __name__ == "__main__":
    main()
