"""
Quick sanity check that we can reach CognoDB with the official neo4j driver.
Run this BEFORE building anything else.

Usage:
    pip install -r requirements.txt
    cp .env.example .env      # then fill in your real values in .env
    python test_connection.py
"""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()  # reads .env in the current folder

URI = os.getenv("COGNODB_URI")
USER = os.getenv("COGNODB_USER")
PASSWORD = os.getenv("COGNODB_PASSWORD")


def main():
    if not all([URI, USER, PASSWORD]):
        print("Missing env vars. Did you copy .env.example to .env and fill it in?")
        sys.exit(1)

    try:
        driver = GraphDatabase.driver(URI, auth=(USER, PASSWORD))
        driver.verify_connectivity()
        print("Connected to CognoDB successfully.")

        with driver.session() as session:
            result = session.run("RETURN 'hello from CognoDB' AS message")
            record = result.single()
            print("Query result:", record["message"])

        driver.close()

    except Exception as e:
        print("Connection failed.")
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
