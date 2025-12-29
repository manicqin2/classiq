# Quantum Circuits API: High-Level Architecture

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   Docker Compose Network                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │ API Server   │                                               │
│  │ (FastAPI)    │                                               │
│  └──────┬───────┘                                               │
│         │                                                       │
│         └──────────────┬──────────────────────────────────┐    │
│                        │                                  │    │
│        ┌───────────────▼──────────────┐   ┌──────────────▼──┐ │
│        │   RabbitMQ (Message Queue)   │   │  PostgreSQL     │ │
│        │   - Exchange: quantum_task   │   │  (Task State)   │ │
│        │   - Queue: task_queue        │   └─────────────────┘ │
│        └───────────────┬──────────────┘                        │
│                        │                                       │
│        ┌───────────────┼───────────────┐                       │
│        │               │               │                       │
│    ┌───▼──┐        ┌───▼──┐       ┌───▼──┐                   │
│    │Worker│        │Worker│       │Worker│                   │
│    │  #1  │        │  #2  │       │  #3  │                   │
│    └──────┘        └──────┘       └──────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Server** | FastAPI + Uvicorn | REST endpoints for task submission/status |
| **Message Queue** | RabbitMQ (AMQP) | Durable, reliable task queue with guarantees |
| **Workers** | Python + Pika | Consume messages, execute Qiskit circuits |
| **Database** | PostgreSQL | Task state persistence (source of truth) |
| **Orchestration** | Docker Compose | Container coordination |

---

## Why RabbitMQ?

RabbitMQ provides production-grade guarantees that Redis lacks:

| Feature | Redis | RabbitMQ |
|---------|-------|----------|
| **Message persistence** | Optional | Built-in (durable queues) |
| **Acknowledgments** | Manual | Automatic (ACK/NACK) |
| **Redelivery** | Manual retry logic | Automatic on worker failure |
| **Message routing** | Simple FIFO | Complex routing (exchanges, routing keys) |
| **Dead letter handling** | Not built-in | Built-in (DLX) |
| **Flow control** | Basic | Advanced (QoS prefetch) |
| **Task guarantees** | At-most-once | At-least-once |
| **Learning curve** | Shallow | Steeper (AMQP concepts) |

**For this project:** RabbitMQ ensures no tasks are lost even if workers crash mid-processing.

---

## Complete docker-compose.yml

```yaml
version: '3.8'

services:
  # ============================================
  # PostgreSQL: Task state persistence
  # ============================================
  postgres:
    image: postgres:15
    container_name: quantum-postgres
    environment:
      POSTGRES_DB: quantum_db
      POSTGRES_USER: quantum_user
      POSTGRES_PASSWORD: quantum_pass
    volumes:
      - ./migrations/schema.sql:/docker-entrypoint-initdb.d/schema.sql
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U quantum_user"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - quantum-network

  # ============================================
  # RabbitMQ: Message queue (AMQP broker)
  # ============================================
  rabbitmq:
    image: rabbitmq:3.12-management-alpine
    container_name: quantum-rabbitmq
    environment:
      RABBITMQ_DEFAULT_USER: quantum_user
      RABBITMQ_DEFAULT_PASS: quantum_pass
    ports:
      - "5672:5672"      # AMQP port (workers connect here)
      - "15672:15672"    # Management UI (http://localhost:15672)
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - quantum-network

  # ============================================
  # FastAPI Server: REST API
  # ============================================
  api:
    build: ./api
    container_name: quantum-api
    ports:
      - "5000:8000"
    environment:
      DATABASE_URL: postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
      RABBITMQ_URL: amqp://quantum_user:quantum_pass@rabbitmq:5672/
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    command: uvicorn app:app --host 0.0.0.0 --port 8000 --reload
    networks:
      - quantum-network
    volumes:
      - ./api:/app

  # ============================================
  # Worker #1: Process tasks from queue
  # ============================================
  worker-1:
    build: ./worker
    container_name: quantum-worker-1
    environment:
      DATABASE_URL: postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
      RABBITMQ_URL: amqp://quantum_user:quantum_pass@rabbitmq:5672/
      WORKER_ID: worker-1
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    command: python worker.py
    networks:
      - quantum-network
    volumes:
      - ./worker:/app

  # ============================================
  # Worker #2: Process tasks from queue
  # ============================================
  worker-2:
    build: ./worker
    container_name: quantum-worker-2
    environment:
      DATABASE_URL: postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
      RABBITMQ_URL: amqp://quantum_user:quantum_pass@rabbitmq:5672/
      WORKER_ID: worker-2
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    command: python worker.py
    networks:
      - quantum-network
    volumes:
      - ./worker:/app

  # ============================================
  # Worker #3: Process tasks from queue
  # ============================================
  worker-3:
    build: ./worker
    container_name: quantum-worker-3
    environment:
      DATABASE_URL: postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db
      RABBITMQ_URL: amqp://quantum_user:quantum_pass@rabbitmq:5672/
      WORKER_ID: worker-3
    depends_on:
      postgres:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    command: python worker.py
    networks:
      - quantum-network
    volumes:
      - ./worker:/app

networks:
  quantum-network:
    driver: bridge

volumes:
  postgres_data:
```

