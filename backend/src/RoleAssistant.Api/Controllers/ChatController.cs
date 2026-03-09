using Microsoft.AspNetCore.Mvc;
using RoleAssistant.Api.Models;
using RoleAssistant.Api.Services;
using System.Text.Json;

namespace RoleAssistant.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class ChatController : ControllerBase
{
    private readonly AiService _aiService;
    private readonly SqlExecutionService _sqlService;
    private readonly ILogger<ChatController> _logger;

    public ChatController(AiService aiService, SqlExecutionService sqlService, ILogger<ChatController> logger)
    {
        _aiService = aiService;
        _sqlService = sqlService;
        _logger = logger;
    }

    /// <summary>
    /// Main chat endpoint: takes a natural language prompt, converts to SQL via AI, 
    /// executes the query, and returns results with an AI-generated summary.
    /// </summary>
    [HttpPost]
    public async Task<ActionResult<ChatResponse>> Chat([FromBody] ChatRequest request)
    {
        try
        {
            if (string.IsNullOrWhiteSpace(request.Prompt))
            {
                return BadRequest(new ChatResponse
                {
                    Success = false,
                    Error = "Prompt is required."
                });
            }

            _logger.LogInformation("Chat request: {Prompt} (Category: {Category})", request.Prompt, request.Category);

            // Step 1: Classify intent — does this need SQL or is it a general question?
            var intent = await _aiService.ClassifyIntentAsync(request.Prompt, request.History);

            if (intent == "general")
            {
                // General/follow-up question — answer directly without SQL
                var answer = await _aiService.GenerateGeneralAnswerAsync(request.Prompt, request.History);
                return Ok(new ChatResponse
                {
                    Success = true,
                    Summary = answer
                });
            }

            // Step 2: Convert natural language to SQL
            var sql = await _aiService.GenerateSqlAsync(request.Prompt, request.Category);

            // Step 2: Execute the SQL query (retry once if it fails)
            List<Dictionary<string, object?>> data;
            try
            {
                data = await _sqlService.ExecuteQueryAsync(sql);
            }
            catch (Exception sqlEx)
            {
                _logger.LogWarning(sqlEx, "Initial SQL failed, attempting AI-assisted fix");
                sql = await _aiService.FixSqlAsync(request.Prompt, sql, sqlEx.Message, request.Category);
                data = await _sqlService.ExecuteQueryAsync(sql);
            }

            // Step 3: Generate human-readable summary
            var resultsJson = JsonSerializer.Serialize(data.Take(20)); // Limit for AI context
            var rawSummary = await _aiService.GenerateSummaryAsync(request.Prompt, sql, resultsJson, data.Count);

            // Parse chart config from AI response
            var (summary, chartConfig) = ParseChartConfig(rawSummary);

            return Ok(new ChatResponse
            {
                Success = true,
                Summary = summary,
                SqlQuery = sql,
                Data = data,
                AnalysisType = request.Category,
                ChartConfig = chartConfig
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error processing chat request");
            return Ok(new ChatResponse
            {
                Success = false,
                Error = ex.Message,
                Summary = $"An error occurred: {ex.Message}"
            });
        }
    }

    private static (string summary, ChartConfig? chartConfig) ParseChartConfig(string rawSummary)
    {
        const string startTag = "[CHART_CONFIG]";
        const string endTag = "[/CHART_CONFIG]";

        var startIdx = rawSummary.IndexOf(startTag, StringComparison.OrdinalIgnoreCase);
        if (startIdx < 0)
            return (rawSummary.Trim(), null);

        var endIdx = rawSummary.IndexOf(endTag, startIdx, StringComparison.OrdinalIgnoreCase);
        if (endIdx < 0)
            return (rawSummary[..startIdx].Trim(), null);

        var summary = rawSummary[..startIdx].Trim();
        var jsonBlock = rawSummary[(startIdx + startTag.Length)..endIdx].Trim();

        try
        {
            var chartConfig = JsonSerializer.Deserialize<ChartConfig>(jsonBlock, new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            });

            if (chartConfig is not null && chartConfig.Type == "none")
                chartConfig = null;

            return (summary, chartConfig);
        }
        catch (JsonException)
        {
            return (summary, null);
        }
    }
}
