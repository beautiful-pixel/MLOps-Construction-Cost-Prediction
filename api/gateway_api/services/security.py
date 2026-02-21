from datetime import datetime, timedelta
import os
from jose import JWTError, jwt
from fastapi import HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from psycopg2 import connect
from psycopg2.extras import RealDictCursor
from core.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# Fake DB for now (can move to real DB later)
fake_users_db = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("admin"),
        "role": "admin",
    },
    "user": {
        "username": "user",
        "hashed_password": pwd_context.hash("user"),
        "role": "user",
    }
}

_db_initialized = False


def _db_configured() -> bool:
    return bool(
        os.getenv("GATEWAY_DATABASE_URL")
        or os.getenv("GATEWAY_DB_HOST")
    )


def _get_db_connection():
    dsn = os.getenv("GATEWAY_DATABASE_URL")
    if dsn:
        conn = connect(dsn, cursor_factory=RealDictCursor)
    else:
        conn = connect(
            host=os.getenv("GATEWAY_DB_HOST", "postgres"),
            port=int(os.getenv("GATEWAY_DB_PORT", "5432")),
            dbname=os.getenv("GATEWAY_DB_NAME", "gateway_api"),
            user=os.getenv("GATEWAY_DB_USER", "gateway"),
            password=os.getenv("GATEWAY_DB_PASSWORD", "gateway"),
            connect_timeout=5,
            cursor_factory=RealDictCursor,
        )
    conn.autocommit = True
    return conn


def _ensure_auth_schema(conn):
    global _db_initialized
    if _db_initialized:
        return

    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role TEXT NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            );
            """
        )
        cur.execute(
            """
            INSERT INTO auth_users (username, hashed_password, role, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (username) DO NOTHING;
            """,
            ("admin", pwd_context.hash("admin"), "admin"),
        )
        cur.execute(
            """
            INSERT INTO auth_users (username, hashed_password, role, is_active)
            VALUES (%s, %s, %s, TRUE)
            ON CONFLICT (username) DO NOTHING;
            """,
            ("user", pwd_context.hash("user"), "user"),
        )
    _db_initialized = True


def _get_user_from_db(username: str):
    with _get_db_connection() as conn:
        _ensure_auth_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT username, hashed_password, role, is_active
                FROM auth_users
                WHERE username = %s
                """,
                (username,),
            )
            return cur.fetchone()


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str):
    if _db_configured():
        try:
            user = _get_user_from_db(username)
        except Exception:
            user = None
    else:
        user = fake_users_db.get(username)

    if not user:
        return None
    if not user.get("is_active", True):
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)):

    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    return {"username": username, "role": role}


def require_user(user=Depends(get_current_user)):
    if user.get("role") not in {"user", "admin"}:
        raise HTTPException(
            status_code=403,
            detail="User privileges required",
        )
    return user


def require_admin(user=Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )
    return user