---

## File Structure

```
quantum-circuits-api/
├── docker-compose.yml                    # Main orchestration
├── README.md                             # Setup instructions
├── ARCHITECTURE.md                       # This file
├── verify.sh                             # Verification script
│
├── api/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app.py                           # FastAPI endpoints
│   ├── database.py                      # PostgreSQL connection
│   ├── rabbitmq_client.py                # RabbitMQ publisher
│   ├── models.py                        # Pydantic models
│   └── __init__.py
│
├── worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── worker.py                        # RabbitMQ consumer + Qiskit
│   ├── rabbitmq_setup.py                # Queue/exchange setup
│   └── __init__.py
│
├── migrations/
│   └── schema.sql                       # Database initialization
│
└── tests/
    ├── __init__.py
    └── test_integration.py              # Integration tests
```

---

## Component Details

### 1. PostgreSQL Container

**Purpose:** Durable task state storage

**Initialization:**
- Automatically runs `schema.sql` on first startup
- Creates `tasks` table with status tracking
- Persists across container restarts (named volume)

**Health Check:**
- `pg_isready` verifies database is accepting connections
- API and workers wait for this before starting

**Table Schema:**
```sql
CREATE TABLE tasks (
  id VARCHAR(36) PRIMARY KEY,
  circuit_qasm3 TEXT NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  result JSONB,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP,
  CONSTRAINT status_check CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);
```

### 2. RabbitMQ Container

**Purpose:** Durable message queue for task distribution

**Key Concepts:**

- **Exchange**: `quantum_task` (direct exchange)
  - Routes messages to queues based on routing keys
  
- **Queue**: `task_queue` (durable)
  - Persists messages to disk
  - Survives broker restarts
  - ACK-based delivery (workers must confirm receipt)

- **Binding**: Routes messages from exchange to queue
  - Routing key: `tasks`

**Initialization:**
- RabbitMQ automatically creates exchange/queue if they don't exist
- Or explicitly set up via API in `rabbitmq_setup.py`

**Management UI:**
- Access at `http://localhost:15672`
- Username: `quantum_user`
- Password: `quantum_pass`
- View queue depth, message rates, connections

**Health Check:**
- `rabbitmq-diagnostics ping` verifies broker is running
- Workers and API wait for this before starting

### 3. FastAPI Container (API Server)

**Purpose:** REST API for task submission and status retrieval

**Endpoints:**

```
POST /tasks
  Input:  {"qc": "<QASM3 circuit string>"}
  Output: {"task_id": "uuid", "message": "Task submitted successfully."}
  
GET /tasks/{id}
  Output (pending): {"status": "pending", "message": "Task is still in progress."}
  Output (completed): {"status": "completed", "result": {"0": 512, "1": 512}}
  Output (error): {"status": "error", "message": "Task not found."}

GET /health
  Output: {"status": "healthy"}
```

**Flow for POST /tasks:**

```
1. Validate QASM3 input (Pydantic validation)
2. Generate UUID task_id
3. Insert into PostgreSQL with status='pending'
4. Publish message to RabbitMQ:
   - Exchange: quantum_task
   - Routing key: tasks
   - Body: {"task_id": "...", "circuit": "..."}
5. Return HTTP 200 with task_id
```

