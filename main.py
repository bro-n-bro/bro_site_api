from typing import Union, List

import uvicorn
from fastapi import FastAPI, Depends
from fastapi_utils.tasks import repeat_every
from sqlalchemy.orm import Session

from sql_app.crud import get_networks, get_info
from sql_app.database import engine, Base, sessionmaker_for_periodic_task, get_db
from sql_app.schemas import Network, FullInfo
from sql_app.sync import sync_networks


def create_tables():
    Base.metadata.create_all(bind=engine)


def start_application():
    app = FastAPI()
    create_tables()
    return app


app = start_application()


@app.get("/networks/", response_model=FullInfo)
def read_networks(db: Session = Depends(get_db)):
    return get_info(db)


@app.on_event("startup")
@repeat_every(seconds=14400)
def sync_tokens_task() -> None:
    with sessionmaker_for_periodic_task.context_session() as db:
        sync_networks(db)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)
