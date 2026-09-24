from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI(title="Assignment Management System")


# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# In-memory storage
# =========================

assignments = []
submissions = []
next_assignment_id = 1
next_submission_id = 1


# =========================
# Models
# =========================

class AssignmentCreate(BaseModel):
    title: str
    subject: str
    description: str
    deadline: datetime


class SubmissionCreate(BaseModel):
    student_id: str
    content: str


# =========================
# Utility
# =========================

def normalize_datetime(value):
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def calculate_status(deadline, submitted_at=None):
    deadline = normalize_datetime(deadline)
    now = datetime.now(timezone.utc)

    # Student has submitted
    if submitted_at is not None:
        submitted_at = normalize_datetime(submitted_at)

        if submitted_at <= deadline:
            return "On Time"
        else:
            return "Late"

    # Student has not submitted
    if now > deadline:
        return "Missing"

    return "Pending"


# =========================
# Root
# =========================

@app.get("/")
def home():
    return {
        "message": "Assignment Management System API is running"
    }


# =========================
# Assignment CRUD
# =========================

@app.post("/assignments")
def create_assignment(data: AssignmentCreate):
    global next_assignment_id

    if not data.title.strip():
        raise HTTPException(
            status_code=400,
            detail="Title is required"
        )

    if not data.subject.strip():
        raise HTTPException(
            status_code=400,
            detail="Subject is required"
        )

    deadline = normalize_datetime(data.deadline)

    # Deadline must be in future
    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Deadline must be in the future"
        )

    assignment = {
        "id": next_assignment_id,
        "title": data.title.strip(),
        "subject": data.subject.strip(),
        "description": data.description.strip(),
        "deadline": deadline
    }

    assignments.append(assignment)
    next_assignment_id += 1

    return assignment


@app.get("/assignments")
def get_assignments():
    result = []

    for assignment in assignments:

        assignment_copy = assignment.copy()

        related_submissions = [
            submission
            for submission in submissions
            if submission["assignment_id"] == assignment["id"]
        ]

        assignment_copy["submissions"] = []

        for submission in related_submissions:
            submission_copy = submission.copy()

            submission_copy["status"] = calculate_status(
                assignment["deadline"],
                submission["submitted_at"]
            )

            assignment_copy["submissions"].append(
                submission_copy
            )

        # If nobody submitted
        if not related_submissions:
            assignment_copy["status"] = calculate_status(
                assignment["deadline"]
            )

        result.append(assignment_copy)

    return result


@app.get("/assignments/{assignment_id}")
def get_assignment(assignment_id: int):

    for assignment in assignments:
        if assignment["id"] == assignment_id:
            return assignment

    raise HTTPException(
        status_code=404,
        detail="Assignment not found"
    )


@app.put("/assignments/{assignment_id}")
def update_assignment(
    assignment_id: int,
    data: AssignmentCreate
):

    if not data.title.strip():
        raise HTTPException(
            status_code=400,
            detail="Title is required"
        )

    if not data.subject.strip():
        raise HTTPException(
            status_code=400,
            detail="Subject is required"
        )

    deadline = normalize_datetime(data.deadline)

    if deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Deadline must be in the future"
        )

    for assignment in assignments:

        if assignment["id"] == assignment_id:

            assignment["title"] = data.title.strip()
            assignment["subject"] = data.subject.strip()
            assignment["description"] = data.description.strip()
            assignment["deadline"] = deadline

            return assignment

    raise HTTPException(
        status_code=404,
        detail="Assignment not found"
    )


@app.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int):

    global assignments
    global submissions

    exists = any(
        assignment["id"] == assignment_id
        for assignment in assignments
    )

    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    assignments = [
        assignment
        for assignment in assignments
        if assignment["id"] != assignment_id
    ]

    submissions = [
        submission
        for submission in submissions
        if submission["assignment_id"] != assignment_id
    ]

    return {
        "message": "Assignment deleted successfully"
    }


# =========================
# Student Submission
# =========================

@app.post("/assignments/{assignment_id}/submit")
def submit_assignment(
    assignment_id: int,
    data: SubmissionCreate
):

    global next_submission_id

    assignment = next(
        (
            assignment
            for assignment in assignments
            if assignment["id"] == assignment_id
        ),
        None
    )

    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    if not data.student_id.strip():
        raise HTTPException(
            status_code=400,
            detail="Student ID is required"
        )

    if not data.content.strip():
        raise HTTPException(
            status_code=400,
            detail="Submission content is required"
        )

    # Duplicate submission check
    duplicate = next(
        (
            submission
            for submission in submissions
            if submission["assignment_id"] == assignment_id
            and submission["student_id"] == data.student_id.strip()
        ),
        None
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Duplicate submission not allowed"
        )

    # SERVER timestamp
    submitted_at = datetime.now(timezone.utc)

    status = calculate_status(
        assignment["deadline"],
        submitted_at
    )

    submission = {
        "id": next_submission_id,
        "assignment_id": assignment_id,
        "student_id": data.student_id.strip(),
        "content": data.content.strip(),
        "submitted_at": submitted_at,
        "status": status
    }

    submissions.append(submission)
    next_submission_id += 1

    return submission


@app.get("/assignments/{assignment_id}/submissions")
def get_submissions(assignment_id: int):

    exists = any(
        assignment["id"] == assignment_id
        for assignment in assignments
    )

    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Assignment not found"
        )

    return [
        submission
        for submission in submissions
        if submission["assignment_id"] == assignment_id
    ]