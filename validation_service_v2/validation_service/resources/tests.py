from uuid import UUID
from typing import List
from datetime import datetime
import logging

from fairgraph.base import KGQuery, as_list
from fairgraph.brainsimulation import ValidationTestDefinition, ValidationScript

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import ValidationError

from ..auth import get_kg_client, get_user_from_token, is_collab_member
from ..data_models import (Person, Species, BrainRegion, CellType, RecordingModality,
                           ValidationTestType, ScoreType,
                           ValidationTest, ValidationTestInstance,
                           ValidationTestPatch, ValidationTestInstancePatch)
from ..queries import build_validation_test_filters, test_alias_exists
from .. import settings


logger = logging.getLogger("validation_service_v2")

auth = HTTPBearer()
kg_client = get_kg_client()
router = APIRouter()


@router.get("/tests/")
def query_tests(alias: List[str] = Query(None),
                id: List[UUID] = Query(None),
                name: List[str] = Query(None),
                status: str = Query(None),
                brain_region: List[BrainRegion] = Query(None),
                species: List[Species] = Query(None),
                cell_type: List[CellType] = Query(None),
                data_type: List[str] = Query(None),
                data_modality: List[RecordingModality] = Query(None),
                test_type: List[ValidationTestType] = Query(None),
                score_type: List[ScoreType] = Query(None),
                author: List[str] = Query(None),
                size: int = Query(100),
                from_index: int = Query(0),
                # from header
                token: HTTPAuthorizationCredentials = Depends(auth)
                ):

    # get the values of of the Enums
    if brain_region:
        brain_region = [item.value for item in brain_region]
    if species:
        species = [item.value for item in species]
    if cell_type:
        cell_type = [item.value for item in cell_type]
    if data_modality:
        data_modality = [item.value for item in data_modality]
    if test_type:
        test_type = [item.value for item in test_type]
    if score_type:
        score_type = [item.value for item in score_type]

    filter_query, context = build_validation_test_filters(
        alias, id, name, status, brain_region, species, cell_type, data_type,
        data_modality, test_type, score_type, author)
    if len(filter_query["value"]) > 0:
        logger.info(f"Searching for ValidationTestDefinition with the following query: {filter_query}")
        # note that from_index is not currently supported by KGQuery.resolve
        query = KGQuery(ValidationTestDefinition, {"nexus": filter_query}, context)
        test_definitions = query.resolve(kg_client, api="nexus", size=size)
    else:
        test_definitions = ValidationTestDefinition.list(kg_client, api="nexus", size=size, from_index=from_index)
    return [ValidationTest.from_kg_object(test_definition, kg_client)
            for test_definition in test_definitions]

def _get_test_by_id_or_alias(test_id, token):
    try:
        test_id = UUID(test_id)
        test_definition = ValidationTestDefinition.from_uuid(str(test_id), kg_client, api="nexus")
    except ValueError:
        test_alias = test_id
        test_definition = ValidationTestDefinition.from_alias(test_alias, kg_client, api="nexus")
    if test_definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Test with ID or alias '{test_id}' not found.")
    # todo: fairgraph should accept UUID object as well as str
    return test_definition


def _get_test_instance_by_id(instance_id, token):
    test_instance = ValidationScript.from_uuid(str(instance_id), kg_client, api="nexus")
    if test_instance is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Test instance with ID '{instance_id}' not found.")

    test_definition = test_instance.test_definition.resolve(kg_client, api="nexus")
    # todo: in case of a dangling test instance, where the parent test_definition
    #       has been deleted but the instance wasn't, we could get a None here
    #       which we need to deal with
    return test_instance


@router.get("/tests/{test_id}", response_model=ValidationTest)
def get_test(test_id: str, token: HTTPAuthorizationCredentials = Depends(auth)):
    test_definition = _get_test_by_id_or_alias(test_id, token)
    return ValidationTest.from_kg_object(test_definition, kg_client)


