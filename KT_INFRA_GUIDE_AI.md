# InfraGuide AI Knowledge Transfer

## 1. Project Overview

**InfraGuide AI** is a cloud migration intelligence platform. It analyzes an existing application repository or uploaded source folder and generates a practical cloud migration blueprint.

The platform helps answer questions such as:

- **What technology stack is this application using?**
- **How cloud-ready is the application?**
- **Which cloud provider and managed services are suitable?**
- **What migration strategy should be followed?**
- **What will the approximate monthly and annual cloud cost be?**
- **What are the risks, dependencies, and modernization opportunities?**
- **What roadmap should the migration team follow?**

The application supports:

```text
AWS
Azure
GCP
```

For **Azure** and **GCP**, pricing is fetched from cloud provider APIs through the MCP pricing layer. For **AWS**, pricing is currently generated through Groq LLM-based regional estimation.

The final output is a complete migration blueprint that includes:

- Technology stack analysis
- Cloud readiness score
- Recommended provider and cloud services
- Cost estimation
- Regional pricing comparison
- Migration strategy
- Migration roadmap
- Governance and security assessment
- AI architect reasoning
- Markdown export

## 2. Type Of Application

InfraGuide AI is a **full-stack AI-assisted cloud migration assessment tool**.

It is not just a static dashboard. It performs:

- Repository analysis
- Cloud service recommendation
- AI reasoning
- Cloud pricing lookup
- Cost estimation
- Migration planning
- Blueprint generation

The application has four major runtime parts:

```text
React Frontend
FastAPI Backend
MCP Pricing Server
Bridge API
```

The frontend collects user input. The backend analyzes the application and builds the assessment. The MCP server exposes cloud pricing tools. The bridge API connects the backend to MCP tools over HTTP.

## 3. Technology Stack

### Frontend

```text
React
TypeScript
Vite
Tailwind CSS
Lucide React Icons
```

The frontend handles:

- GitHub URL input
- Folder upload
- Required field validation
- Migration report rendering
- Cost and strategy display
- Regional pricing modal
- Markdown export

### Backend

```text
Python
FastAPI
Pydantic
Git clone / GitPython-style repository access
HTTPX
Groq API
```

The backend handles:

- Repository/folder analysis
- Cloud readiness scoring
- Provider selection
- Service recommendation
- Cost estimation
- Governance assessment
- Migration roadmap generation
- Blueprint rendering

### MCP Pricing Layer

```text
Python
MCP Server
HTTPX
Azure Retail Pricing API
Google Cloud Billing API
Redis Cache
```

The MCP pricing layer handles:

- Azure VM pricing
- Azure managed service pricing
- Azure regional pricing
- GCP compute pricing
- GCP service pricing
- GCP regional pricing
- Redis-backed pricing response cache

## 4. High-Level Architecture

```text
User
  -> React Frontend
  -> FastAPI Backend
  -> Repository Analyzer
  -> Recommendation Engine
  -> MCP Bridge API
  -> MCP Pricing Server
  -> Azure / GCP Pricing APIs
  -> Redis Cache
  -> Migration Blueprint
```

For GitHub repositories, the backend clones the repository into a temporary directory, analyzes the files, and deletes the temporary copy after analysis.

For uploaded folders, the frontend sends selected files to the backend. The backend stores them temporarily, analyzes them, and removes them after processing.

## 5. Core Features

InfraGuide AI currently supports:

- **GitHub repository analysis**
- **Private GitHub repository access token flow**
- **Folder upload analysis**
- **Technology stack detection**
- **Cloud readiness scoring**
- **Cloud provider recommendation**
- **Recommended cloud service mapping**
- **Azure pricing**
- **GCP pricing**
- **AWS LLM-based pricing**
- **Regional pricing modal**
- **Selected region cost update**
- **Markdown blueprint export**
- **Governance and security assessment**
- **Migration strategy recommendation**
- **Migration roadmap generation**
- **Redis pricing cache**

The analyzer detects signals such as:

```text
Languages
Frameworks
Runtimes
Databases
Package managers
Container files
CI/CD files
Infrastructure files
Cloud dependencies
Storage dependencies
Governance findings
```

## 6. Repository Analysis

The analyzer scans repository files and extracts technical evidence.

Examples:

If it sees `.cs` files, it detects:

```text
C#
.NET
```

If it sees ASP.NET patterns such as controllers or views, it detects:

```text
ASP.NET Core
ASP.NET Core MVC
```

