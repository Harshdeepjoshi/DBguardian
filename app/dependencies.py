import os
from fastapi import Header

# Global metrics to avoid duplication
_request_count = None
_request_latency = None

def get_prometheus_metrics():
    """Get prometheus metrics at runtime to avoid import-time failures"""
    global _request_count, _request_latency
    if _request_count is None:
        try:
            from prometheus_client import Counter, Histogram
            _request_count = Counter('request_count', 'App Request Count', ['method', 'endpoint', 'http_status'])
            _request_latency = Histogram('request_latency_seconds', 'Request latency', ['method', 'endpoint'])
        except ImportError:
            # Return dummy objects if prometheus is not available
            class DummyMetric:
                def labels(self, **kwargs):
                    return self
                def inc(self):
                    pass
                def observe(self, value):
                    pass
            _request_count = DummyMetric()
            _request_latency = DummyMetric()
    return _request_count, _request_latency

def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """Basic API key authentication - replace with proper auth later"""
    expected_key = os.getenv('API_KEY', 'default-key')
    if x_api_key != expected_key:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
