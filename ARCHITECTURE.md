# Box Office Architecture Documentation

## System Overview

The Box Office ticketing service is built as a microservice following clean architecture principles, SOLID design patterns, and production-ready practices. The system ensures no overbooking through distributed locking and provides idempotent operations for network resilience.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                             │
├─────────────────────────────────────────────────────────────────┤
│  Web Apps │ Mobile Apps │ Postman │ cURL │ Load Balancer       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                          │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI Application │ Middleware │ Rate Limiting │ Auth        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Business Logic Layer                       │
├─────────────────────────────────────────────────────────────────┤
│ EventService │ HoldService │ BookingService │ ExpiryService    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Access Layer                          │
├─────────────────────────────────────────────────────────────────┤
│ EventRepository │ HoldRepository │ BookingRepository           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Storage Layer                              │
├─────────────────────────────────────────────────────────────────┤
│ In-Memory Storage │ Redis Cache │ Distributed Locking          │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. API Layer (FastAPI)

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│  Routes │ Middleware │ Dependencies │ Exception Handlers        │
│         │            │              │                           │
│  • /events          │ • Logging     │ • Service Injection      │ • Business Logic Errors │
│  • /holds           │ • Error Handling │ • Redis Client        │ • Validation Errors     │
│  • /book            │ • Correlation IDs │ • Repository Factory │ • System Errors         │
│  • /metrics         │ • Request Timing │ • Configuration       │ • HTTP Status Codes     │
│  • /health          │ • CORS         │ • Environment Vars      │ • Error Response Format │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Service Layer (Business Logic)

```
┌─────────────────────────────────────────────────────────────────┐
│                        Service Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  EventService                    │  HoldService                 │
│  • Create events                 │  • Create holds              │
│  • Get event details             │  • Validate holds            │
│  • Get event status              │  • Expire holds              │
│  • List events                   │  • Seat availability check   │
│                                  │  • Concurrency control       │
├─────────────────────────────────────────────────────────────────┤
│  BookingService                  │  ExpiryService               │
│  • Create bookings               │  • Background expiry worker  │
│  • Idempotent operations         │  • Periodic hold cleanup     │
│  • Payment token validation      │  • Seat release              │
│  • Hold confirmation             │  • Metrics collection        │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Repository Layer (Data Access)

```
┌─────────────────────────────────────────────────────────────────┐
│                      Repository Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  BaseRepository (Interface)                                     │
│  • create(entity)                                               │
│  • get_by_id(id)                                                │
│  • update(entity)                                               │
│  • delete(id)                                                   │
│  • list_all()                                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│  EventRepository    │  HoldRepository    │  BookingRepository   │
│  • In-memory storage│  • Redis locking   │  • Idempotency check │
│  • Redis caching    │  • Seat reservation│  • Booking tracking  │
│  • Event CRUD       │  • Hold expiration │  • Payment validation│
│  • Status calculation│  • Concurrency     │  • Hold confirmation│
└─────────────────────────────────────────────────────────────────┘
```

### 4. Data Flow Architecture

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Client    │───▶│   FastAPI   │───▶│   Service   │───▶│ Repository  │
│             │    │   Router    │    │   Layer     │    │   Layer     │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
                          │                    │                    │
                          ▼                    ▼                    ▼
                   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
                   │ Middleware  │    │ Validation  │    │ Redis Cache │
                   │ • Logging   │    │ • Business  │    │ • Distributed│
                   │ • Error     │    │   Rules     │    │   Locking   │
                   │ • Metrics   │    │ • Concurrency│   │ • Caching   │
                   └─────────────┘    └─────────────┘    └─────────────┘
```

## Concurrency Control Architecture

### Distributed Locking with Redis

```
┌─────────────────────────────────────────────────────────────────┐
│                    Concurrency Control Flow                     │
├─────────────────────────────────────────────────────────────────┤
│  Client A Request │  Client B Request │  Client C Request       │
│  Hold 30 seats    │  Hold 25 seats    │  Hold 15 seats          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Redis Transaction                          │
├─────────────────────────────────────────────────────────────────┤
│  1. WATCH held_seats:{event_id}                                 │
│  2. GET current_held_seats                                      │
│  3. VALIDATE available_seats >= requested_seats                 │
│  4. MULTI                                                        │
│  5. INCRBY held_seats:{event_id} requested_seats                │
│  6. EXEC                                                         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Result Distribution                      │
├─────────────────────────────────────────────────────────────────┤
│  ✅ Client A: Success (30 seats held)                          │
│  ❌ Client B: Failed (insufficient seats)                      │
│  ✅ Client C: Success (15 seats held)                          │
└─────────────────────────────────────────────────────────────────┘
```

## Hold Expiration Architecture

### Background Worker System

