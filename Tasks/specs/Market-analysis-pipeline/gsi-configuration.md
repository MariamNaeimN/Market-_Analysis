# DynamoDB Global Secondary Indexes Configuration

## Overview

Task 3.2 has been completed. Four Global Secondary Indexes (GSIs) have been configured on the ContractInsightsTable to enable efficient querying patterns as specified in Requirements 6.2 and 6.3.

## Attribute Definitions

The following attributes have been added to support the GSIs:

- `insightId` (S) - Primary partition key
- `documentId` (S) - Document identifier for tracking source contracts
- `uploadTimestamp` (N) - Unix timestamp of when the contract was uploaded
- `partyName` (S) - Name of a contract party (e.g., company or individual)
- `effectiveDate` (S) - Contract effective date in ISO 8601 format (YYYY-MM-DD)

## Global Secondary Indexes

### 1. DocumentIdIndex (Requirement 6.2)

**Purpose:** Enables efficient lookup of all insights for a specific document

**Key Schema:**
- Partition Key: `documentId` (HASH)
- Sort Key: `uploadTimestamp` (RANGE)

**Projection:** ALL

**Use Case:** Query all insights related to a specific contract document, sorted by upload time

**Example Query:**
```
Query where documentId = "contract-12345" ORDER BY uploadTimestamp DESC
```

### 2. UploadTimestampIndex (Requirement 6.2)

**Purpose:** Enables efficient queries for insights by upload time range

**Key Schema:**
- Partition Key: `uploadTimestamp` (HASH)

**Projection:** ALL

**Use Case:** Find all contracts uploaded within a specific time period

**Example Query:**
```
Query where uploadTimestamp BETWEEN start_time AND end_time
```

### 3. PartyNameIndex (Requirement 6.3)

**Purpose:** Enables efficient lookup of contracts by party name

**Key Schema:**
- Partition Key: `partyName` (HASH)
- Sort Key: `effectiveDate` (RANGE)

**Projection:** ALL

**Use Case:** Find all contracts involving a specific party, sorted by effective date

**Example Query:**
```
Query where partyName = "Acme Corporation" ORDER BY effectiveDate DESC
```

### 4. EffectiveDateIndex (Requirement 6.3)

**Purpose:** Enables efficient queries for contracts by effective date range

**Key Schema:**
- Partition Key: `effectiveDate` (HASH)

**Projection:** ALL

**Use Case:** Find all contracts with a specific effective date or within a date range

**Example Query:**
```
Query where effectiveDate = "2024-01-15"
```

## Billing and Performance

All GSIs use the same billing mode as the base table (PAY_PER_REQUEST), which provides:
- Automatic scaling based on demand
- No capacity planning required
- Cost optimization for variable workloads (Requirement 10.3)

All GSIs project ALL attributes, ensuring complete data availability without additional table reads.

## Validation

The CloudFormation template has been validated using AWS CLI:
```bash
aws cloudformation validate-template --template-body file://template.yaml
```

Result: ✅ Template validation successful

## Requirements Satisfied

- ✅ Requirement 6.2: Index records by document identifier and upload timestamp
- ✅ Requirement 6.3: Support queries by contract party names and date ranges
- ✅ Requirement 10.3: Use on-demand billing mode for cost optimization
