# Ayush_Kumar_Agrawal's Box Office - Ticketing Service

A production-ready, scalable ticketing service that allows users to hold seats temporarily and then book them. Built with FastAPI, Redis, and following SOLID principles and OOP design patterns.

## 🏗️ Architecture Overview

### System Architecture Diagram

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   Load Balancer │    │   FastAPI App   │
│   (Web/Mobile)  │───▶│   (Optional)    │───▶│   (Port 8080)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │   Redis Cache   │    │   In-Memory     │
│   (Metrics)     │◀───│   (Port 6379)   │◀───│   Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Application Architecture (SOLID Principles)

```
┌─────────────────────────────────────────────────────────────────┐
│                        API Layer (FastAPI)                      │
├─────────────────────────────────────────────────────────────────┤
│  Routes │ Middleware │ Dependencies │ Exception Handlers        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer                              │
├─────────────────────────────────────────────────────────────────┤
│ EventService │ HoldService │ BookingService │ ExpiryService    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                             │
├─────────────────────────────────────────────────────────────────┤
│ EventRepository │ HoldRepository │ BookingRepository           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
├─────────────────────────────────────────────────────────────────┤
│ In-Memory Storage │ Redis Cache │ Distributed Locking          │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Features

### Core Features
- ✅ **Event Management**: Create events with configurable seat capacity
- ✅ **Temporary Holds**: Reserve seats for 2 minutes with automatic expiration
- ✅ **Booking System**: Convert holds to permanent bookings
- ✅ **Concurrency Control**: Redis-based distributed locking prevents overbooking
- ✅ **Idempotency**: Booking operations are idempotent for network resilience

### Advanced Features (Bonus)
- ✅ **Metrics Endpoint**: System-wide metrics and monitoring
- ✅ **Structured Logging**: Correlation IDs and structured JSON logs
- ✅ **Health Checks**: Application health monitoring
- ✅ **Prometheus Integration**: Metrics collection for observability
- ✅ **Auto-expiry Worker**: Background task for hold expiration

## 🛠️ Technology Stack

- **Framework**: FastAPI (Python 3.10+)
- **Storage**: In-Memory + Redis for caching and distributed locking
- **Concurrency**: AsyncIO with Redis transactions
- **Logging**: Structured logging with correlation IDs
- **Monitoring**: Prometheus metrics
- **Containerization**: Docker & Docker Compose
- **Testing**: Pytest with async support

## 📋 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/events` | Create a new event |
| `GET` | `/api/v1/events/{id}` | Get event details |
| `GET` | `/api/v1/events/{id}/status` | Get event seat status |
| `POST` | `/api/v1/holds` | Create temporary seat hold |
| `GET` | `/api/v1/holds/{id}` | Get hold details |
| `POST` | `/api/v1/book` | Confirm booking from hold |

### Bonus Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/metrics` | System metrics |
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/holds/{id}/expire` | Manually expire hold |

## 🏃‍♂️ Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd ticket-booking-service

# Start the services
docker-compose up -d

# The API will be available at http://localhost:8080
# API documentation at http://localhost:8080/docs
```

### Option 2: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (if not using Docker)
redis-server

# Run the application
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

## 📖 Usage Examples

### 1. Create an Event

```bash
curl -X POST "http://localhost:8080/api/v1/events" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Rock Concert 2024",
    "total_seats": 1000
  }'
```

**Response:**
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Rock Concert 2024",
  "total_seats": 1000,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### 2. Hold Seats

```bash
curl -X POST "http://localhost:8080/api/v1/holds" \
  -H "Content-Type: application/json" \
  -d '{
    "event_id": "550e8400-e29b-41d4-a716-446655440000",
    "qty": 5
  }'
```

**Response:**
```json
{
  "hold_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "qty": 5,
  "expires_at": "2024-01-15T10:32:00Z",
  "payment_token": "payment_token_123",
  "status": "active"
}
```

### 3. Book Seats

```bash
curl -X POST "http://localhost:8080/api/v1/book" \
  -H "Content-Type: application/json" \
  -d '{
    "hold_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
    "payment_token": "payment_token_123"
  }'
```

