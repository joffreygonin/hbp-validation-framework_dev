from uuid import UUID
from enum import Enum
from typing import List
from datetime import datetime
from urllib.parse import quote_plus, urlencode
import os
import logging
import itertools
from requests.exceptions import HTTPError

from fairgraph.client import KGClient, SCOPE_MAP
from fairgraph.base import KGQuery, KGProxy, as_list
import fairgraph.brainsimulation

from fastapi import APIRouter, Depends, Header, Query, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from ..auth import get_kg_client, get_user_from_token
from ..data_models import Simulation, ConsistencyError
from .. import settings


logger = logging.getLogger("validation_service_v2")

auth = HTTPBearer()
kg_client = get_kg_client()
router = APIRouter()



@router.get("/simulations/", response_model=List[Simulation])
def query_simulations(
    size: int = Query(100),
    from_index: int = Query(0),
    # from header
    token: HTTPAuthorizationCredentials = Depends(auth),
):
    pass



@router.get("/simulations/{simulation_id}", response_model=Simulation)
def get_simulation(simulation_id: UUID, token: HTTPAuthorizationCredentials = Depends(auth)):
    simulation_activity = fairgraph.brainsimulation.Simulation.from_uuid(str(simulation_id), kg_client, api="nexus")
    if simulation_activity:
        try:
            obj = Simulation.from_kg_object(simulation_activity, kg_client)
        except ConsistencyError as err:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(err))
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Simulation {simulation_id} not found.",
        )
    return obj


@router.post("/simulations/", response_model=Simulation, status_code=status.HTTP_201_CREATED)
def create_simulation(simulation: Simulation, token: HTTPAuthorizationCredentials = Depends(auth)):
    logger.info("Beginning post simulation")
    kg_objects = simulation.to_kg_objects(kg_client, token)
    logger.info("Created objects")
    for label in ('person', 'config', 'outputs', 'hardware', 'dependencies', 'env', 'activity'):
        for obj in as_list(kg_objects[label]):
            obj.save(kg_client)
    for obj in as_list(kg_objects['outputs']):
        obj.generated_by = kg_objects['activity']
        obj.save(kg_client)
    logger.info("Saved objects")

    return Simulation.from_kg_object(kg_objects['activity'], kg_client)
