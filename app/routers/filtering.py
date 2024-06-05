from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from app.database.db import DatabaseConnector
from app.models.action_result import ActionResult
from datetime import datetime, timedelta
from app.models.call_filtering import CallFilter


filter_router = APIRouter()
db = DatabaseConnector("calls")
analytics_db = DatabaseConnector("analytics")


@filter_router.post("/filter-calls", response_model=ActionResult)
async def read_items(call_filtering: CallFilter):
    action_result = ActionResult(status=True)
    filter_query_analytics = {}
    filter_query_calls = {}
    # Define the parameters as a list
    params_analytics = [call_filtering.keywords, call_filtering.sentiment_category, call_filtering.topics]
    params_calls = [call_filtering.start_date, call_filtering.end_date, call_filtering.duration]
    # Loop through the parameters and add non-None ones to the filter_query dictionary
    for param_name, param_value in zip(["keywords", "sentiment_category", "topics"], params_analytics):
        if param_value not in ("", []):
            if param_name == "sentiment_category":
                filter_query_analytics[param_name] = param_value
            else:
                filter_query_analytics[param_name] = param_value[0]
    for param_name, param_value in zip(["start_date", "end_date", "call_duration"], params_calls):
        if param_value not in ("", []):
            if param_name in ["start_date", "end_date"]:
                if "call_date" not in filter_query_calls:
                    filter_query_calls["call_date"] = {}
                if param_name == "start_date" and param_value != "":
                    filter_query_calls["call_date"]["$gte"] = param_value
                elif param_name == "end_date" and param_value != "":
                    filter_query_calls["call_date"]["$lte"] = param_value

            # if param_name in ["start_date", "end_date"]:
            #     if param_name == "start_date" and param_value != "":
            #         if "call_date" not in filter_query_calls:
            #             filter_query_calls["call_date"] = {}
            #         filter_query_calls["call_date"]["$gte"] = param_value
            #     elif param_name == "end_date" and param_value != "":
            #         if "call_date" not in filter_query_calls:
            #             filter_query_calls["call_date"] = {}
            #         filter_query_calls["call_date"]["$lte"] = param_value
            elif param_name == "call_duration":
                if param_value != 0:

                    min_duration = max(param_value - 60, 0)
                    max_duration = min(param_value + 60, 3600)
                    filter_query_calls["call_duration"] = {"$gte": min_duration, "$lte": max_duration}
            # else:
            #     filter_query_calls[param_name] = param_value

    # Return the filter_query dictionary
    result_analytics = await analytics_db.find_entities(filter_query_analytics)
    result_calls = await db.find_entities(filter_query_calls)

    # Check if params_analytics is empty
    # if not params_analytics:
    #     # result_calls = common_matches_list
    #    common_matches_list = result_calls
    # # Check if params_calls is empty
    # elif not params_calls:
    #     common_matches_list = result_analytics
    # else:
    merged_list = []
    # Handle empty results
    # if result_analytics.data:
    #     matching_analytics_ids = [analytics_record.get("call_id") for analytics_record in result_analytics.data]
    # if result_calls.data:
    #     matching_calls_ids = [call_record.get("_id").get("$oid") for call_record in result_calls.data]
    # if not result_analytics.data or not result_calls.data:
    #     if result_analytics.data:
    #         matching_analytics_ids = [analytics_record.get("call_id") for analytics_record in result_analytics.data]
    #         all_calls = await db.get_all_entities()
    #         matching_calls_ids = [call_record.get("_id").get("$oid") for call_record in all_calls.data]
    #     if result_calls.data:
    #         matching_calls_ids = [call_record.get("_id").get("$oid") for call_record in result_calls.data]
    #         all_analytics_calls = await db.get_all_entities()
    # matching_analytics_ids = [analytics_record.get("call_id") for analytics_record in all_analytics_calls.data]

    # Ensure result data is iterable
    # if not result_calls or not isinstance(result_calls.data, list):
    #     raise HTTPException(status_code=500, detail="Unexpected result format for calls data")
    # if not result_analytics or not isinstance(result_analytics.data, list):
    #     raise HTTPException(status_code=500, detail="Unexpected result format for analytics data")

    # Extract IDs and find common matches
    matching_calls_ids = [call_record["_id"]["$oid"] for call_record in result_calls.data if
                          "_id" in call_record and "$oid" in call_record["_id"]]
    matching_analytics_ids = [analytics_record["call_id"] for analytics_record in result_analytics.data if
                              "call_id" in analytics_record]

    common_matches = set(matching_analytics_ids) | set(matching_calls_ids)
    common_matches_list = list(common_matches)
    for common_id in common_matches_list:
        # Find the call record corresponding to the current ID in result_calls
        call_record = next((record for record in result_calls.data if record.get("_id").get("$oid") == common_id), None)
        # Find the analytics record corresponding to the current ID in result_analytics
        analytics_record = next(
            (record for record in result_analytics.data if record.get("call_id") == common_id),
            None)
        # Check if both call_record and analytics_record are not None
        if call_record and analytics_record:
            # Merge call_record and analytics_record based on the common ID
            merged_record = {**call_record, **analytics_record}
            merged_list.append(merged_record)
# Return the merged list
    return ActionResult(data=merged_list)