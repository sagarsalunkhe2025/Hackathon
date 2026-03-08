# 🛡️ Role Assistant

### AI-Powered SAP Role Governance & Risk Analysis

**Team Hackathon Presentation**

---

## 📌 Agenda

1. Problem Statement
2. What We Aim to Achieve
3. Solution Overview
4. How It Works — Architecture & Demo
5. Key Features
6. Business Impact
7. Future Roadmap

---

## 🔴 The Problem

### SAP Role Governance is Broken

Enterprise SAP environments accumulate **thousands of roles** and **millions of user-role assignments** over time. Security and compliance teams face critical challenges:

| Challenge                    | Impact                                                                                             |
| ---------------------------- | -------------------------------------------------------------------------------------------------- |
| **Duplicate Roles**          | Roles with identical permissions but different names — wasted management effort, audit confusion   |
| **Unused Roles**             | Roles never assigned to any user — bloated landscape, increased attack surface                     |
| **Over-Privileged Users**    | Users with 20+ roles or roles granting ALL transaction codes — **SOD violations & audit failures** |
| **Expired Assignments**      | Role assignments past their expiry date still active — regulatory non-compliance                   |
| **Orphaned Assignments**     | User-role mappings pointing to deleted roles — data integrity breakdown                            |
| **No Self-Service Analysis** | Business users depend on IT for every query — **weeks of delay** for critical security insights    |

### The Core Pain Point

> _"Organizations spend **$2.5M+ annually** on manual SAP role reviews. Security teams lack real-time visibility into role risks, and business users cannot self-serve — every question requires a DBA to write SQL."_

---

## 🎯 What We Aim to Achieve

### Vision: Democratize SAP Role Intelligence

| Goal                        | Description                                                                                              |
| --------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Natural Language Access** | Let business users ask role governance questions in plain English — no SQL knowledge required            |
| **Instant Risk Detection**  | Surface over-privileged users, duplicates, and expired assignments in seconds — not weeks                |
| **AI-Powered Analysis**     | Use LLMs to generate SQL queries, analyze results, and provide actionable insights with severity ratings |
| **Proactive Governance**    | Shift from reactive audit responses to proactive, continuous role monitoring                             |
| **Risk Scoring**            | Assign quantitative risk scores to users based on role count, privileges, and expired assignments        |

### Success Metrics

- ⏱️ **Time-to-Insight**: From weeks → **seconds**
- 🔍 **Coverage**: 7 pre-built governance analyses + unlimited natural language queries
- 🎯 **Accuracy**: AI-generated SQL validated and sandboxed (SELECT-only, keyword-blocked)
- 👥 **Accessibility**: Zero SQL knowledge needed for business users

---

## 💡 Solution Overview

### Role Assistant — An AI Chat Interface for SAP Role Governance

Role Assistant is an **intelligent conversational interface** that sits on top of your SAP role data. Users type questions in natural language, and the system:

1. **Translates** the question into a safe T-SQL query using GPT-4o
2. **Executes** the query against the SAP role database
3. **Analyzes** the results with AI to generate human-readable summaries
4. **Presents** findings with severity-tagged insights, data tables, and the generated SQL for transparency

### Two Modes of Operation

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│    💬 CHAT MODE                 │     │    📊 QUICK ANALYSIS MODE       │
│                                 │     │                                 │
│  Ask anything in English:       │     │  One-click pre-built analyses:  │
│  "Show users with >10 roles"    │     │  • Duplicate Roles              │
│  "Find roles in Finance area"   │     │  • Unused Roles                 │
│  "Who has full access?"         │     │  • Over-Privileged Users        │
│                                 │     │  • Expired Assignments          │
│  AI generates SQL on-the-fly    │     │  • Orphaned Assignments         │
│  and returns insights           │     │  • Role Distribution            │
│                                 │     │  • User Risk Scoring            │
└─────────────────────────────────┘     └─────────────────────────────────┘
```

---

## ⚙️ How It Works — Architecture

### System Architecture

```
┌──────────────────────┐        ┌──────────────────────┐        ┌──────────────────┐
│                      │  REST  │                      │  HTTP  │                  │
│   FRONTEND           │◄──────►│   BACKEND API        │◄──────►│   AI / LLM       │
│   React + TypeScript │  JSON  │   ASP.NET Core 9     │        │   GPT-4o         │
│   Vite               │        │                      │        │   (OpenAI /      │
│                      │        │                      │        │    GitHub Models) │
└──────────────────────┘        └──────────┬───────────┘        └──────────────────┘
                                           │
                                           │ T-SQL (SELECT only)
                                           ▼
                                ┌──────────────────────┐
                                │                      │
                                │   SQL SERVER          │
                                │   ProfileTailor DB   │
                                │                      │
                                │   Tables:            │
                                │   • SapRoles         │
                                │   • Users            │
                                │   • SapUserRoles     │
                                │   • RoleTypes        │
                                │   • UsersGroups      │
                                └──────────────────────┘
