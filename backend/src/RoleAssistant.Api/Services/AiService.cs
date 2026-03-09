using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace RoleAssistant.Api.Services;

/// <summary>
/// Communicates with the OpenAI API (or Azure OpenAI) to convert natural language to SQL
/// and to generate human-readable summaries of query results.
/// </summary>
public class AiService
{
    private readonly IConfiguration _config;
    private readonly SchemaProvider _schemaProvider;
    private readonly ILogger<AiService> _logger;
    private readonly HttpClient _httpClient;

    public AiService(IConfiguration config, SchemaProvider schemaProvider, ILogger<AiService> logger)
    {
        _config = config;
        _schemaProvider = schemaProvider;
        _logger = logger;
        _httpClient = new HttpClient();
    }

    /// <summary>
    /// Classifies user intent: does this prompt need a SQL query or is it a general/follow-up question?
    /// </summary>
    public async Task<string> ClassifyIntentAsync(string userPrompt, List<Models.ConversationMessage>? history)
    {
        var historyContext = "";
        if (history is { Count: > 0 })
        {
            var recent = history.TakeLast(6);
            historyContext = "Recent conversation:\n" +
                string.Join("\n", recent.Select(m => $"{m.Role}: {m.Content}")) + "\n\n";
        }

        var systemMessage = """
            You are an intent classifier for a SAP role governance assistant.
            Given the user's message and recent conversation history, classify the intent as one of:
            - "query" — the user wants to retrieve, search, filter, count, or analyze data from the database
            - "general" — the user is asking a follow-up question, asking for explanation, clarification, or general knowledge

            Return ONLY the single word "query" or "general". No other text.

            Examples of "query":
            - "Show me all users with more than 10 roles"
            - "List duplicate roles"
            - "How many users are in the Finance department?"
            - "Find expired role assignments"

            Examples of "general":
            - "What does Authorization Hash mean?"
            - "Explain the risk level column"
            - "Why is that a problem?"
            - "Can you summarize the findings?"
            - "What should I do about these duplicates?"
            - "Hello"
            - "Thanks"
            """;

        var userMessage = $"{historyContext}Current user message: {userPrompt}";

        var result = await CallOpenAiAsync(systemMessage, userMessage);
        var intent = result.Trim().ToLowerInvariant();

        // Default to "query" if classification is unclear
        if (intent != "general" && intent != "query")
            intent = "query";

        _logger.LogInformation("Intent classified as: {Intent} for prompt: {Prompt}", intent, userPrompt);
        return intent;
    }

    /// <summary>
    /// Answers a general/follow-up question using conversation context (no SQL needed).
    /// </summary>
    public async Task<string> GenerateGeneralAnswerAsync(string userPrompt, List<Models.ConversationMessage>? history)
    {
        var systemMessage = """
            You are an expert SAP role governance analyst assistant. Answer the user's question based on
            the conversation history provided. Be helpful, concise, and specific.

            If the user asks about SAP concepts, role governance, authorization terms, or anything
            related to the domain, explain clearly.

            If the user is asking about previous results or findings in the conversation, refer to
            the conversation history to provide context-aware answers.

            Use plain text. Be concise but thorough.
            """;

        var messages = new List<object>
        {
            new { role = "system", content = systemMessage }
        };

        if (history is { Count: > 0 })
        {
            foreach (var msg in history.TakeLast(10))
            {
                messages.Add(new { role = msg.Role.ToLowerInvariant(), content = msg.Content });
            }
        }

        messages.Add(new { role = "user", content = userPrompt });

        return await CallOpenAiWithMessagesAsync(messages);
    }

