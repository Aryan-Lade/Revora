from sqlalchemy.orm import Session


def generate_synthetic_data(db: Session) -> None:
    from app.data.seeder import _seed
    _seed(db)
