# app/main.py

import json
import os
import random
from fastapi import FastAPI, Query, Body, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.core import create_jwt

app = FastAPI(title="FreeFire JWT Static Factory", version="3.0.0")

ACCOUNTS_FILE = "GuestAccounts.json"

# Initialize Static Memory DB
def load_accounts():
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, "r") as f:
            return json.load(f)
    return {}

accounts_db = load_accounts()

class TokenRequest(BaseModel):
    uid: Optional[str] = None
    password: Optional[str] = None
    reg: Optional[str] = "IND"

@app.get("/")
async def root():
    return {
        "status": "JWT Generator Live (Static Load Balancer) 💀",
        "loaded_regions": list(accounts_db.keys()),
        "endpoints": "/api/token?reg=IND"
    }

@app.get("/api/token")
async def get_token(
    reg: str = Query("IND"), 
    uid: Optional[str] = Query(None), 
    password: Optional[str] = Query(None)
):
    reg = reg.upper()
    aliases = {"PAK": "PK", "INDIA": "IND", "BGD": "BD", "BRA": "BR", "VNM": "VN", "SGP": "SG", "THA": "TH"}
    reg = aliases.get(reg, reg)

    # 1. Manual Override Mode (If you pass UID/Pass directly)
    if uid and password:
        try:
            result = await create_jwt(uid, password, reg)
            return {"developer": "BITTU__DEV", "uid": uid, **result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # 2. Static DB Mode
    if reg not in accounts_db:
        raise HTTPException(status_code=404, detail=f"No pre-generated accounts found for region: {reg}")

    # Load Balancer: Handles both single dicts and lists of 10+ accounts
    account_pool = accounts_db[reg]
    if isinstance(account_pool, list):
        active_account = random.choice(account_pool)
    else:
        active_account = account_pool

    active_uid = active_account.get("uid")
    active_pwd = active_account.get("password")

    if not active_uid or not active_pwd:
        raise HTTPException(status_code=500, detail=f"Malformed account data in GuestAccounts.json for {reg}")

    try:
        # Attempt to harvest the JWT
        result = await create_jwt(active_uid, active_pwd, reg)
        return {
            "developer": "BITTU__DEV",
            "status": "active",
            "region": reg,
            "uid": active_uid,
            **result
        }
    except Exception as e:
        err_msg = str(e)
        if "ACCOUNT_BANNED" in err_msg or "error" in err_msg.lower():
            raise HTTPException(status_code=403, detail=f"BANNED_ACCOUNT: {active_uid}. Please replace this account in GuestAccounts.json!")
        else:
            raise HTTPException(status_code=500, detail=err_msg)

@app.post("/api/token")
async def post_token(payload: TokenRequest = Body(...)):
    try:
        reg = payload.reg.upper() if payload.reg else "IND"
        aliases = {"PAK": "PK", "INDIA": "IND", "BGD": "BD", "BRA": "BR"}
        reg = aliases.get(reg, reg)
        
        if payload.uid and payload.password:
            result = await create_jwt(payload.uid, payload.password, reg)
            return {"developer": "BITTU__DEV", "uid": payload.uid, **result}
        else:
            # Route to GET logic if no manual UID provided
            return await get_token(reg=reg)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
