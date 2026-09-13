from sqlalchemy import text

from app.database import engine


def test_postgresql_connection_executes_select_one():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()

    assert result == 1
