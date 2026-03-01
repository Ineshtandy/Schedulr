"""Encrypted OAuth refresh token persistence."""
from typing import Optional

from app.crypto.tokens import decrypt_token, encrypt_token
from app.db.snowflake import exec_query, fetch_one


def upsert_refresh_token(user_id: str, refresh_token: str) -> None:
    refresh_token_enc = encrypt_token(refresh_token)
    exec_query(
        """
        MERGE INTO oauth_tokens AS target
        USING (SELECT %s AS user_id, %s AS refresh_token_enc) AS src
        ON target.user_id = src.user_id
        WHEN MATCHED THEN
          UPDATE SET refresh_token_enc = src.refresh_token_enc, updated_at = CURRENT_TIMESTAMP()
        WHEN NOT MATCHED THEN
          INSERT (user_id, refresh_token_enc, updated_at)
          VALUES (src.user_id, src.refresh_token_enc, CURRENT_TIMESTAMP())
        """,
        (user_id, refresh_token_enc),
    )


def get_refresh_token(user_id: str) -> Optional[str]:
    row = fetch_one(
        "SELECT refresh_token_enc FROM oauth_tokens WHERE user_id = %s",
        (user_id,),
    )
    if not row or not row.get("refresh_token_enc"):
        return None
    return decrypt_token(row["refresh_token_enc"])