**Implementation:**
```python
# Pydantic model for validation
class SubmitTaskRequest(BaseModel):
    qc: str  # QASM3 circuit

# In app.py
@app.post("/tasks")
async def submit_task(request: SubmitTaskRequest):
    task_id = str(uuid.uuid4())
    
    # Insert to PostgreSQL
    await db.execute(
        "INSERT INTO tasks (id, circuit_qasm3, status) VALUES ($1, $2, $3)",
        task_id, request.qc, "pending"
    )
    
    # Publish to RabbitMQ
    channel.basic_publish(
        exchange='quantum_task',
        routing_key='tasks',
        body=json.dumps({"task_id": task_id, "circuit": request.qc}),
        properties=pika.BasicProperties(
            delivery_mode=2  # Make message persistent
        )
    )
    
    return {"task_id": task_id, "message": "Task submitted successfully."}
```

**Dependencies:**
- PostgreSQL (must be healthy)
- RabbitMQ (must be healthy)

### 4. Worker Containers (3 instances)

**Purpose:** Consume messages from RabbitMQ, execute Qiskit, store results

**Each worker runs independently:**

1. Connect to RabbitMQ
2. Declare queue and exchange (idempotent)
3. Start consuming messages from `task_queue`
4. For each message:
   - Extract task_id and circuit
   - Fetch circuit from PostgreSQL (optional, included in message)
   - Deserialize QASM3 string
   - Execute with Qiskit AerSimulator (1024 shots)
   - Update PostgreSQL: status='completed', result=<counts>
   - Acknowledge message to RabbitMQ
5. If worker crashes before ACK:
   - RabbitMQ redelivers message to another worker
   - No task is lost

**Implementation:**
```python
import pika
import asyncpg
import json
from qiskit import qasm3
from qiskit.providers.aer import AerSimulator

def setup_rabbitmq():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='rabbitmq', 
                                   credentials=pika.PlainCredentials('quantum_user', 'quantum_pass'))
    )
    channel = connection.channel()
    
    # Declare exchange and queue (idempotent)
    channel.exchange_declare(exchange='quantum_task', 
                            exchange_type='direct', 
                            durable=True)
    channel.queue_declare(queue='task_queue', durable=True)
    channel.queue_bind(exchange='quantum_task', 
                      queue='task_queue', 
                      routing_key='tasks')
    
    return connection, channel

async def process_message(task_id, circuit_qasm3, db_pool):
    """Execute quantum circuit and store results"""
    try:
        # Deserialize QASM3
        circuit = qasm3.loads(circuit_qasm3)
        
        # Execute
        simulator = AerSimulator()
        job = simulator.run(circuit, shots=1024)
        result = job.result()
        counts = result.get_counts()
        
        # Update PostgreSQL
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET status=$1, result=$2, completed_at=$3 WHERE id=$4",
                'completed', json.dumps(counts), datetime.now(), task_id
            )
        
        return True
    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}")
        # Update status to failed
        async with db_pool.acquire() as conn:
            await conn.execute(
                "UPDATE tasks SET status=$1 WHERE id=$2",
                'failed', task_id
            )
        return False

def callback(ch, method, properties, body):
    """RabbitMQ message callback"""
    message = json.loads(body)
    task_id = message['task_id']
    circuit = message['circuit']
    
    logger.info(f"Processing task {task_id}")
    
    # Process
    success = asyncio.run(process_message(task_id, circuit, db_pool))
    
    if success:
        # Acknowledge successful processing
        ch.basic_ack(delivery_tag=method.delivery_tag)
    else:
        # NACK - RabbitMQ will redeliver to another worker
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

async def main():
    # Connect to PostgreSQL
    global db_pool
    db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))
    
    # Connect to RabbitMQ
    connection, channel = setup_rabbitmq()
    
    # Set QoS (process 1 task at a time per worker)
    channel.basic_qos(prefetch_count=1)
    
    # Register callback
    channel.basic_consume(queue='task_queue', on_message_callback=callback)
    
    logger.info(f"Worker started: {os.getenv('WORKER_ID')}")
    channel.start_consuming()

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Data Flow

### Task Submission Flow

```
Client
  │
  └─→ POST /tasks {"qc": "OPENQASM 3; ..."}
      │
      ├─→ [API] Validate QASM3 with Pydantic
      │
      ├─→ [API] Generate UUID task_id
      │
      ├─→ [PostgreSQL] INSERT task
      │   INSERT INTO tasks (id, circuit_qasm3, status)
      │   VALUES ('550e8400-...', 'OPENQASM 3; ...', 'pending')
      │
      ├─→ [RabbitMQ] Publish message
      │   exchange: quantum_task
      │   routing_key: tasks
      │   body: {"task_id": "550e8400-...", "circuit": "OPENQASM 3; ..."}
      │   persistent: yes (durable)
      │
      └─→ HTTP 200 Response
          {"task_id": "550e8400-...", "message": "Task submitted successfully."}
