from __future__ import annotations

import asyncio
from contextlib import suppress
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status

from vikram_api.contracts import (
    AiPolicyResponse,
    AiPolicyUpdate,
    AnswerCreate,
    AnswerResponse,
    FeedbackResponse,
    FeedbackUpdate,
    FocusCreate,
    FocusResponse,
    FocusTransition,
    ProjectCreate,
    ProjectResponse,
    SourceResponse,
    TaskFromAnswerCreate,
    TaskResponse,
    WorkspaceResponse,
)
from vikram_api.services.workspace import VikramService

router = APIRouter(prefix="/api/v1")


def get_service(request: Request) -> VikramService:
    service: VikramService = request.app.state.vikram_service
    return service


ServiceDependency = Annotated[VikramService, Depends(get_service)]


@router.get("/projects", response_model=list[ProjectResponse])
def list_projects(service: ServiceDependency) -> list[ProjectResponse]:
    return service.list_projects()


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, service: ServiceDependency) -> ProjectResponse:
    return service.create_project(payload.name)


@router.get("/projects/{project_id}", response_model=WorkspaceResponse)
def get_workspace(project_id: str, service: ServiceDependency) -> WorkspaceResponse:
    return service.get_workspace(project_id)


@router.put("/projects/{project_id}/ai-policy", response_model=AiPolicyResponse)
async def update_ai_policy(
    project_id: str, payload: AiPolicyUpdate, service: ServiceDependency
) -> AiPolicyResponse:
    return await service.set_ai_policy(project_id, payload)


@router.post(
    "/projects/{project_id}/sources",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def import_source(
    project_id: str,
    service: ServiceDependency,
    file: Annotated[UploadFile, File()],
    display_name: Annotated[str | None, Form()] = None,
) -> SourceResponse:
    content = await file.read(service.settings.max_source_bytes + 1)
    return service.import_source(
        project_id, display_name or file.filename or "source", file.content_type, content
    )


@router.post(
    "/projects/{project_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_answer(
    project_id: str,
    payload: AnswerCreate,
    request: Request,
    service: ServiceDependency,
) -> AnswerResponse:
    answer_task = asyncio.create_task(service.answer(project_id, payload.question))
    try:
        while not answer_task.done():
            await asyncio.wait({answer_task}, timeout=0.1)
            if await request.is_disconnected():
                answer_task.cancel()
                raise asyncio.CancelledError
        return await answer_task
    finally:
        if not answer_task.done():
            answer_task.cancel()
        with suppress(asyncio.CancelledError):
            await answer_task


@router.put("/answers/{answer_id}/feedback", response_model=FeedbackResponse)
def update_feedback(
    answer_id: str, payload: FeedbackUpdate, service: ServiceDependency
) -> FeedbackResponse:
    return service.set_feedback(answer_id, payload.status)


@router.post(
    "/answers/{answer_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def task_from_answer(
    answer_id: str, payload: TaskFromAnswerCreate, service: ServiceDependency
) -> TaskResponse:
    return service.task_from_answer(answer_id, payload.title)


@router.post(
    "/tasks/{task_id}/focus-sessions",
    response_model=FocusResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_focus(task_id: str, payload: FocusCreate, service: ServiceDependency) -> FocusResponse:
    return service.start_focus(task_id, payload.duration_minutes)


@router.get("/focus-sessions/{focus_id}", response_model=FocusResponse)
def get_focus(focus_id: str, service: ServiceDependency) -> FocusResponse:
    return service.get_focus(focus_id)


@router.post("/focus-sessions/{focus_id}/transitions", response_model=FocusResponse)
def transition_focus(
    focus_id: str, payload: FocusTransition, service: ServiceDependency
) -> FocusResponse:
    return service.transition_focus(focus_id, payload.transition, payload.expected_revision)
