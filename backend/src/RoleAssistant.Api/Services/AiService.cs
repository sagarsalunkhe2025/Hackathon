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
            [
                {
                    "title": "Brief title of the finding",
                    "description": "Detailed explanation of the finding and its implications",
                    "severity": "info|warning|critical"
                }
            ]
            
            Return ONLY valid JSON array. No markdown, no extra text.
            Be specific with numbers and provide actionable recommendations.
            If results are empty, return a single insight noting the clean state.
            """;

        var userMessage = $"""
            Analysis type: {analysisType}
            Results ({rowCount} rows):
            {resultsJson}
            """;

        return await CallOpenAiAsync(systemMessage, userMessage);
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
}