```

### Task Processing Flow

```
[RabbitMQ] task_queue contains message
  │
  ├─→ [Worker-1/2/3] Fetch message from queue
  │   (RabbitMQ holds message, waiting for ACK)
  │
  ├─→ [Worker] Extract task_id and circuit from message
  │
  ├─→ [Qiskit] Deserialize QASM3
  │   circuit = qasm3.loads(circuit_string)
  │
  ├─→ [Qiskit] Execute on AerSimulator
  │   job = simulator.run(circuit, shots=1024)
  │   result = {"0": 512, "1": 512}
  │
  ├─→ [PostgreSQL] Update task with results
  │   UPDATE tasks SET status='completed', result='{"0": 512, "1": 512}', 
  │   completed_at=now WHERE id='550e8400-...'
  │
  └─→ [RabbitMQ] Send ACK
      (Message removed from queue)
      basic_ack(delivery_tag=...)
```

### Status Retrieval Flow

```
Client
  │
  └─→ GET /tasks/550e8400-...
      │
      ├─→ [PostgreSQL] SELECT status, result FROM tasks WHERE id=?
      │
      ├─→ If status='completed':
      │   {"status": "completed", "result": {"0": 512, "1": 512}}
      │
      └─→ Else:
          {"status": "pending", "message": "Task is still in progress."}
```

---

## Environment Variables

All containers use these environment variables:

```bash
# Database connection
DATABASE_URL=postgresql://quantum_user:quantum_pass@postgres:5432/quantum_db

# RabbitMQ connection
RABBITMQ_URL=amqp://quantum_user:quantum_pass@rabbitmq:5672/

# Worker identification (workers only)
WORKER_ID=worker-1  # (different for each worker)
```

---

## Running the System

### Start Everything

```bash
# Build images and start all containers
docker-compose up -d

# Check that all containers are running and healthy
docker-compose ps
```

**Expected output:**
```
NAME                   STATUS
quantum-postgres       Up (healthy)
quantum-rabbitmq       Up (healthy)
quantum-api            Up
quantum-worker-1       Up
quantum-worker-2       Up
quantum-worker-3       Up
```

### Monitor System Health

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f quantum-api
docker-compose logs -f quantum-worker-1
docker-compose logs -f quantum-rabbitmq

# Last N lines
docker-compose logs --tail=100
```

### Access Management UIs

- **RabbitMQ Management**: http://localhost:15672
  - Username: `quantum_user`
  - Password: `quantum_pass`
  - View: Queues, messages, connections, message rates

- **API Docs**: http://localhost:5000/docs
  - Swagger UI
  - Test endpoints interactively

### Stop the System

```bash
# Stop containers (keep data)
docker-compose stop

# Remove containers (keep volumes)
docker-compose down

# Remove everything including data
docker-compose down -v
```

---

## Testing the System

### 1. Health Check

```bash
curl http://localhost:5000/health
```

**Expected response:**
```json
{"status": "healthy"}
```

### 2. Submit a Task

```bash
RESPONSE=$(curl -s -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}')

echo $RESPONSE

# Extract task ID
TASK_ID=$(echo $RESPONSE | jq -r '.task_id')
echo "Submitted task: $TASK_ID"
```

