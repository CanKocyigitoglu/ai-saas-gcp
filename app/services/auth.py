import os
from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth, credentials


bearer_scheme = HTTPBearer(auto_error=False)


def initialise_firebase_admin() -> None:
    """
    Initialise Firebase Admin SDK once.

    On GCP VM, this uses Application Default Credentials.
    If GOOGLE_APPLICATION_CREDENTIALS exists, it can also use a service account JSON.
    """
    if firebase_admin._apps:
        return

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    options = {"projectId": project_id} if project_id else None

    if credential_path and os.path.exists(credential_path):
        cred = credentials.Certificate(credential_path)
        firebase_admin.initialize_app(cred, options=options)
    else:
        firebase_admin.initialize_app(options=options)


def get_current_user(
    credentials_value: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict[str, Any]:
    """
    Verify Firebase ID token from Authorization: Bearer <token>.
    """
    if credentials_value is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Firebase ID token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials_value.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    initialise_firebase_admin()

    try:
        decoded_token = auth.verify_id_token(credentials_value.credentials)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired Firebase ID token: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return {
        "uid": decoded_token.get("uid"),
        "email": decoded_token.get("email"),
        "email_verified": decoded_token.get("email_verified"),
        "claims": decoded_token,
    }