If it finds Entity Framework or SQL Server signals, it detects:

```text
Entity Framework Core
SQL Server
```

If it finds Docker-related files:

```text
Dockerfile
docker-compose.yml
```

then container readiness improves and the deployment model becomes more cloud-portable.

This local static analysis gives us deterministic baseline facts before AI is used.

## 7. AI Mechanism

InfraGuide AI uses **Groq LLM** for reasoning and estimation.

The system does **not** blindly ask the LLM to invent the full answer. First, deterministic local analysis extracts facts from the repository. Then those structured facts are sent to the LLM for refinement.

AI is used for:

- Improving repository summary
- Estimating cloud sizing
- Generating architect reasoning
- Answering migration questions
- Estimating AWS pricing

The AI returns structured output where needed, usually as strict JSON.

## 8. AI Techniques Used

The application uses a **hybrid AI approach**:

```text
Rule-based analysis
LLM-enhanced reasoning
Structured JSON prompting
Fallback logic
Cloud-specific service mapping
Heuristic fallback
```

**Rule-based analysis** is used for deterministic signals like file types, frameworks, databases, containers, package managers, and CI/CD files.

**LLM-enhanced reasoning** is used where architectural judgment is useful, such as sizing, migration explanation, strategy reasoning, and AWS pricing estimation.

**Structured JSON prompting** makes the LLM output machine-readable, so the backend can safely convert AI responses into application models.

**Fallback logic** ensures the platform still produces a usable report even if Groq is unavailable or returns an invalid response.

## 9. Cloud Provider Recommendation

If the user explicitly selects a provider, the platform respects that choice:

```text
AWS
Azure
GCP
```

If provider selection is automatic, the system uses application signals.

Examples:

- ASP.NET Core + SQL Server strongly favors **Azure**
- Low-cost preference can favor **GCP**
- General cloud migration without strong provider-specific signals can favor **AWS**

## 10. Recommended Services

InfraGuide maps application needs to cloud-native services.

### Azure

```text
Application Runtime -> Azure Container Apps / Azure Functions
Database -> Azure SQL Database / Azure Database for PostgreSQL
Storage -> Azure Blob Storage
Secrets -> Azure Key Vault
Monitoring -> Azure Monitor
```

### AWS

```text
Application Runtime -> Amazon ECS Fargate / AWS Lambda
Database -> Amazon RDS
Storage -> Amazon S3
Secrets -> AWS Secrets Manager
Monitoring -> Amazon CloudWatch
```

### GCP

```text
Application Runtime -> Cloud Run / Cloud Functions
Database -> Cloud SQL
Storage -> Cloud Storage
Secrets -> Secret Manager
Monitoring -> Cloud Monitoring
```

## 11. Cloud Readiness Score

The readiness score is rule-based.

Example scoring signals:

```text
Runtime detected -> +15
Framework detected -> +10
Database dependency detected -> +10
Container configuration detected -> +15
Package manager detected -> +5
Governance/security issues -> penalty
```

The result is categorized as:

```text
Low complexity
Medium complexity
High complexity
```

This helps teams quickly understand how difficult the migration may be.

## 12. Migration Strategy

The system recommends strategies such as:

```text
Rehost
Replatform
Refactor
```

The strategy is based on:

- User migration goal
- Cloud readiness score
- Application complexity
- Container readiness
- Modernization opportunities

Example:

If the user wants modernization and the application is reasonably cloud-ready, the platform may recommend:

```text
Replatform
```

If the application needs major architecture changes, it may recommend:

```text
Refactor
```

## 13. Pricing Mechanism

### Azure Pricing

Azure pricing comes from:

```text
Azure Retail Pricing API
```

The platform fetches:

- VM pricing
- Managed service pricing
- Regional pricing

### GCP Pricing

GCP pricing comes from:

```text
Google Cloud Billing API
```

The platform fetches:

- Compute Engine pricing
- Service catalog
- Service SKUs
- SKU prices
- Regional pricing

### AWS Pricing

AWS pricing currently comes from:

```text
Groq LLM regional pricing estimate
```

The LLM returns AWS pricing in the same structure as Azure/GCP:

- Runtime monthly cost
- Services monthly cost
- Total monthly cost
- Regional rows
- Service breakdown

## 14. Redis Pricing Cache

Azure and GCP pricing APIs can be slow because pricing data is large and paginated.

To improve performance, InfraGuide uses **Redis caching**.

The Redis cache stores **pricing API responses only**.

It does **not** store:

