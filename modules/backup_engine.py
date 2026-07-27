import os
import json
import pandas as pd
from datetime import datetime
from modules.api_safeguards import safe_api_request

def export_notion_database_snapshot(database_id: str, notion_token: str, output_dir: str = "backups"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    headers = {
        "Authorization": f"Bearer {notion_token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }

    results = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        res = safe_api_request(
            method="POST",
            url=url,
            headers=headers,
            json_data=payload,
            service_type="notion"
        )
        data = res.json()
        results.extend(data.get("results", []))
        has_more = data.get("has_more", False)
        next_cursor = data.get("next_cursor", None)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = os.path.join(output_dir, f"notion_db_{timestamp}.json")
    csv_path = os.path.join(output_dir, f"notion_db_{timestamp}.csv")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    rows = []
    for item in results:
        row = {"id": item.get("id"), "created_time": item.get("created_time")}
        props = item.get("properties", {})
        for prop_name, prop_data in props.items():
            p_type = prop_data.get("type")
            if p_type == "title" and prop_data.get("title"):
                row[prop_name] = "".join([t.get("plain_text", "") for t in prop_data["title"]])
            elif p_type == "rich_text" and prop_data.get("rich_text"):
                row[prop_name] = "".join([t.get("plain_text", "") for t in prop_data["rich_text"]])
            elif p_type == "number":
                row[prop_name] = prop_data.get("number")
            elif p_type == "select" and prop_data.get("select"):
                row[prop_name] = prop_data["select"].get("name")
            elif p_type == "url":
                row[prop_name] = prop_data.get("url")
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(csv_path, index=False)

    return {
        "status": "success",
        "record_count": len(results),
        "json_path": json_path,
        "csv_path": csv_path,
        "raw_json": json.dumps(results, indent=2),
        "raw_csv": df.to_csv(index=False)
    }
