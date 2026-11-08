"""Read-only snapshots of actual world job identity and state."""


def roster(world, initial=False):
    """Return sorted actual jobs without mutating world state.

    Args:
        world: Existing freight world instance.
        initial: Include origin, destination and initial release turn.

    Returns:
        A fresh list of bounded job audit records.
    """
    jobs = sorted(world.delivery_jobs.values(), key=lambda job: job.job_id)
    if (
        len(jobs) > 32
        or len({j.freight_id for j in jobs}) != len(jobs)
        or len({j.job_id for j in jobs}) != len(jobs)
    ):
        raise ValueError("unsupported job roster")
    result = []
    for job in jobs:
        row = {"job_id": job.job_id, "freight_id": job.freight_id, "state": job.state}
        if initial:
            if job.state != "pending":
                raise ValueError("initial job must be pending")
            row.update(origin=job.origin, destination=job.destination, release_turn=0)
        result.append(row)
    return result
