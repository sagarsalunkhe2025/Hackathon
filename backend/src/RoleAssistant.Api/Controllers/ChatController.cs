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

            // Step 1: Convert natural language to SQL
            var sql = await _aiService.GenerateSqlAsync(request.Prompt, request.Category);

            // Step 2: Execute the SQL query
            var data = await _sqlService.ExecuteQueryAsync(sql);

            // Step 3: Generate human-readable summary
            var resultsJson = JsonSerializer.Serialize(data.Take(20)); // Limit for AI context
            var summary = await _aiService.GenerateSummaryAsync(request.Prompt, sql, resultsJson, data.Count);

            return Ok(new ChatResponse
            {
                Success = true,
                Summary = summary,
                SqlQuery = sql,
                Data = data,
                AnalysisType = request.Category
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
}
