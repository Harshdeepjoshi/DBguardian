from fastapi import APIRouter, HTTPException, Depends
from ..models.schemas import DatabaseListResponse, TableListResponse
from ..database.connection import get_db_connection
from ..dependencies import verify_api_key, get_prometheus_metrics

router = APIRouter()

@router.get("/databases", response_model=DatabaseListResponse)
async def list_databases(api_key: str = Depends(verify_api_key)):
    """List available databases"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get database size and basic info
            cursor.execute("""
                SELECT
                    current_database() as name,
                    pg_size_pretty(pg_database_size(current_database())) as size,
                    (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count
            """)

            result = cursor.fetchone()
            databases = [{
                "name": result[0],
                "size": result[1],
                "table_count": result[2],
                "status": "connected"
            }]

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/databases', http_status=200).inc()

        return DatabaseListResponse(databases=databases)

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint='/api/databases', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to list databases: {str(e)}")

@router.get("/databases/{database_name}/tables", response_model=TableListResponse)
async def list_database_tables(database_name: str, api_key: str = Depends(verify_api_key)):
    """List tables in a specific database"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    table_name,
                    table_type,
                    (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
                FROM information_schema.tables t
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = []
            for row in cursor.fetchall():
                tables.append({
                    "name": row[0],
                    "type": row[1],
                    "column_count": row[2]
                })

        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/databases/{database_name}/tables', http_status=200).inc()

        return TableListResponse(tables=tables)

    except Exception as e:
        REQUEST_COUNT, _ = get_prometheus_metrics()
        REQUEST_COUNT.labels(method='GET', endpoint=f'/api/databases/{database_name}/tables', http_status=500).inc()
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")
