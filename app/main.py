import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.post("/api/slack/command/sparrow")
async def handle_slack_command(request: Request):
    # Extract data from the Slack request
    data = await request.form()
    # You can process the data here, e.g., parse command, check token, etc.
    # For now, we'll just return a simple JSON response
    with open("data.json", "w") as f:
        json.dump(data, f)

    return JSONResponse(content={"message": "Command received", "data": data})