```

### Request Flow — Natural Language to Insights

```
 USER                    FRONTEND              BACKEND                AI (GPT-4o)           DATABASE
  │                         │                      │                      │                      │
  │  "Show over-privileged  │                      │                      │                      │
  │   users in Finance"     │                      │                      │                      │
  │────────────────────────►│                      │                      │                      │
  │                         │  POST /api/chat      │                      │                      │
  │                         │─────────────────────►│                      │                      │
  │                         │                      │                      │                      │
  │                         │                      │  [Schema + Question] │                      │
  │                         │                      │─────────────────────►│                      │
  │                         │                      │                      │                      │
  │                         │                      │  ◄── SQL Query ──── │                      │
  │                         │                      │                      │                      │
  │                         │                      │  Validate & Execute  │                      │
  │                         │                      │─────────────────────────────────────────────►│
  │                         │                      │                      │                      │
  │                         │                      │  ◄──── Results ──────────────────────────── │
  │                         │                      │                      │                      │
  │                         │                      │  [Results + Question]│                      │
  │                         │                      │─────────────────────►│                      │
  │                         │                      │                      │                      │
  │                         │                      │  ◄── AI Summary ─── │                      │
  │                         │                      │                      │                      │
  │                         │  JSON Response       │                      │                      │
  │                         │◄─────────────────────│                      │                      │
  │  Summary + Insights     │                      │                      │                      │
  │  + Data Table + SQL     │                      │                      │                      │
  │◄────────────────────────│                      │                      │                      │