**Expected response:**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Task submitted successfully."
}
```

### 3. Check Status While Processing

```bash
curl http://localhost:5000/tasks/$TASK_ID
```

**Expected response (while processing):**
```json
{
  "status": "pending",
  "message": "Task is still in progress."
}
```

### 4. Wait and Check Again

```bash
sleep 5
curl http://localhost:5000/tasks/$TASK_ID
```

**Expected response (after completion):**
```json
{
  "status": "completed",
  "result": {"0": 512, "1": 512}
}
```

### 5. View Worker Processing

```bash
docker-compose logs quantum-worker-1

# Should show:
# Processing task 550e8400-...
# Task 550e8400-... completed successfully
```

### 6. View RabbitMQ Queue Depth

Access http://localhost:15672 and navigate to:
- **Queues** → **task_queue**
- See message count, consumer count, message rates

### 7. Submit Multiple Tasks and Observe Load Balancing

```bash
for i in {1..10}; do
  curl -s -X POST http://localhost:5000/tasks \
    -H "Content-Type: application/json" \
    -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}' &
done

# Watch all workers process tasks
docker-compose logs -f quantum-worker-1 quantum-worker-2 quantum-worker-3
```

---

## Key Architectural Decisions

### 1. RabbitMQ for Durability

**Why not Redis?**
- Redis queue is ephemeral
- If Redis restarts, messages in queue are lost
- RabbitMQ persists to disk

**RabbitMQ guarantees:**
- Messages survive broker restarts
- Workers must ACK before removal
- Failed workers cause redelivery
- No task loss

### 2. PostgreSQL as Source of Truth

**Design principle:**
- RabbitMQ holds "todo" (pending execution)
- PostgreSQL holds "truth" (final state)

**Why this matters:**
- If RabbitMQ and Worker both crash after pickup but before ACK:
  - Message reappears in queue
  - Task status still "pending" in PostgreSQL
  - Next worker processes it again
  - Idempotent execution ensures correctness

### 3. Explicit Worker Services

**Benefits:**
- Named workers (`worker-1`, `worker-2`, `worker-3`)
- Easy to add/remove workers by editing compose file
- Clear in logs which worker processed what
- Interview-friendly (shows orchestration knowledge)

### 4. FastAPI for API Server

**Why FastAPI over Flask?**
- Async/await native
- Pydantic validation built-in
- Type safety
- Auto-generated OpenAPI docs
- Better performance under concurrent load

### 5. Health Checks for Startup Ordering

**Without health checks:**
- API starts before PostgreSQL is ready
- Crashes trying to connect

**With health checks:**
- `condition: service_healthy`
- API waits for dependencies to be ready
- Graceful startup sequence

---

## RabbitMQ vs Redis Trade-offs

| Aspect | Redis | RabbitMQ |
|--------|-------|----------|
| **Setup time** | 2 min | 5 min |
| **Queue persistence** | Optional | Built-in |
| **Message durability** | Basic | Advanced |
| **Task acknowledgment** | Manual | Automatic |
| **Redelivery on failure** | Manual | Automatic |
| **Dead letter queues** | Custom | Built-in |
| **Memory footprint** | ~10MB | ~100MB |
| **Complexity** | Low | Medium |
| **Production readiness** | Moderate | High |
| **Learning curve** | Shallow | Steeper |

**For this assignment:** RabbitMQ is the better choice because:
- ✅ No task loss even if workers crash
- ✅ Built-in redelivery handling
- ✅ Professional-grade durability guarantees
- ✅ Shows understanding of production patterns
- ✅ Only marginally more complex than Redis
- ✅ Aligns with interview expectations for Staff-level design

---

## Scalability Considerations

### Scaling Workers

```bash
# Add more worker containers by editing docker-compose.yml
# Then restart:
docker-compose up -d
```

Alternatively, use `--scale` (not recommended with explicit services):
```bash
docker-compose up -d --scale worker=5
# Creates worker-4, worker-5 (random names, less ideal)
```

### RabbitMQ Scaling

For this 2-day assignment, single RabbitMQ instance is sufficient.

Production considerations:
- RabbitMQ clustering for high availability
- Message replication across brokers
- Load balancing across replicas

### Database Scaling

PostgreSQL single instance handles moderate load.

Production considerations:
- Read replicas for queries
- Write replication for durability
- Partitioning for large task tables

---

## Monitoring and Debugging

### Check Queue Depth

```bash
# Via RabbitMQ UI
open http://localhost:15672

