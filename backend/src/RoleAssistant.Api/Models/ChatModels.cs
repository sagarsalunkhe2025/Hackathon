namespace RoleAssistant.Api.Models;

public class ChatRequest
{
    public string Prompt { get; set; } = string.Empty;
    public string? Category { get; set; } // "roles", "users", "usergroups", "analysis"
}

public class ChatResponse
{
    public string Summary { get; set; } = string.Empty;
    public string? SqlQuery { get; set; }
    public List<Dictionary<string, object?>>? Data { get; set; }
    public string? AnalysisType { get; set; }
    public List<AnalysisInsight>? Insights { get; set; }
    public bool Success { get; set; }
    public string? Error { get; set; }
}

public class AnalysisInsight
{
    public string Title { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public string Severity { get; set; } = "info"; // "info", "warning", "critical"
    public List<Dictionary<string, object?>>? RelatedData { get; set; }
}

public class QuickAnalysisRequest
{
    public string AnalysisType { get; set; } = string.Empty; // "duplicates", "unused", "overprivileged", "expired", "orphaned"
}