    /// <summary>
    /// Converts a natural-language prompt into a SQL SELECT query using the LLM.
    /// </summary>
    public async Task<string> GenerateSqlAsync(string userPrompt, string? category)
    {
        var schemaContext = _schemaProvider.GetSchemaContext();

        var categoryHint = category switch
        {
            "roles" => "Focus on the SapRoles and RoleTypes tables.",
            "users" => "Focus on the Users table and their role assignments in SapUserRoles.",
            "usergroups" => "Focus on the UsersGroups table and how users relate to groups.",
            "analysis" => "Provide analytical queries that detect issues like duplicates, unused roles, overprivileged patterns, or expired assignments.",
            _ => ""
        };

        var systemMessage = $"""
            {schemaContext}

            {categoryHint}

            Given the user's natural language question, generate ONLY a single T-SQL SELECT query.
            Return ONLY the SQL query, no explanations, no markdown fencing, no extra text.
            The query must be safe (SELECT only) and optimized.
            """;

        var response = await CallOpenAiAsync(systemMessage, userPrompt);

        // Clean up the response - remove markdown fencing if present
        var sql = response.Trim();
        if (sql.StartsWith("```sql", StringComparison.OrdinalIgnoreCase))
            sql = sql[6..];
        if (sql.StartsWith("```"))
            sql = sql[3..];
        if (sql.EndsWith("```"))
            sql = sql[..^3];

        sql = sql.Trim();

        _logger.LogInformation("Generated SQL: {Sql}", sql);
        return sql;
    }

    /// <summary>
    /// Takes query results and generates a human-readable summary with insights.
    /// </summary>
    public async Task<string> GenerateSummaryAsync(string userPrompt, string sql, string resultsJson, int rowCount)
    {
        var systemMessage = """
            You are an expert SAP role governance analyst. Given the user's question, the SQL query that was executed,
            and the query results, produce a clear, concise, human-readable summary.

            Format your response as follows:
            1. A brief overview paragraph.
            2. Key findings as bullet points.
            3. If there are potential risks or recommendations, list them.

            Use plain text, not markdown. Be specific with numbers and names from the data.
            If the results are empty, explain what that means in context.

            IMPORTANT: At the very end of your response, you MUST include a chart configuration block to help visualize the data.
            Use this exact format on its own lines:
            [CHART_CONFIG]
            {"type": "<chart_type>", "title": "<chart_title>", "categoryKey": "<column_name>", "dataKey": "<column_name>"}
            [/CHART_CONFIG]

            Rules for chart configuration:
            - "type" must be one of: "bar", "pie", "line", "none"
            - "bar": best for comparing quantities across categories
            - "pie": best for showing proportions/distribution (use ONLY when 8 or fewer categories)
            - "line": best for trends over time or sequential data
            - "none": use when data doesn't suit visualization (e.g., text-heavy, single row, or no numeric columns)
            - "categoryKey": the column name to use for labels/x-axis (must match an exact column name from results)
            - "dataKey": the column name to use for numeric values/y-axis (must match an exact column name with numeric data)
            - "title": a short, descriptive title for the chart
            """;

        var userMessage = $"""
            User question: {userPrompt}

            SQL executed: {sql}

            Results ({rowCount} rows):
            {resultsJson}
            """;

        return await CallOpenAiAsync(systemMessage, userMessage);
    }

    /// <summary>
    /// Generates analysis insights for predefined analysis types.
    /// </summary>
    public async Task<string> GenerateAnalysisInsightsAsync(string analysisType, string resultsJson, int rowCount)
    {
        var systemMessage = """
            You are an expert SAP role governance analyst. Based on the analysis results provided,
            generate structured insights in the following JSON format:
            {
                "insights": [
                    {
                        "title": "Brief title of the finding",
                        "description": "Detailed explanation of the finding and its implications",
                        "severity": "info|warning|critical"
                    }
                ],
                "chartConfig": {
                    "type": "bar|pie|line|none",
                    "title": "Short descriptive chart title",
                    "categoryKey": "exact column name for labels/x-axis",
                    "dataKey": "exact column name for numeric values/y-axis"
                }
            }
            
            Return ONLY valid JSON object. No markdown, no extra text.
            Be specific with numbers and provide actionable recommendations.
            If results are empty, return a single insight noting the clean state and set chart type to "none".

            Chart type rules:
            - "bar": best for comparing quantities across categories
            - "pie": best for showing proportions/distribution (use ONLY when 8 or fewer categories)
            - "line": best for trends over time or sequential data
            - "none": when data doesn't suit visualization
            - categoryKey and dataKey must match exact column names from the results
            """;

        var userMessage = $"""
            Analysis type: {analysisType}
            Results ({rowCount} rows):
            {resultsJson}
            """;

        return await CallOpenAiAsync(systemMessage, userMessage);
    }