```
┌─────────────────────────────────────────────────────────────────┐
│                    Expiry Worker Architecture                   │
├─────────────────────────────────────────────────────────────────┤
│  Application Startup                                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  ExpiryService.start_expiry_worker()                       │ │
│  │  • Create background task                                   │ │
│  │  • Start periodic checking                                  │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Periodic Check Loop                          │
├─────────────────────────────────────────────────────────────────┤
│  Every 30 seconds:                                             │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  1. Get all holds from repository                          │ │
│  │  2. Check each hold for expiration                         │ │
│  │  3. Expire holds that are past TTL                         │ │
│  │  4. Release seats back to available pool                   │ │
│  │  5. Update hold status to 'expired'                        │ │
│  │  6. Log expiration metrics                                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Idempotency Architecture

### Booking Idempotency Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Idempotency Implementation                   │
├─────────────────────────────────────────────────────────────────┤
│  Client Request (hold_id + payment_token)                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  1. Validate hold exists and is active                     │ │
│  │  2. Validate payment token matches                         │ │
│  │  3. Check if booking already exists for hold_id            │ │
│  │  4. If exists: return existing booking (idempotent)        │ │
│  │  5. If not exists: create new booking                      │ │
│  │  6. Confirm hold status                                    │ │
│  │  7. Update seat counts                                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Monitoring and Observability

### Metrics Collection Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Stack                          │
├─────────────────────────────────────────────────────────────────┤
│  Application Metrics                                            │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  • HTTP request count by endpoint                          │ │
│  │  • Request latency histogram                               │ │
│  │  • Error rate by error type                                │ │
│  │  • Business metrics (events, holds, bookings)              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                │                                │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Prometheus Metrics Endpoint (/metrics)                    │ │
│  │  • Counter: http_requests_total                             │ │
│  │  • Histogram: http_request_duration_seconds                 │ │
│  │  • Gauge: active_holds, total_bookings                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                │                                │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Structured Logging                                         │ │
│  │  • Correlation IDs for request tracing                     │ │
│  │  • JSON structured logs                                     │ │
│  │  • Request/response logging                                 │ │
│  │  • Error context and stack traces                          │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Docker Compose Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Deployment                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Box Office    │    │     Redis       │    │   Load Balancer │ │
│  │   Application   │◀──▶│     Cache       │◀──▶│   (Optional)    │ │
│  │   (Port 8080)   │    │   (Port 6379)   │    │                 │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │       │
│           ▼                       ▼                       ▼       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Application   │    │   Redis Data    │    │   Client Apps   │ │
│  │     Logs        │    │   Persistence   │    │   (Web/Mobile)  │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Kubernetes Deployment

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Architecture                      │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Ingress       │    │   Service       │    │   ConfigMap     │ │
│  │   Controller    │───▶│   (ClusterIP)   │───▶│   & Secrets     │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │       │
│           ▼                       ▼                       ▼       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Box Office    │    │   Redis         │    │   Prometheus    │ │
│  │   Deployment    │◀──▶│   StatefulSet   │◀──▶│   Monitoring    │ │
│  │   (Replicas: 3) │    │   (Replicas: 3) │    │   Stack         │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Security Architecture

### Security Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        Security Architecture                    │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Network       │    │   Application   │    │   Data          │ │
│  │   Security      │    │   Security      │    │   Security      │ │
│  │   • Firewall    │    │   • Input       │    │   • Encryption  │ │
│  │   • DDoS        │    │     Validation  │    │   • Access      │ │
│  │   • Rate        │    │   • Authentication│   │     Control    │ │
│  │     Limiting    │    │   • Authorization│   │   • Audit       │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Performance Architecture

### Caching Strategy

```
┌─────────────────────────────────────────────────────────────────┐
│                        Caching Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Application   │    │   Redis Cache   │    │   In-Memory     │ │
│  │     Layer       │───▶│   (L1 Cache)    │───▶│   Storage       │ │
│  │                 │    │   • Events      │    │   (L2 Cache)    │ │
│  │                 │    │   • Holds       │    │   • Fallback    │ │
│  │                 │    │   • Bookings    │    │   • Persistence │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
│           │                       │                       │       │
│           ▼                       ▼                       ▼       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Cache Hit     │    │   Cache Miss    │    │   Cache Update  │ │
│  │   • Fast        │    │   • Load from   │    │   • Invalidate  │ │
│  │     Response    │    │     Storage     │    │   • Refresh     │ │
│  │   • Reduced     │    │   • Update      │    │   • Consistency │ │
│  │     Latency     │    │     Cache       │    │                 │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Architecture

### Error Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Error Handling Flow                          │
├─────────────────────────────────────────────────────────────────┤
│  Request Processing                                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  1. Input validation                                        │ │
│  │  2. Business logic execution                                │ │
│  │  3. Data access operations                                  │ │
│  │  4. Response generation                                      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                │                                │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Error Types:                                               │ │
│  │  • ValidationError: Invalid input data                      │ │
│  │  • BusinessError: Business rule violations                  │ │
│  │  • SystemError: Infrastructure issues                       │ │
│  │  • NetworkError: Communication failures                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                │                                │
│                                ▼                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │  Error Handling:                                            │ │
│  │  • Log error with context                                   │ │
│  │  • Generate appropriate HTTP status                         │ │
│  │  • Return structured error response                         │ │
│  │  • Include correlation ID for tracing                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Scalability Considerations

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────────┐
│                    Scalability Architecture                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐ │
│  │   Load          │    │   Box Office    │    │   Box Office    │ │
│  │   Balancer      │───▶│   Instance 1    │    │   Instance 2    │ │
│  │   (HAProxy/     │    │   • Stateless   │    │   • Stateless   │ │
│  │    Nginx)       │    │   • Shared      │    │   • Shared      │ │
│  └─────────────────┘    │     Redis       │    │     Redis       │ │
│                         └─────────────────┘    └─────────────────┘ │
│                                  │                       │         │
│                                  ▼                       ▼         │
│                         ┌─────────────────────────────────────────┐ │
│                         │           Redis Cluster                 │ │
│                         │  • Master-Slave replication             │ │
│                         │  • Automatic failover                   │ │
│                         │  • Data persistence                     │ │
│                         └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

This architecture ensures the Box Office service is production-ready, scalable, and maintainable while following industry best practices and SOLID principles.

