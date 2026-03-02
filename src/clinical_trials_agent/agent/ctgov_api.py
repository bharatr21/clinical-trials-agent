"""ClinicalTrials.gov API client for fallback searches."""

import logging

import httpx

logger = logging.getLogger(__name__)

CTGOV_API_BASE = "https://clinicaltrials.gov/api/v2/studies"
MAX_NCT_IDS = 200
REQUEST_TIMEOUT = 30.0


async def search_ctgov(
    condition: str = "",
    term: str = "",
    intervention: str = "",
    max_results: int = MAX_NCT_IDS,
) -> dict:
    """Search ClinicalTrials.gov API and return matching NCT IDs.

    Args:
        condition: Condition or disease to search for.
        term: General search term.
        intervention: Intervention/treatment to search for.
        max_results: Maximum number of NCT IDs to return (capped at 200).

    Returns:
        Dict with keys: nct_ids (list[str]), total_count (int), was_truncated (bool).
    """
    max_results = min(max_results, MAX_NCT_IDS)
    nct_ids: list[str] = []
    total_count = 0
    page_token: str | None = None

    params: dict = {
        "format": "json",
        "fields": "NCTId",
        "pageSize": 100,
    }
    if condition:
        params["query.cond"] = condition
    if term:
        params["query.term"] = term
    if intervention:
        params["query.intr"] = intervention

    if not any(params.get(k) for k in ("query.cond", "query.term", "query.intr")):
        return {"nct_ids": [], "total_count": 0, "was_truncated": False}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        while len(nct_ids) < max_results:
            request_params = {**params}
            if page_token:
                request_params["pageToken"] = page_token

            logger.info(
                "ClinicalTrials.gov API request: params=%s",
                list(request_params.keys()),
            )

            response = await client.get(CTGOV_API_BASE, params=request_params)
            response.raise_for_status()
            data = response.json()

            if total_count == 0:
                total_count = data.get("totalCount", 0)

            studies = data.get("studies", [])
            if not studies:
                break

            for study in studies:
                nct_id = (
                    study.get("protocolSection", {})
                    .get("identificationModule", {})
                    .get("nctId")
                )
                if nct_id:
                    nct_ids.append(nct_id)
                    if len(nct_ids) >= max_results:
                        break

            page_token = data.get("nextPageToken")
            if not page_token:
                break

    was_truncated = total_count > len(nct_ids)
    logger.info(
        f"ClinicalTrials.gov API: {len(nct_ids)} NCT IDs fetched, "
        f"{total_count} total, truncated={was_truncated}"
    )
    return {
        "nct_ids": nct_ids,
        "total_count": total_count,
        "was_truncated": was_truncated,
    }
