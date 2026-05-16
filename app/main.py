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
    reg: Optional[str] = None
    region: Optional[str] = None

@app.get("/")
async def root():
    return {
        "status": "JWT Generator Live (Static Load Balancer) 💀",
        "loaded_regions": list(accounts_db.keys()),
        "endpoints": "/api/token?region=IND"
    }

@app.get("/api/token")
async def get_token(
    reg: Optional[str] = Query(None), 
    region: Optional[str] = Query(None),
    uid: Optional[str] = Query(None), 
    password: Optional[str] = Query(None)
):
    # Strict Parameter Enforcement 🛡️
    target_region = region or reg
    
    if not target_region:
        raise HTTPException(status_code=400, detail="Missing region parameter. You must explicitly specify ?region= (Example: ?region=IND)")
        
    target_region = target_region.upper()
    aliases = {"PAK": "PK", "INDIA": "IND", "BGD": "BD", "BRA": "BR", "VNM": "VN", "SGP": "SG", "THA": "TH"}
    target_region = aliases.get(target_region, target_region)

    # 1. Manual Override Mode
    if uid and password:
        try:
            result = await create_jwt(uid, password, target_region)
            return {"developer": "BITTU__DEV", "uid": uid, **result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # 2. Static DB Mode (Fails if region is incorrect/unsupported)
    if target_region not in accounts_db:
        raise HTTPException(status_code=404, detail=f"Unsupported or incorrect region: {target_region}")

    # Load Balancer
    account_pool = accounts_db[target_region]
    if isinstance(account_pool, list):
        active_account = random.choice(account_pool)
    else:
        active_account = account_pool

    active_uid = active_account.get("uid")
    active_pwd = active_account.get("password")

    if not active_uid or not active_pwd:
        raise HTTPException(status_code=500, detail=f"Malformed account data for {target_region}")

    try:
        result = await create_jwt(active_uid, active_pwd, target_region)
        return {
            "developer": "BITTU__DEV",
            "status": "active",
            "region": target_region,
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
        target_region = payload.region or payload.reg
        
        if not target_region:
            raise HTTPException(status_code=400, detail="Missing region parameter in JSON payload.")
            
        target_region = target_region.upper()
        aliases = {"PAK": "PK", "INDIA": "IND", "BGD": "BD", "BRA": "BR", "VNM": "VN", "SGP": "SG", "THA": "TH"}
        target_region = aliases.get(target_region, target_region)
        
        if payload.uid and payload.password:
            result = await create_jwt(payload.uid, payload.password, target_region)
            return {"developer": "BITTU__DEV", "uid": payload.uid, **result}
        else:
            return await get_token(region=target_region)
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