    /// <summary>
    /// Given a failed SQL query and the error message, asks the AI to fix it.
    /// </summary>
    public async Task<string> FixSqlAsync(string originalPrompt, string failedSql, string errorMessage, string? category)
    {
        var schemaContext = _schemaProvider.GetSchemaContext();

        var systemMessage = $"""
            {schemaContext}

            The following SQL query was generated for the user's question but failed with an error.
            Fix the SQL query so it executes correctly.
            Return ONLY the corrected SQL query, no explanations, no markdown fencing, no extra text.
            The query must be safe (SELECT only) and optimized.
            """;

        var userMessage = $"""
            User question: {originalPrompt}

            Failed SQL:
            {failedSql}

            Error:
            {errorMessage}
            """;

        var response = await CallOpenAiAsync(systemMessage, userMessage);

        var sql = response.Trim();
        if (sql.StartsWith("```sql", StringComparison.OrdinalIgnoreCase))
            sql = sql[6..];
        if (sql.StartsWith("```"))
            sql = sql[3..];
        if (sql.EndsWith("```"))
            sql = sql[..^3];

        sql = sql.Trim();
        _logger.LogInformation("Fixed SQL: {Sql}", sql);
        return sql;
    }

    private async Task<string> CallOpenAiAsync(string systemMessage, string userMessage)
    {
        var apiKey = _config["OpenAI:ApiKey"];
        var model = _config["OpenAI:Model"] ?? "gpt-4o";
        var endpoint = _config["OpenAI:Endpoint"] ?? "https://models.inference.ai.azure.com/chat/completions";

        if (string.IsNullOrWhiteSpace(apiKey) || apiKey == "YOUR_GITHUB_PAT_HERE")
        {
            throw new InvalidOperationException(
                "API key not configured. Set 'OpenAI:ApiKey' in appsettings.json to your GitHub PAT (for GitHub Models) or OpenAI API key.");
        }

        var request = new
        {
            model,
            messages = new[]
            {
                new { role = "system", content = systemMessage },
                new { role = "user", content = userMessage }
            },
            temperature = 0.1,
            max_tokens = 2000
        };

        var json = JsonSerializer.Serialize(request);
        var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        var response = await _httpClient.SendAsync(httpRequest);
        var responseBody = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError("OpenAI API error: {Status} {Body}", response.StatusCode, responseBody);
            throw new InvalidOperationException($"OpenAI API returned {response.StatusCode}: {responseBody}");
        }

        using var doc = JsonDocument.Parse(responseBody);
        var content = doc.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString();

        return content ?? string.Empty;
    }

    private async Task<string> CallOpenAiWithMessagesAsync(List<object> messages)
    {
        var apiKey = _config["OpenAI:ApiKey"];
        var model = _config["OpenAI:Model"] ?? "gpt-4o";
        var endpoint = _config["OpenAI:Endpoint"] ?? "https://models.inference.ai.azure.com/chat/completions";

        if (string.IsNullOrWhiteSpace(apiKey) || apiKey == "YOUR_GITHUB_PAT_HERE")
        {
            throw new InvalidOperationException(
                "API key not configured. Set 'OpenAI:ApiKey' in appsettings.json to your GitHub PAT (for GitHub Models) or OpenAI API key.");
        }

        var request = new
        {
            model,
            messages,
            temperature = 0.3,
            max_tokens = 2000
        };

        var json = JsonSerializer.Serialize(request);
        var httpRequest = new HttpRequestMessage(HttpMethod.Post, endpoint)
        {
            Content = new StringContent(json, Encoding.UTF8, "application/json")
        };
        httpRequest.Headers.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

        var response = await _httpClient.SendAsync(httpRequest);
        var responseBody = await response.Content.ReadAsStringAsync();

        if (!response.IsSuccessStatusCode)
        {
            _logger.LogError("API error: {Status} {Body}", response.StatusCode, responseBody);
            throw new InvalidOperationException($"API returned {response.StatusCode}: {responseBody}");
        }

        using var doc = JsonDocument.Parse(responseBody);
        var content = doc.RootElement
            .GetProperty("choices")[0]
            .GetProperty("message")
            .GetProperty("content")
            .GetString();

        return content ?? string.Empty;
    }
}
