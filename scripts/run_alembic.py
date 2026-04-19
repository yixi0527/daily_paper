from alembic.config import main

if __name__ == "__main__":
    main(argv=["-c", "apps/api/alembic.ini", *(__import__("sys").argv[1:] or ["upgrade", "head"])])
