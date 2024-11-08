# Technical Solution and Design

## Introduction

This document describes the technical solution and design implemented to address the issues related to event logging in the application. The solution leverages the **Transactional Outbox Pattern** using PostgreSQL and Celery to ensure transactional integrity, improve performance, and provide a robust mechanism for event logging and processing.

## Problem Statement

The application initially wrote event logs synchronously to ClickHouse, leading to several issues:

- **Lack of Transactionality:** Events could be missed if the web worker failed before executing the business logic.
- **Poor User Experience:** Network errors when writing to ClickHouse directly affected the application's responsiveness.
- **Performance Issues:** ClickHouse struggled with handling a large number of small inserts, leading to inefficiencies.

## Technical Solution

To resolve these issues, we implemented the **Transactional Outbox Pattern** using PostgreSQL and Celery:

- **Transactional Integrity:** Event logs are written to an outbox table in PostgreSQL within the same transaction as the business logic.
- **Asynchronous Processing:** A Celery worker processes the outbox entries asynchronously, batching events and inserting them into ClickHouse.
- **Improved Performance:** Batching reduces the number of inserts to ClickHouse, mitigating performance issues with small inserts.
- **Decoupling:** The application is decoupled from the event processing mechanism, enhancing maintainability.

## Architecture Overview

The solution consists of the following components:

- **Django Application:**
  - Handles business logic and writes events to the outbox.
- **PostgreSQL Outbox Table:**
  - Stores event logs transactionally.
- **Celery Worker:**
  - Processes the outbox entries and inserts events into ClickHouse.
- **ClickHouse Database:**
  - Stores event logs for analysis and auditing.

**Data Flow:**

1. **User Action:**
   - A user action triggers a business operation (e.g., creating a user).
2. **Transactional Write:**
   - The application writes the business data and event log to PostgreSQL within a single transaction.
3. **Outbox Processing:**
   - Celery worker periodically fetches unprocessed events from the outbox.
4. **Batch Insertion:**
   - Events are batched and inserted into ClickHouse.
5. **Event Consumption:**
   - Events are available in ClickHouse for analytics and auditing.


## Detailed Design

### 1. **Outbox Table in PostgreSQL**

A new Django model `EventOutbox` represents the outbox table:

- **Fields:**
  - `event_type`: Type of the event.
  - `event_date_time`: Timestamp of the event.
  - `environment`: Application environment (e.g., 'Local', 'Production').
  - `event_context`: JSON field containing event payload.
  - `metadata_version`: Versioning for future schema changes.
  - `processed`: Boolean flag indicating if the event has been processed.
  - `processed_at`: Timestamp when the event was processed.

### 2. **Modifications to Business Logic**

In the `CreateUser` use case:

- **Original Approach:**
  - Directly writing event logs to ClickHouse synchronously.
- **New Approach:**
  - Writing event logs to the `EventOutbox` within the same transaction as user creation.

### 3. **Celery Worker and Task**

- **Celery Configuration:**
  - Celery is configured with Redis as the message broker.
- **Task `process_event_outbox`:**
  - Periodically fetches unprocessed events from the outbox.
  - Batches events and inserts them into ClickHouse.
  - Marks events as processed to prevent reprocessing.

### 4. **Event Insertion into ClickHouse**

- **Batching:**
  - Events are inserted in batches to improve performance.
- **Data Conversion:**
  - Event data is converted to match ClickHouse schema.
- **Error Handling:**
  - Exceptions during insertion are logged, and the task can retry failed operations.

## Event Flow

1. **Business Operation Initiated:**
   - A request to create a new user is received.

2. **Transaction Begins:**
   - A database transaction is started.

3. **User Creation:**
   - The new user is created in the `User` table.

4. **Event Logged to Outbox:**
   - An event representing the user creation is written to the `EventOutbox` table.

5. **Transaction Commits:**
   - Both the user data and event log are committed atomically.

6. **Outbox Processing by Celery:**
   - The `process_event_outbox` task fetches unprocessed events.

7. **Batch Insertion into ClickHouse:**
   - Events are inserted into the `event_log` table in ClickHouse.

8. **Event Marked as Processed:**
   - Events in the outbox are marked as processed with a timestamp.

## Error Handling and Reliability

- **Atomic Transactions:**
  - Using database transactions ensures that either both the user data and event log are saved, or neither is, preventing inconsistencies.

- **Idempotent Processing:**
  - The outbox processing task can safely retry failed operations without causing duplicate events.

- **Error Logging:**
  - Exceptions during outbox processing are logged using `structlog`, facilitating monitoring and debugging.

- **Task Retrying:**
  - Celery can be configured to automatically retry tasks in case of transient failures.

- **Outbox Clean-up:**
  - Processed events can be archived or deleted after a certain period to prevent the outbox table from growing indefinitely.

## Performance Considerations

- **Batch Processing:**
  - Events are processed in batches (e.g., 1000 at a time) to reduce the number of insert operations to ClickHouse.

- **Asynchronous Operation:**
  - Offloading event processing to Celery workers prevents delays in the main application flow, improving user experience.

- **Efficient Queries:**
  - Indexes can be added to the `EventOutbox` table to optimize query performance when fetching unprocessed events.

- **Resource Utilization:**
  - Celery workers can be scaled horizontally to handle increased load without impacting the main application.

## Trade-offs and Decisions

- **Not Using External Messaging Systems:**
  - Decided against using Kafka or RabbitMQ to keep the solution simple and within the given constraints.

- **Database Choice for Outbox:**
  - Using PostgreSQL for the outbox leverages existing infrastructure and ensures transactional integrity.

- **Avoiding ClickHouse-Specific Features:**
  - The solution avoids ClickHouse-specific ingestion methods to maintain flexibility in case of future database changes.

- **Handling Large Payloads:**
  - Storing large `event_context` payloads in PostgreSQL may impact storage but simplifies the architecture.

- **Celery vs. Custom Daemon:**
  - Chose Celery for its robustness, scalability, and familiarity within the tech stack.

## Conclusion

The implemented solution effectively addresses the initial problems by ensuring transactional integrity, improving performance, and providing a reliable event logging mechanism. By using the transactional outbox pattern and asynchronous processing with Celery, the application can handle events efficiently without impacting the user experience or system reliability.