```

### Technology Stack

| Layer         | Technology                      | Purpose                                   |
| ------------- | ------------------------------- | ----------------------------------------- |
| **Frontend**  | React 18 + TypeScript + Vite    | Modern, fast chat UI with data tables     |
| **Backend**   | ASP.NET Core 9 (C#)             | REST API, SQL validation, orchestration   |
| **AI Engine** | GPT-4o (OpenAI / GitHub Models) | NL→SQL translation + Result summarization |
| **Database**  | Microsoft SQL Server            | SAP role data (ProfileTailor schema)      |

---

## 🔑 Key Features

### 1. 💬 Natural Language Chat

Ask questions in plain English — no SQL expertise needed.

**Example Queries:**

- _"Show me all users with more than 10 roles"_
- _"Find duplicate roles in the system"_
- _"Which users in Finance have roles expiring this month?"_
- _"List roles that grant all transaction codes"_

### 2. 📊 7 Pre-Built Governance Analyses

| #   | Analysis                  | What It Detects                                      |
| --- | ------------------------- | ---------------------------------------------------- |
| 1   | **Duplicate Roles**       | Roles with identical authorization hashes            |
| 2   | **Unused Roles**          | Roles not assigned to any active user                |
| 3   | **Over-Privileged Users** | Users with excessive roles or full-access privileges |
| 4   | **Expired Assignments**   | Role assignments past their expiry date              |
| 5   | **Orphaned Assignments**  | User-role mappings pointing to non-existent roles    |
| 6   | **Role Distribution**     | Role landscape by type and application area          |
| 7   | **User Risk Scoring**     | Composite risk score per user (weighted formula)     |

### 3. 🧠 AI-Generated Insights with Severity Ratings

Each analysis returns structured insights tagged as:

- 🔵 **Info** — Informational finding
- 🟡 **Warning** — Requires attention
- 🔴 **Critical** — Immediate action needed

### 4. 🔒 Safety & Security Built-In

| Safety Measure              | Description                                                   |
| --------------------------- | ------------------------------------------------------------- |
| **SELECT-Only Enforcement** | Only SELECT/WITH (CTE) queries allowed — no data modification |
| **Keyword Blocking**        | INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, EXEC blocked   |
| **Low Temperature (0.1)**   | Deterministic AI output for consistent SQL generation         |
| **30-Second Timeout**       | Query execution time-bounded                                  |
| **Schema Context**          | Full table definitions provided to AI for accurate queries    |

### 5. 🔍 Full Transparency

- View the AI-generated SQL query behind every answer
- Data tables show raw results for verification
- Category filters guide AI focus (Roles, Users, User Groups, Analysis)

### 6. 📈 Risk Scoring Formula

```
Risk Score = (Total Roles × 1) + (Critical Roles × 10) + (Expired Roles × 5)
```

- **Critical Roles** = Roles with `ContainAllTcodes = 1` (grant ALL transaction codes)
- Enables **prioritized remediation** — fix highest-risk users first

---

## 📈 Business Impact

### Quantifiable Value

| Metric                | Before Role Assistant      | After Role Assistant           |
| --------------------- | -------------------------- | ------------------------------ |
| **Time to Answer**    | Days to weeks (manual SQL) | **Seconds** (AI-generated)     |
| **Audience**          | DBAs & IT only             | **All business users**         |
| **Analysis Coverage** | Ad-hoc, inconsistent       | **7 standardized + unlimited** |
| **Audit Preparation** | Manual role reviews        | **Continuous, automated**      |
| **Risk Visibility**   | Periodic (quarterly)       | **Real-time, on-demand**       |

### Strategic Benefits

| Benefit                         | Description                                                                             |
| ------------------------------- | --------------------------------------------------------------------------------------- |
| **🔐 Reduced Security Risk**    | Instant detection of over-privileged users, expired assignments, and orphaned roles     |
| **📋 Audit Readiness**          | Pre-built analyses align with SOX, SOD, and GRC compliance requirements                 |
| **💰 Cost Savings**             | Eliminate manual role review cycles — estimated **60-80% reduction** in analysis effort |
| **👥 Self-Service Empowerment** | Business users get answers independently — no IT dependency                             |
| **⚡ Faster Remediation**       | Risk-scored users enable prioritized cleanup and governance actions                     |
| **📊 Data-Driven Decisions**    | Move from gut-feel to quantitative role governance                                      |

### Compliance Alignment

Role Assistant directly supports:

- **SOX Compliance** — Segregation of Duties (SOD) violation detection
- **GRC Requirements** — Continuous role monitoring and risk assessment
- **Access Certification** — Evidence for periodic access reviews
- **Least Privilege Principle** — Identify and reduce excessive permissions

---

## 🗺️ Future Roadmap

| Phase    | Enhancement                                                                  | Value                                                |
| -------- | ---------------------------------------------------------------------------- | ---------------------------------------------------- |
| **v2.0** | **Remediation Actions** — One-click role revocation and reassignment         | Close the loop from detection → action               |
| **v2.0** | **Scheduled Reports** — Automated weekly/monthly governance reports          | Proactive governance without manual effort           |
| **v2.5** | **Multi-System Support** — Analyze roles across multiple SAP systems         | Enterprise-wide visibility                           |
| **v2.5** | **SOD Rule Engine** — Built-in Segregation of Duties conflict detection      | Direct compliance violation flagging                 |
| **v3.0** | **Role Mining** — AI-suggested optimal role definitions                      | Reduce role sprawl through intelligent consolidation |
| **v3.0** | **Integration with Pathlock GRC** — Feed insights into the Pathlock platform | Unified GRC workflow                                 |

---

## 🏗️ Demo Walkthrough

### Screen 1: Welcome & Quick Prompts

> User lands on a clean chat interface with suggestion buttons: _"Show all users with more than 10 roles"_, _"Find roles granting all transaction codes"_, etc.

### Screen 2: Natural Language Query

> User types: _"Which users in the Finance department have critical access?"_
> → AI generates SQL → Executes → Returns summary with insights and data table

### Screen 3: Pre-Built Analysis

> User clicks **"Over-Privileged Users"** in sidebar
> → Runs hardcoded analysis → Returns risk-flagged users with CRITICAL/WARNING/REVIEW ratings

### Screen 4: Risk Scoring

> User clicks **"User Risk Scoring"**
> → Returns ranked list of users by composite risk score with breakdown (total roles, critical roles, expired roles)

### Screen 5: SQL Transparency

> User clicks **"Show SQL Query"** toggle
> → Sees the exact T-SQL generated by AI — full transparency for audit trail

---

## 🎯 Summary

|                     |                                                                                 |
| ------------------- | ------------------------------------------------------------------------------- |
| **Problem**         | SAP role governance is manual, slow, and inaccessible to business users         |
| **Solution**        | AI-powered chat interface that translates English → SQL → Insights              |
| **Technology**      | React + ASP.NET Core 9 + GPT-4o + SQL Server                                    |
| **Key Innovation**  | Natural language to safe, validated SQL with AI-generated governance insights   |
| **Business Impact** | Seconds instead of weeks · Self-service for all users · Continuous compliance   |
| **Differentiator**  | Safety-first design (SELECT-only, keyword blocking) + quantitative risk scoring |

---

### Thank You! 🙏

**Role Assistant** — _Ask your data, don't query it._

Questions?