@router.post("/tests/", response_model=ValidationTest, status_code=status.HTTP_201_CREATED)
def create_test(test: ValidationTest, token: HTTPAuthorizationCredentials = Depends(auth)):
    # check uniqueness of alias
    if test_alias_exists(test.alias, kg_client):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Another validation test with alias '{test.alias}' already exists.")
    kg_objects = test.to_kg_objects()
    recently_saved_scripts = []  # due to the time it takes for Nexus to become consistent,
                                 # we keep newly saved scripts to add to the result of the KG query
                                 # in case they are not yet included
    for obj in kg_objects:
        if isinstance(obj, ValidationTestDefinition):
            test_definition = obj
        elif isinstance(obj, ValidationScript):
            recently_saved_scripts.append(obj)
    if test_definition.exists(kg_client, api="any"):
        # see https://stackoverflow.com/questions/3825990/http-response-code-for-post-when-resource-already-exists
        # for a discussion of the most appropriate status code to use here
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Another validation test with the same name and timestamp already exists.")
    for obj in kg_objects:
        obj.save(kg_client)
    return ValidationTest.from_kg_object(test_definition, kg_client,
                                         recently_saved_scripts=recently_saved_scripts)


@router.put("/tests/{test_id}", response_model=ValidationTest, status_code=status.HTTP_200_OK)
def update_test(test_id: UUID, test_patch: ValidationTestPatch,
                 token: HTTPAuthorizationCredentials = Depends(auth)):
    # retrieve stored test
    test_definition = ValidationTestDefinition.from_uuid(str(test_id), kg_client, api="nexus")
    stored_test = ValidationTest.from_kg_object(test_definition, kg_client)
    # if alias changed, check uniqueness of new alias
    if (test_patch.alias
            and test_patch.alias != stored_test.alias
            and test_alias_exists(test_patch.alias, kg_client)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=f"Another validation test with alias '{test_patch.alias}' already exists.")
    # todo: if test id provided in payload, check it matches the test_id parameter
    # todo: if test uri provided in payload, check it matches the id

    # here we are updating the pydantic test `stored_test`, then recreating the kg objects
    # from this. It might be more efficient to directly update `test_definition`.
    # todo: profile both possible implementations
    update_data = test_patch.dict(exclude_unset=True)
    if "author" in update_data:
        update_data["author"] = [Person(**p) for p in update_data["author"]]
    updated_test = stored_test.copy(update=update_data)
    kg_objects = updated_test.to_kg_objects()
    for obj in kg_objects:
        obj.save(kg_client)
        if isinstance(obj, ValidationTestDefinition):
            test_definition = obj
    return ValidationTest.from_kg_object(test_definition, kg_client)


@router.delete("/tests/{test_id}", status_code=status.HTTP_200_OK)
def delete_test(test_id: UUID, token: HTTPAuthorizationCredentials = Depends(auth)):
    # todo: handle non-existent UUID
    test_definition = ValidationTestDefinition.from_uuid(str(test_id), kg_client, api="nexus")
    if not is_collab_member(settings.ADMIN_COLLAB_ID, token.credentials):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Deleting tests is restricted to admins")
    test_definition.delete(kg_client)
    for test_script in as_list(test_definition.scripts.resolve(kg_client, api="nexus")):
        test_script.delete(kg_client)


@router.get("/tests/{test_id}/instances/", response_model=List[ValidationTestInstance])
def get_test_instances(test_id: str,
                        token: HTTPAuthorizationCredentials = Depends(auth)):
    test_definition = _get_test_by_id_or_alias(test_id, token)
    test_instances = [ValidationTestInstance.from_kg_object(inst, kg_client)
                       for inst in as_list(test_definition.scripts.resolve(kg_client, api="nexus"))]
    return test_instances
    # todo: implement filter by version


@router.get("/tests/query/instances/{test_instance_id}", response_model=ValidationTestInstance)
def get_test_instance_from_instance_id(test_instance_id: UUID,
                                        token: HTTPAuthorizationCredentials = Depends(auth)):
     inst = _get_test_instance_by_id(test_instance_id, token)
     return ValidationTestInstance.from_kg_object(inst, kg_client)


