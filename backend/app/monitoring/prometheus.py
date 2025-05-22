# backend/app/monitoring/prometheus.py
from prometheus_client import Counter, Gauge, Histogram, Summary

# --- Fix: Provide the expected function names and label consistency ---

# Counter for total HTTP requests
def get_requests_total():
    """
    Returns a singleton Counter for total HTTP requests.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_requests_total, "_counter"):
        get_requests_total._counter = Counter(
            "http_requests_total", 
            "Total HTTP requests",
            ["method", "endpoint", "status"]  # Use 'status' to match main.py
        )
    return get_requests_total._counter

# Histogram for HTTP request duration
def get_requests_latency():
    """
    Returns a singleton Histogram for HTTP request duration.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_requests_latency, "_histogram"):
        get_requests_latency._histogram = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"]
        )
    return get_requests_latency._histogram

# Gauge for in-progress HTTP requests
def get_requests_in_progress():
    """
    Returns a singleton Gauge for in-progress HTTP requests.
    Ensures the metric is only registered once per process.
    """
    if not hasattr(get_requests_in_progress, "_gauge"):
        get_requests_in_progress._gauge = Gauge(
            "http_requests_in_progress",
            "Number of HTTP requests in progress"
        )
    return get_requests_in_progress._gauge

# (Optional) Keep your system memory usage metric if needed
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

# (Optional) Update setup_metrics to use the new function names if you use it elsewhere
def setup_metrics(app=None):
    """
    Setup Prometheus metrics middleware for FastAPI application.
    """
    if app is None:
        return

    @app.middleware("http")
    async def metrics_middleware(request, call_next):
        get_requests_in_progress().inc()
        method = request.method
        endpoint = request.url.path
        start_time = time.time()
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            duration = time.time() - start_time
            get_requests_total().labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            get_requests_latency().labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)
            get_requests_in_progress().dec()
