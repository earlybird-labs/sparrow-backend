from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
import requests
import asyncio
import json

from .config import SLACK_APP_ID, SLACK_APP_SECRET, SLACK_REDIRECT_URI

app = FastAPI()


# Route for handling the OAuth redirect and exchanging the code for an access token
@app.get("/slack/oauth_redirect")
async def oauth_redirect(request: Request):
    # Extract the code from the query parameters
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Missing 'code' query parameter.")

    # Exchange the authorization code for an access token
    response = requests.post(
        "https://slack.com/api/oauth.v2.access",
        data={
            "client_id": SLACK_APP_ID,
            "client_secret": SLACK_APP_SECRET,
            "code": code,
            "redirect_uri": SLACK_REDIRECT_URI,
        },
    ).json()

    if response.get("ok"):
        with open("response.json", "w") as f:
            json.dump(response, f)
        # Return a simple HTML response indicating success
        content = f"<html><body><h1>Authentication successful!</h1><p>Your access token has been saved securely.</p></body></html>"
        return HTMLResponse(content=content, status_code=200)
    else:
        # Return an HTML response indicating failure
        content = f"<html><body><h1>Authentication failed.</h1><p>{response.get('error', 'Unknown error')}</p></body></html>"
        return HTMLResponse(content=content, status_code=400)


# Example endpoint for a long-running task
@app.post("/tasks/long_running")
async def long_running_task(data: dict):
    # Simulate a long-running task
    await asyncio.sleep(10)  # Simulates a delay
    return {"status": "completed", "data": data}


# Health check route
@app.get("/health")
async def health_check():
    return JSONResponse(status_code=200, content={"status": "ok"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
