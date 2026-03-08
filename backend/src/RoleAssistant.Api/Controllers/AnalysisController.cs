using Microsoft.AspNetCore.Mvc;
using RoleAssistant.Api.Models;
using RoleAssistant.Api.Services;
using System.Text.Json;

namespace RoleAssistant.Api.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AnalysisController : ControllerBase
{
    private readonly RoleAnalysisService _analysisService;
    private readonly SqlExecutionService _sqlService;
    private readonly AiService _aiService;
    private readonly ILogger<AnalysisController> _logger;

    public AnalysisController(
        RoleAnalysisService analysisService,
        SqlExecutionService sqlService,
        AiService aiService,
        ILogger<AnalysisController> logger)
    {
        _analysisService = analysisService;
        _sqlService = sqlService;
        _aiService = aiService;
        _logger = logger;
    }

    /// <summary>
    /// Returns the list of available pre-built analyses.
    /// </summary>
    [HttpGet("types")]
    public ActionResult<Dictionary<string, string>> GetAnalysisTypes()
    {
        return Ok(_analysisService.GetAvailableAnalyses());
    }

    /// <summary>
    /// Runs a pre-built analysis and returns results with AI-generated insights.
    /// </summary>
    [HttpPost("run")]
    public async Task<ActionResult<ChatResponse>> RunAnalysis([FromBody] QuickAnalysisRequest request)
    {
        try
        {
            var analysis = _analysisService.GetAnalysis(request.AnalysisType);
            if (analysis is null)
            {
                return BadRequest(new ChatResponse
                {
                    Success = false,
                    Error = $"Unknown analysis type: {request.AnalysisType}. Use GET /api/analysis/types to see available options."
                });
            }

            _logger.LogInformation("Running analysis: {Type} - {Name}", request.AnalysisType, analysis.Name);

            // Execute the pre-built query
            var data = await _sqlService.ExecuteQueryAsync(analysis.Sql);

            // Generate AI insights
            var resultsJson = JsonSerializer.Serialize(data.Take(30));
            var insightsJson = await _aiService.GenerateAnalysisInsightsAsync(
                $"{analysis.Name}: {analysis.Description}",
                resultsJson,
                data.Count);

            // Parse insights
            List<AnalysisInsight>? insights = null;
            try
            {
                insights = JsonSerializer.Deserialize<List<AnalysisInsight>>(insightsJson, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });
            }
            catch (JsonException ex)
            {
                _logger.LogWarning(ex, "Failed to parse AI insights JSON, using raw text");
            }

            return Ok(new ChatResponse
            {
                Success = true,
                Summary = $"**{analysis.Name}**\n{analysis.Description}",
                SqlQuery = analysis.Sql,
                Data = data,
                AnalysisType = request.AnalysisType,
                Insights = insights
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error running analysis: {Type}", request.AnalysisType);
            return Ok(new ChatResponse
            {
                Success = false,
                Error = ex.Message,
                Summary = $"An error occurred running the analysis: {ex.Message}"
            });
        }
    }
}
