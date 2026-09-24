from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime, timezone

app = FastAPI(title="Assignment Management System")

assignments = []
submissions = []
next_assignment_id = 1


class AssignmentCreate(BaseModel):
    title: str
    subject: str
    description: str
    deadline: datetime


class SubmissionCreate(BaseModel):
    student_id: str
    content: str


def calculate_status(deadline, submitted_at=None):
    now = datetime.now(timezone.utc)

    if submitted_at:
        return "On Time" if submitted_at <= deadline else "Late"

    return "Missing" if now > deadline else "Pending"


@app.get("/")
def home():
    return {"message": "Assignment Management System API is running"}


@app.post("/assignments")
def create_assignment(data: AssignmentCreate):
    global next_assignment_id

    if data.deadline <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="Deadline must be in the future"
        )

    assignment = {
        "id": next_assignment_id,
        "title": data.title,
        "subject": data.subject,
        "description": data.description,
        "deadline": data.deadline
    }

    assignments.append(assignment)
    next_assignment_id += 1

    return assignment


@app.get("/assignments")
def get_assignments():
    result = []

    for assignment in assignments:
        item = assignment.copy()

        related = [
            s for s in submissions
            if s["assignment_id"] == assignment["id"]
        ]

        item["submissions"] = [
            {
                **s,
                "status": calculate_status(
                    assignment["deadline"],
                    s["submitted_at"]
                )
            }
            for s in related
        ]

        if not related:
            item["status"] = calculate_status(assignment["deadline"])

        result.append(item)

    return result


@app.get("/assignments/{assignment_id}")
def get_assignment(assignment_id: int):
    for assignment in assignments:
        if assignment["id"] == assignment_id:
            return assignment

    raise HTTPException(status_code=404, detail="Assignment not found")


@app.put("/assignments/{assignment_id}")
def update_assignment(assignment_id: int, data: AssignmentCreate):
    for assignment in assignments:
        if assignment["id"] == assignment_id:
            assignment.update(data.model_dump())
            return assignment

    raise HTTPException(status_code=404, detail="Assignment not found")


@app.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int):
    global assignments

    for assignment in assignments:
        if assignment["id"] == assignment_id:
            assignments = [
                a for a in assignments if a["id"] != assignment_id
            ]
            return {"message": "Assignment deleted"}

    raise HTTPException(status_code=404, detail="Assignment not found")


@app.post("/assignments/{assignment_id}/submit")
def submit_assignment(assignment_id: int, data: SubmissionCreate):
    assignment = next(
        (a for a in assignments if a["id"] == assignment_id),
        None
    )

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    duplicate = next(
        (
            s for s in submissions
            if s["assignment_id"] == assignment_id
            and s["student_id"] == data.student_id
        ),
        None
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail="Duplicate submission not allowed"
        )

    submitted_at = datetime.now(timezone.utc)

    submission = {
        "id": len(submissions) + 1,
        "assignment_id": assignment_id,
        "student_id": data.student_id,
        "content": data.content,
        "submitted_at": submitted_at,
        "status": calculate_status(
            assignment["deadline"],
            submitted_at
        )
    }

    submissions.append(submission)

    return submission