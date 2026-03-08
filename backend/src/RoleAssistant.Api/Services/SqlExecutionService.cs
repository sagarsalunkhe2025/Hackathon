using Microsoft.Data.SqlClient;
using System.Text.Json;

namespace RoleAssistant.Api.Services;

/// <summary>
/// Executes SQL queries safely against the ProfileTailor database.
/// Only allows SELECT statements.
/// </summary>
public class SqlExecutionService
{
    private readonly IConfiguration _config;
    private readonly ILogger<SqlExecutionService> _logger;

    public SqlExecutionService(IConfiguration config, ILogger<SqlExecutionService> logger)
    {
        _config = config;
        _logger = logger;
    }

    /// <summary>
    /// Executes a SELECT query and returns results as a list of dictionaries.
    /// </summary>
    public async Task<List<Dictionary<string, object?>>> ExecuteQueryAsync(string sql)
    {
        // Safety check: only allow SELECT statements
        var trimmed = sql.TrimStart().TrimStart(';').TrimStart().ToUpperInvariant();
        if (!trimmed.StartsWith("SELECT") && !trimmed.StartsWith("WITH"))
        {
            throw new InvalidOperationException("Only SELECT queries are allowed.");
        }

        // Block dangerous keywords
        var blocked = new[] { "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "EXEC", "EXECUTE", "CREATE", "GRANT", "REVOKE" };
        foreach (var keyword in blocked)
        {
            // Check for keyword as a standalone word (not part of column names)
            if (System.Text.RegularExpressions.Regex.IsMatch(trimmed, $@"\b{keyword}\b") && keyword != "CREATE")
            {
                throw new InvalidOperationException($"Query contains blocked keyword: {keyword}");
            }
        }

        var connectionString = _config.GetConnectionString("ProfileTailor");
        if (string.IsNullOrWhiteSpace(connectionString))
        {
            throw new InvalidOperationException("Database connection string 'ProfileTailor' not configured.");
        }

        var results = new List<Dictionary<string, object?>>();

        await using var connection = new SqlConnection(connectionString);
        await connection.OpenAsync();

        await using var command = new SqlCommand(sql, connection)
        {
            CommandTimeout = 30
        };

        await using var reader = await command.ExecuteReaderAsync();

        while (await reader.ReadAsync())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                var name = reader.GetName(i);
                var value = reader.IsDBNull(i) ? null : reader.GetValue(i);

                // Convert DateTime to ISO string for JSON
                if (value is DateTime dt)
                    value = dt.ToString("yyyy-MM-dd HH:mm:ss");

                row[name] = value;
            }
            results.Add(row);
        }

        _logger.LogInformation("Query returned {Count} rows", results.Count);
        return results;
    }
}