@router.get("/tests/{test_id}/instances/latest", response_model=ValidationTestInstance)
def get_latest_test_instance_given_test_id(test_id: str,
                                             token: HTTPAuthorizationCredentials = Depends(auth)):
    test_definition = _get_test_by_id_or_alias(test_id, token)
    test_instances = [ValidationTestInstance.from_kg_object(inst, kg_client)
                       for inst in as_list(test_definition.scripts.resolve(kg_client, api="nexus"))]
    latest = sorted(test_instances, key=lambda inst: inst["timestamp"])[-1]
    return latest


@router.get("/tests/{test_id}/instances/{test_instance_id}", response_model=ValidationTestInstance)
def get_test_instance_given_test_id(test_id: str,
                                    test_instance_id: UUID,
                                    token: HTTPAuthorizationCredentials = Depends(auth)):
    test_definition = _get_test_by_id_or_alias(test_id, token)
    for inst in as_list(test_definition.scripts.resolve(kg_client, api="nexus")):
        if UUID(inst.uuid) == test_instance_id:
            return ValidationTestInstance.from_kg_object(inst, kg_client)
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Test ID and test instance ID are inconsistent")


@router.get("/tests/query/instances/{test_instance_id}", response_model=ValidationTestInstance)
def get_test_instance_from_instance_id(test_instance_id: UUID,
                                       token: HTTPAuthorizationCredentials = Depends(auth)):
    test_instance_kg = _get_test_instance_by_id(test_instance_id, token)
    return ValidationTestInstance.from_kg_object(test_instance_kg, kg_client)


@router.post("/tests/{test_id}/instances/",
             response_model=ValidationTestInstance, status_code=status.HTTP_201_CREATED)
def create_test_instance(test_id: str,
                         test_instance: ValidationTestInstance,
                         token: HTTPAuthorizationCredentials = Depends(auth)):
    test_definition = _get_test_by_id_or_alias(test_id, token)
    kg_object = test_instance.to_kg_objects(test_definition)[0]
    kg_object.save(kg_client)
    return ValidationTestInstance.from_kg_object(kg_object, kg_client)


@router.put("/tests/{test_id}/instances/{test_instance_id}",
         response_model=ValidationTestInstance, status_code=status.HTTP_200_OK)
def update_test_instance(test_id: str,
                         test_instance_id: str,
                         test_instance_patch: ValidationTestInstancePatch,
                         token: HTTPAuthorizationCredentials = Depends(auth)):
    validation_script = _get_test_instance_by_id(test_instance_id, token)
    test_definition_kg = _get_test_by_id_or_alias(test_id, token)
    return _update_test_instance(validation_script, test_definition_kg, test_instance_patch, token)


@router.put("/tests/query/instances/{test_instance_id}",
         response_model=ValidationTestInstance, status_code=status.HTTP_200_OK)
def update_test_instance_by_id(test_instance_id: str,
                               test_instance_patch: ValidationTestInstancePatch,
                               token: HTTPAuthorizationCredentials = Depends(auth)):
    validation_script = _get_test_instance_by_id(test_instance_id, token)
    test_definition_kg = validation_script.test_definition.resolve(kg_client, api="nexus")
    return _update_test_instance(validation_script, test_definition_kg, test_instance_patch, token)


def _update_test_instance(validation_script, test_definition_kg, test_instance_patch, token):
    stored_test_instance = ValidationTestInstance.from_kg_object(validation_script, kg_client)
    update_data = test_instance_patch.dict(exclude_unset=True)
    updated_test_instance = stored_test_instance.copy(update=update_data)
    kg_objects = updated_test_instance.to_kg_objects(test_definition_kg)
    for obj in kg_objects:
        obj.save(kg_client)
    test_instance_kg = kg_objects[-1]
    assert isinstance(test_instance_kg, ValidationScript)
    return ValidationTestInstance.from_kg_object(test_instance_kg, kg_client)