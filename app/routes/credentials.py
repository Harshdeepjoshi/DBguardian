from fastapi import APIRouter, HTTPException, Depends
from typing import List
import psycopg2
from ..database.connection import get_db_connection
from ..models.schemas import DatabaseCredentials, DatabaseCredentialsList

router = APIRouter(prefix="/credentials", tags=["credentials"])

@router.post("/", response_model=DatabaseCredentials)
async def create_database_credentials(credentials: DatabaseCredentials):
    """Create new database credentials"""
    try:
        # Test the connection first
        test_connection(credentials)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO database_credentials (name, host, port, database, username, password, version)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, name, host, port, database, username, password, version, created_at
            """, (
                credentials.name, credentials.host, credentials.port,
                credentials.database, credentials.username, credentials.password, credentials.version
            ))

            result = cursor.fetchone()
            conn.commit()

            return DatabaseCredentials(
                id=result[0],
                name=result[1],
                host=result[2],
                port=result[3],
                database=result[4],
                username=result[5],
                password=result[6],
                version=result[7],
                created_at=str(result[8])
            )

    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=f"Database connection failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")

@router.get("/", response_model=DatabaseCredentialsList)
async def list_database_credentials():
    """List all database credentials"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, host, port, database, username, password, version, created_at
                FROM database_credentials
                ORDER BY created_at DESC
            """)

            credentials = []
            for row in cursor.fetchall():
                credentials.append(DatabaseCredentials(
                    id=row[0],
                    name=row[1],
                    host=row[2],
                    port=row[3],
                    database=row[4],
                    username=row[5],
                    password=row[6],
                    version=row[7],
                    created_at=str(row[8])
                ))

            return DatabaseCredentialsList(databases=credentials)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch credentials: {str(e)}")

@router.get("/{credential_id}", response_model=DatabaseCredentials)
async def get_database_credentials(credential_id: int):
    """Get specific database credentials"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, name, host, port, database, username, password, version, created_at
                FROM database_credentials
                WHERE id = %s
            """, (credential_id,))

            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Credentials not found")

            return DatabaseCredentials(
                id=row[0],
                name=row[1],
                host=row[2],
                port=row[3],
                database=row[4],
                username=row[5],
                password=row[6],
                version=row[7],
                created_at=str(row[8])
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch credentials: {str(e)}")

@router.put("/{credential_id}", response_model=DatabaseCredentials)
async def update_database_credentials(credential_id: int, credentials: DatabaseCredentials):
    """Update database credentials"""
    try:
        # Test the connection first
        test_connection(credentials)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE database_credentials
                SET name = %s, host = %s, port = %s, database = %s, username = %s, password = %s, version = %s
                WHERE id = %s
                RETURNING id, name, host, port, database, username, password, version, created_at
            """, (
                credentials.name, credentials.host, credentials.port,
                credentials.database, credentials.username, credentials.password,
                credentials.version, credential_id
            ))

            result = cursor.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Credentials not found")

            conn.commit()

            return DatabaseCredentials(
                id=result[0],
                name=result[1],
                host=result[2],
                port=result[3],
                database=result[4],
                username=result[5],
                password=result[6],
                version=result[7],
                created_at=str(result[8])
            )

    except HTTPException:
        raise
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=f"Database connection failed: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update credentials: {str(e)}")

@router.delete("/{credential_id}")
async def delete_database_credentials(credential_id: int):
    """Delete database credentials"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM database_credentials WHERE id = %s", (credential_id,))

            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Credentials not found")

            conn.commit()

            return {"message": "Credentials deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete credentials: {str(e)}")

def test_connection(credentials: DatabaseCredentials):
    """Test database connection with provided credentials"""
    try:
        conn = psycopg2.connect(
            host=credentials.host,
            port=credentials.port,
            database=credentials.database,
            user=credentials.username,
            password=credentials.password,
            connect_timeout=10
        )
        conn.close()
    except psycopg2.Error as e:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {str(e)}")

@router.post("/{credential_id}/test")
async def test_database_connection(credential_id: int):
    """Test connection for existing credentials"""
    try:
        # Get credentials from database
        credentials = await get_database_credentials(credential_id)

        # Test the connection
        test_connection(credentials)

        return {"message": "Connection successful"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Connection test failed: {str(e)}")
