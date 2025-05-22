# backend/app/monitoring/prometheus.py
from prometheus_client import Counter, Gauge, Histogram, Summary

def get_http_requests_total():
    """
    Returns a singleton Counter for total HTTP requests.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_http_requests_total, "_counter"):
        get_http_requests_total._counter = Counter(
            "http_requests_total", 
            "Total HTTP requests",
            ["method", "endpoint", "status_code"]
        )
    return get_http_requests_total._counter

def get_http_request_duration_seconds():
    """
    Returns a singleton Histogram for HTTP request duration.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_http_request_duration_seconds, "_histogram"):
        get_http_request_duration_seconds._histogram = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"]
        )
    return get_http_request_duration_seconds._histogram

def get_http_requests_in_progress():
    """
    Returns a singleton Gauge for in-progress HTTP requests.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_http_requests_in_progress, "_gauge"):
        get_http_requests_in_progress._gauge = Gauge(
            "http_requests_in_progress",
            "Number of HTTP requests in progress"
        )
    return get_http_requests_in_progress._gauge

def get_system_memory_usage():
    """
    Returns a singleton Gauge for system memory usage.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_system_memory_usage, "_gauge"):
        get_system_memory_usage._gauge = Gauge(
            "system_memory_usage",
            "System memory usage in bytes"
        )
    return get_system_memory_usage._gauge

def setup_metrics(app):
    """
    Setup Prometheus metrics middleware for FastAPI application.
    """
    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        get_http_requests_in_progress().inc()
        
        # Record request method and path
        method = request.method
        endpoint = request.url.path
        
        # Time the request processing
        with get_http_request_duration_seconds().labels(
            method=method, 
            endpoint=endpoint
        ).time():
            response = await call_next(request)
        
        # Record request count with status code
        get_http_requests_total().labels(
            method=method,
            endpoint=endpoint,
            status_code=response.status_code
        ).inc()
        
        get_http_requests_in_progress().dec()
        return response
