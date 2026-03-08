# Role Assistant - AI-Powered Role Governance Tool

An AI-powered tool for analyzing SAP role assignments. Ask questions in natural language and get SQL-driven insights about duplicate roles, unused roles, overprivileged users, and more.

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐     ┌──────────────┐
│   React + Vite  │────>│  ASP.NET Core    │────>│  OpenAI API  │     │  SQL Server  │
│   Frontend      │<────│  Web API         │<────│  (GPT-4o)    │     │  ProfileTailor│
│   :5173         │     │  :5199           │────>│              │     │              │
└─────────────────┘     └──────────────────┘     └──────────────┘     └──────────────┘
```

**Flow:**

1. User types a natural language question in the chat UI
2. Backend sends the question + database schema to OpenAI to generate a SQL SELECT query
3. Backend executes the query safely against SQL Server (SELECT only)
4. Backend sends results back to OpenAI to generate a human-readable summary
5. Frontend displays the summary, insights, data table, and the generated SQL

## Features

- **Natural Language Queries** - Ask about roles, users, permissions in plain English
- **Duplicate Role Detection** - Find roles with identical authorization sets
- **Unused Role Detection** - Identify roles not assigned to any user
- **Overprivileged User Detection** - Flag users with excessive role assignments
- **Expired Assignment Detection** - Find role assignments past their expiry date
- **Orphaned Assignment Detection** - Find assignments referencing non-existent roles
- **Role Distribution Analysis** - Breakdown by type and application area
- **User Risk Scoring** - Composite risk score based on role metrics
- **Category Filtering** - Focus queries on Roles, Users, User Groups, or Analysis
- **SQL Safety** - Only SELECT queries are allowed; dangerous keywords are blocked

## Prerequisites

- [.NET 9 SDK](https://dotnet.microsoft.com/download/dotnet/9.0)
- [Node.js 18+](https://nodejs.org/) (with npm)
- SQL Server with the `ProfileTailor` database
- OpenAI API key (from [platform.openai.com](https://platform.openai.com))

## Setup

### 1. Configure the Backend

Edit `backend/src/RoleAssistant.Api/appsettings.Development.json`:

```json
{
  "ConnectionStrings": {
    "ProfileTailor": "Server=YOUR_SERVER;Database=ProfileTailor;Trusted_Connection=True;TrustServerCertificate=True;"
  },
  "OpenAI": {
    "ApiKey": "sk-your-openai-api-key-here",
    "Model": "gpt-4o",
    "Endpoint": "https://api.openai.com/v1/chat/completions"
  }
}
```

**For Azure OpenAI**, change the endpoint:

```json
{
  "OpenAI": {
    "ApiKey": "your-azure-key",
    "Model": "your-deployment-name",
    "Endpoint": "https://your-resource.openai.azure.com/openai/deployments/your-deployment/chat/completions?api-version=2024-08-01-preview"
  }
}
```

### 2. Install Frontend Dependencies

```bash
cd frontend
npm install
```

### 3. Run from VS Code

Use the launch configurations in `.vscode/launch.json`:

- **Backend** - Builds and runs the .NET API on `http://localhost:5199`
- **Frontend** - Runs Vite dev server on `http://localhost:5173`
- **Full Stack (Backend + Frontend)** - Runs both simultaneously

Press `F5` or use the Run and Debug panel, select **"Full Stack (Backend + Frontend)"**.

### 4. Run from Terminal (alternative)

```bash
# Terminal 1 - Backend
cd backend/src/RoleAssistant.Api
dotnet run

# Terminal 2 - Frontend
cd frontend
npm run dev
```

Open **http://localhost:5173** in your browser.

## Usage

1. Type a question like _"Show me all users with more than 10 roles"_
2. Use the **category tabs** to focus on Roles, Users, User Groups, or Analysis
3. Click **Quick Analyses** in the sidebar for pre-built governance checks
4. Click **Show SQL Query** on any result to see the generated SQL
5. Data tables are scrollable and sortable

## Example Prompts

- "Which roles have the same authorization hash?"
- "Show users who haven't logged in for 90 days but still have active roles"
- "List all roles of type X assigned to users in the Finance department"
- "How many roles does each user group have on average?"
- "Find users with roles that expire in the next 30 days"

## Project Structure

```
Hackathon/
├── .vscode/
│   ├── launch.json          # Debug configurations
│   └── tasks.json           # Build tasks
├── backend/
│   ├── RoleAssistant.sln    # .NET solution file
│   └── src/
│       └── RoleAssistant.Api/
│           ├── Controllers/
│           │   ├── ChatController.cs       # NL chat endpoint
│           │   └── AnalysisController.cs   # Pre-built analyses
│           ├── Models/
│           │   └── ChatModels.cs           # Request/response DTOs
│           ├── Services/
│           │   ├── AiService.cs            # OpenAI integration
│           │   ├── RoleAnalysisService.cs  # Pre-built SQL queries
│           │   ├── SchemaProvider.cs       # DB schema for AI context
│           │   └── SqlExecutionService.cs  # Safe SQL execution
│           ├── Program.cs
│           └── appsettings.json
├── frontend/
│   ├── src/
│   │   ├── App.tsx           # Main chat UI component
│   │   ├── api.ts            # API client
│   │   ├── index.css         # Styles
│   │   └── main.tsx          # Entry point
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts        # Dev server + API proxy
└── TableSchema/              # Reference SQL table definitions
    ├── RoleTypes.sql
    ├── SapRoles.sql
    ├── SapUserRoles.sql
    ├── UserGroups.sql
    └── Users.sql
```