**Response:**
```json
{
  "booking_id": "7ba7b810-9dad-11d1-80b4-00c04fd430c9",
  "hold_id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "qty": 5,
  "created_at": "2024-01-15T10:31:00Z"
}
```

### 4. Check Event Status

```bash
curl "http://localhost:8080/api/v1/events/550e8400-e29b-41d4-a716-446655440000/status"
```

**Response:**
```json
{
  "total": 1000,
  "available": 995,
  "held": 0,
  "booked": 5
}
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_api.py
```

### Test Scenarios Covered

1. **Event Management**: Create, retrieve, and status checking
2. **Hold Management**: Create holds, handle insufficient seats
3. **Booking Flow**: Complete booking process with idempotency
4. **Concurrency**: Multiple simultaneous hold requests
5. **Error Handling**: Invalid requests and business logic errors
6. **Metrics**: System metrics collection

## 🔧 Configuration

Environment variables can be set in `.env` file or as environment variables:

```bash
# Application
APP_NAME="Ayush_Kumar_Agrawal's Box Office"
DEBUG=false

# Server
HOST=0.0.0.0
PORT=8080

# Redis
REDIS_URL=redis://localhost:6379

# Hold Settings
HOLD_TTL_MINUTES=2
MAX_HOLD_QUANTITY=100

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 📊 Monitoring & Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- `http_requests_total`: Total HTTP requests by method, endpoint, and status
- `http_request_duration_seconds`: Request latency histogram

### Logging

Structured JSON logging with correlation IDs:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "info",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Event created successfully",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "logger": "app.services.event_service"
}
```

### Health Checks

```bash
curl http://localhost:8080/api/v1/health
```

### Design Patterns Used

1. **Repository Pattern**: Data access abstraction
2. **Service Layer Pattern**: Business logic encapsulation
3. **Dependency Injection**: Loose coupling between components
4. **Factory Pattern**: Service creation and configuration
5. **Observer Pattern**: Event-driven hold expiration
6. **Strategy Pattern**: Different storage strategies

## 🔒 Concurrency & Consistency

### Distributed Locking

- Redis-based distributed locking prevents race conditions
- Atomic seat reservation using Redis transactions
- No overbooking guaranteed under concurrent requests

### Idempotency

- Booking operations are idempotent using hold_id as key
- Retry-safe for network failures
- Consistent state even with duplicate requests

### Hold Expiration

- Background worker checks for expired holds every 30 seconds
- Automatic seat release when holds expire
- Configurable TTL (default: 2 minutes)

## 🚀 Production Deployment

### Docker Deployment

```bash
# Build and run
docker-compose -f docker-compose.prod.yml up -d

# Scale services
docker-compose up -d --scale boxoffice=3
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: box-office
spec:
  replicas: 3
  selector:
    matchLabels:
      app: box-office
  template:
    metadata:
      labels:
        app: box-office
    spec:
      containers:
      - name: box-office
        image: box-office:latest
        ports:
        - containerPort: 8080
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
```

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis is running
   redis-cli ping
   
   # Check connection URL
   echo $REDIS_URL
   ```

2. **Port Already in Use**
   ```bash
   # Check what's using port 8080
   lsof -i :8080
   
   # Use different port
   PORT=8081 docker-compose up
   ```

3. **Hold Not Expiring**
   ```bash
   # Check expiry worker logs
   docker-compose logs boxoffice | grep expiry
   
   # Manually expire hold
   curl -X POST "http://localhost:8080/api/v1/holds/{hold_id}/expire"
   ```

## 📈 Performance Considerations

### Optimizations

1. **Redis Caching**: Frequently accessed data cached in Redis
2. **Connection Pooling**: Redis connection pooling for efficiency
3. **Async Operations**: Non-blocking I/O throughout the application
4. **Batch Operations**: Efficient bulk operations where possible

### Scalability

1. **Horizontal Scaling**: Stateless design allows multiple instances
2. **Load Balancing**: Multiple app instances behind load balancer
3. **Database Scaling**: Redis cluster for high availability
4. **Caching Strategy**: Multi-level caching for performance