- GitHub tokens
- Repository source code
- Private repo data
- User files
- Blueprints
- Assessment history

Cached Azure/GCP pricing data includes:

```text
Azure Retail Pricing API responses
Azure paginated VM pricing results
GCP services catalog
GCP service SKU lists
GCP SKU price responses
```

Cache behavior:

```text
First request -> call provider API -> store response in Redis
Repeated request within 24 hours -> read from Redis
After 24 hours -> Redis expires key -> next request refreshes data
```

TTL is controlled by:

```env
PRICING_CACHE_TTL_SECONDS=86400
```

`86400` seconds equals **24 hours**.

## 15. Security And Governance

The platform performs a basic governance assessment.

It checks for signals such as:

- Hardcoded secrets
- Missing CI/CD
- Missing infrastructure-as-code
- Missing containerization
- Security-sensitive configuration

The output includes:

```text
Risk level
Issues
Passed checks
Recommendations
```

This matters because migration is not only about moving compute. Teams also need secure secrets handling, monitoring, audit logs, RBAC, CI/CD, and infrastructure automation.

## 16. Business Value

InfraGuide AI targets organizations that want faster cloud migration discovery and planning.

Business value includes:

- **Faster cloud assessment**
- **Reduced manual discovery effort**
- **Early cost visibility**
- **Provider-specific service mapping**
- **Region-wise pricing comparison**
- **Better migration planning**
- **Governance risk visibility**
- **Clear stakeholder communication**
- **Downloadable migration blueprint**

Instead of manually reviewing repositories, checking pricing pages, preparing spreadsheets, and writing a migration plan, the platform generates a structured first-pass assessment quickly.

## 17. End Customers

Potential end users include:

- Application owners
- Cloud migration teams
- Enterprise architects
- DevOps teams
- Cloud consultants
- Pre-sales cloud teams
- IT modernization teams
- Small companies planning cloud migration
- Students or teams preparing migration proposals

## 18. Customer Benefits

Customers get:

- A quick understanding of application architecture
- Cloud readiness score
- Recommended cloud provider and services
- Estimated monthly and yearly cost
- Region-wise pricing comparison
- Security and governance observations
- Modernization suggestions
- Step-by-step migration roadmap
- Downloadable blueprint

The platform helps customers move from questions like:

```text
Can this app move to cloud?
Which services do we need?
How much will it cost?
What should we do first?
```

to a structured migration plan.

## 19. Why This Architecture Is Useful

The architecture is modular.

```text
Frontend -> User interaction
Backend -> Analysis and blueprint generation
MCP Server -> Pricing tools
Bridge API -> Backend-to-MCP communication
Redis -> Pricing cache
Groq -> AI reasoning and estimation
```

This separation allows future improvements without rewriting the full application.

Examples:

- Add direct AWS Pricing API later
- Add more governance checks
- Add more cloud providers
- Add architecture diagram generation
- Move Redis from local Docker to managed cloud Redis
- Add background jobs for long-running analysis

## 20. Current Limitations

Current limitations should be explained clearly during KT:

- Azure/GCP pricing depends on external APIs
- AWS pricing is currently LLM-estimated, not direct AWS Pricing API
- Repository analysis is static, not runtime profiling
- Database size and traffic are estimated if not explicitly available
- LLM output can vary slightly
- Cost estimates are planning estimates, not billing guarantees

This is expected for an assessment platform. The result should be treated as a migration planning baseline.

## 21. Future Enhancements

Possible future improvements:

- Direct AWS Pricing API integration
- More detailed infrastructure-as-code detection
- Container image analysis
- Dependency vulnerability scanning
- Architecture diagram generation
- Authentication and user accounts
- Assessment history dashboard
- Export to PDF
- More accurate database sizing
- Cost optimization recommendations
- Multi-environment pricing: dev, test, prod
- Queue/background jobs for long-running analysis

## 22. One-Minute Explanation

**InfraGuide AI is an AI-assisted cloud migration assessment platform.**

A user submits a GitHub repository or uploads a project folder. The system analyzes the application stack, detects dependencies, calculates cloud readiness, recommends provider-specific cloud services, estimates costs, and generates a migration blueprint.

It uses a hybrid approach:

```text
Static repository analysis
Rule-based scoring
Groq LLM reasoning
MCP pricing tools
Azure/GCP pricing APIs
Redis pricing cache
```

The business value is faster migration discovery, better cost visibility, reduced manual effort, and a clearer migration roadmap for application teams and decision makers.

