from sqlalchemy import func
from sqlalchemy.orm import Session

from sql_app.models import Network
from sql_app import schemas


def get_networks(db: Session):
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


def get_info(db: Session) -> schemas.FullInfo:
    networks = get_networks(db)
    networks = [schemas.Network(**network) for network in networks]
    return schemas.FullInfo(infos=networks)
