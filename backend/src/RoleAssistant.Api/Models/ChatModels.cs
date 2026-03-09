namespace RoleAssistant.Api.Models;

public class ChatRequest
{
    public string Prompt { get; set; } = string.Empty;
    public string? Category { get; set; } // "roles", "users", "usergroups", "analysis"
    public List<ConversationMessage>? History { get; set; }
}

public class ConversationMessage
{
    public string Role { get; set; } = string.Empty; // "user" or "assistant"
    public string Content { get; set; } = string.Empty;
}

public class ChatResponse
{
    public string Summary { get; set; } = string.Empty;
    public string? SqlQuery { get; set; }
    public List<Dictionary<string, object?>>? Data { get; set; }
    public string? AnalysisType { get; set; }
    public List<AnalysisInsight>? Insights { get; set; }
    public ChartConfig? ChartConfig { get; set; }
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

public class ChartConfig
{
    public string Type { get; set; } = "bar"; // "bar", "pie", "line", "none"
    public string Title { get; set; } = string.Empty;
    public string CategoryKey { get; set; } = string.Empty;
    public string DataKey { get; set; } = string.Empty;
}

public class QuickAnalysisRequest
{
    public string AnalysisType { get; set; } = string.Empty; // "duplicates", "unused", "overprivileged", "expired", "orphaned"
}
