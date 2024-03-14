from sqlalchemy import func
from sqlalchemy.orm import Session

from sql_app.models import Network


def get_networks(db: Session, skip: int = 0, limit: int = 100):
    subquery = db.query(
        Network,
        func.rank().over(
            order_by=Network.timestamp.desc(),
            partition_by=Network.denom
        ).label('rnk')
    ).subquery()
    networks = db.query(subquery).filter(
        subquery.c.rnk == 1
    ).all()
    return networks