# Via command line
docker-compose exec rabbitmq rabbitmqctl list_queues
```

### View Message Content

```bash
# RabbitMQ Management UI shows messages
# Queues → task_queue → Get Messages
```

### Monitor Worker Activity

```bash
# Watch all workers
docker-compose logs -f quantum-worker-1 quantum-worker-2 quantum-worker-3

# Count processed tasks
docker-compose logs quantum-worker-1 | grep "completed" | wc -l
```

### Check Database State

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U quantum_user -d quantum_db

# Inside psql:
SELECT COUNT(*) FROM tasks;
SELECT status, COUNT(*) FROM tasks GROUP BY status;
SELECT id, status, created_at FROM tasks ORDER BY created_at DESC LIMIT 10;
```

---

## Quick Start

```bash
# 1. Start system
docker-compose up -d

# 2. Wait for services to be healthy
sleep 10

# 3. Check health
curl http://localhost:5000/health

# 4. Submit task
curl -X POST http://localhost:5000/tasks \
  -H "Content-Type: application/json" \
  -d '{"qc": "OPENQASM 3; qubit q; h q; measure q;"}'

# 5. Check status (replace with returned task_id)
curl http://localhost:5000/tasks/550e8400-e29b-41d4-a716-446655440000

# 6. View logs
docker-compose logs -f

# 7. Access RabbitMQ management
open http://localhost:15672

# 8. Stop system
docker-compose down
```

---

## What You'll Implement

### Core Files

- **api/app.py**: FastAPI endpoints (POST /tasks, GET /tasks/<id>, GET /health)
- **api/database.py**: PostgreSQL async connection pool
- **api/rabbitmq_client.py**: RabbitMQ message publisher
- **api/models.py**: Pydantic validation models
- **worker/worker.py**: RabbitMQ consumer + Qiskit executor
- **worker/rabbitmq_setup.py**: Queue/exchange initialization

### Configuration Files

- **docker-compose.yml**: Service orchestration
- **migrations/schema.sql**: Database schema
- **Dockerfiles**: Container definitions
- **requirements.txt**: Python dependencies

### Testing & Documentation

- **tests/test_integration.py**: Integration tests
- **README.md**: Setup and usage instructions
- **verify.sh**: Automated verification script

---

## Key Dependencies

### API Requirements (`api/requirements.txt`)

```
fastapi==0.104.1
uvicorn==0.24.0
asyncpg==0.29.0
pydantic==2.5.0
pika==1.3.2
```

### Worker Requirements (`worker/requirements.txt`)

```
pika==1.3.2
asyncpg==0.29.0
qiskit==0.43.3
qiskit-aer==0.13.2
```

---

## Architecture Strengths

1. **Durability**: RabbitMQ persists messages; no task loss
2. **Reliability**: ACK-based delivery ensures task completion
3. **Scalability**: Easy to add workers; RabbitMQ distributes load
4. **Monitoring**: RabbitMQ management UI provides visibility
5. **Separation of Concerns**: Clear roles for each component
6. **Production-Ready**: Aligns with industry best practices

---

## Architecture Limitations (By Design)

For a 2-day assignment, we accept these limitations:

- Single PostgreSQL instance (no replication)
- Single RabbitMQ instance (no clustering)
- No horizontal scaling of API server
- No metrics/monitoring beyond logs
- No automatic retry on circuit execution failure
- No circuit size validation (could accept huge circuits)

These are natural V2 enhancements after assignment completion.

---

## Summary

This architecture provides:

✅ **Asynchronous processing** with RabbitMQ  
✅ **Task integrity** - no submitted tasks are lost  
✅ **Containerization** - all components in Docker  
✅ **Modularity** - clear separation of concerns  
✅ **Production patterns** - durability, acknowledgments, load distribution  
✅ **Observability** - logs, management UI, status tracking  

The design balances **production-readiness** with **implementation simplicity** suitable for a 2-day assignment and demonstrates **Staff-level architectural thinking** by choosing RabbitMQ's durability guarantees over Redis's simplicity.
