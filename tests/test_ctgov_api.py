"""Tests for the ClinicalTrials.gov API client and tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from clinical_trials_agent.agent.ctgov_api import search_ctgov
from clinical_trials_agent.agent.tools import _search_clinicaltrials_api


def _make_response(nct_ids, total_count, next_page_token=None):
    """Helper to build a mock httpx.Response (sync json(), sync raise_for_status())."""
    studies = [
        {"protocolSection": {"identificationModule": {"nctId": nct}}} for nct in nct_ids
    ]
    data = {"totalCount": total_count, "studies": studies}
    if next_page_token:
        data["nextPageToken"] = next_page_token
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


@pytest.mark.asyncio
async def test_search_ctgov_empty_results():
    """Returns empty when API has no matches."""
    resp = _make_response([], 0)
    mock_client = AsyncMock()
    mock_client.get.return_value = resp

    with patch("clinical_trials_agent.agent.ctgov_api.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_ctgov(condition="nonexistent_condition_xyz")

    assert result["nct_ids"] == []
    assert result["total_count"] == 0
    assert result["was_truncated"] is False


@pytest.mark.asyncio
async def test_search_ctgov_single_page():
    """Returns NCT IDs from a single page of results."""
    nct_ids = ["NCT00000001", "NCT00000002", "NCT00000003"]
    resp = _make_response(nct_ids, 3)
    mock_client = AsyncMock()
    mock_client.get.return_value = resp

    with patch("clinical_trials_agent.agent.ctgov_api.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_ctgov(condition="diabetes")

    assert result["nct_ids"] == nct_ids
    assert result["total_count"] == 3
    assert result["was_truncated"] is False


@pytest.mark.asyncio
async def test_search_ctgov_pagination():
    """Follows pagination tokens across multiple pages."""
    page1 = _make_response(["NCT001"], 3, next_page_token="token2")
    page2 = _make_response(["NCT002"], 3, next_page_token="token3")
    page3 = _make_response(["NCT003"], 3)

    mock_client = AsyncMock()
    mock_client.get.side_effect = [page1, page2, page3]

    with patch("clinical_trials_agent.agent.ctgov_api.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_ctgov(condition="diabetes")

    assert result["nct_ids"] == ["NCT001", "NCT002", "NCT003"]
    assert result["total_count"] == 3
    assert result["was_truncated"] is False


@pytest.mark.asyncio
async def test_search_ctgov_truncation():
    """Caps results at max_results and sets was_truncated."""
    nct_ids = [f"NCT{i:08d}" for i in range(5)]
    resp = _make_response(nct_ids, 500)
    mock_client = AsyncMock()
    mock_client.get.return_value = resp

    with patch("clinical_trials_agent.agent.ctgov_api.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await search_ctgov(condition="cancer", max_results=3)

    assert len(result["nct_ids"]) == 3
    assert result["total_count"] == 500
    assert result["was_truncated"] is True


@pytest.mark.asyncio
async def test_search_ctgov_no_params():
    """Returns empty immediately when no search params provided."""
    result = await search_ctgov()
    assert result == {"nct_ids": [], "total_count": 0, "was_truncated": False}


@pytest.mark.asyncio
async def test_tool_wrapper_with_results():
    """Tool wrapper formats NCT IDs for SQL IN clause."""
    mock_result = {
        "nct_ids": ["NCT001", "NCT002"],
        "total_count": 2,
        "was_truncated": False,
    }
    with patch(
        "clinical_trials_agent.agent.tools.search_ctgov",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        output = await _search_clinicaltrials_api(condition="test")

    assert "NCT001" in output
    assert "NCT002" in output
    assert "WHERE s.nct_id IN" in output


@pytest.mark.asyncio
async def test_tool_wrapper_no_results():
    """Tool wrapper returns no-results message."""
    mock_result = {"nct_ids": [], "total_count": 0, "was_truncated": False}
    with patch(
        "clinical_trials_agent.agent.tools.search_ctgov",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        output = await _search_clinicaltrials_api(condition="nonexistent")

    assert "No results found" in output


@pytest.mark.asyncio
async def test_tool_wrapper_truncated():
    """Tool wrapper includes truncation note."""
    mock_result = {
        "nct_ids": ["NCT001", "NCT002"],
        "total_count": 500,
        "was_truncated": True,
    }
    with patch(
        "clinical_trials_agent.agent.tools.search_ctgov",
        new_callable=AsyncMock,
        return_value=mock_result,
    ):
        output = await _search_clinicaltrials_api(condition="cancer")

    assert "500" in output
    assert "showing 2 of 500" in output
