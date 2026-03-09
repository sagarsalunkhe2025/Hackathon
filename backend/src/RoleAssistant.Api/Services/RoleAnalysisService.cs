namespace RoleAssistant.Api.Services;

/// <summary>
/// Provides pre-built analysis queries for common role governance checks.
/// </summary>
public class RoleAnalysisService
{
    public record AnalysisDefinition(string Name, string Description, string Sql);

    private static readonly Dictionary<string, AnalysisDefinition> Analyses = new()
    {
        ["duplicates"] = new(
            "Duplicate Roles Detection",
            "Finds users who hold duplicate roles (roles with identical authorization sets), aggregated per user.",
            """
            ;WITH DuplicatePairs AS (
                SELECT 
                    u.UserId,
                    u.SapUserName,
                    u.FullName,
                    u.Department,
                    r1.RoleName AS RoleName1,
                    r2.RoleName AS RoleName2,
                    r1.AuthorizationsHash
                FROM dbo.Users u
                INNER JOIN dbo.SapUserRoles ur1 ON u.UserId = ur1.UserId
                INNER JOIN dbo.SapRoles r1 ON ur1.RoleName = r1.RoleName AND r1.IsRoleDeleted = 0
                INNER JOIN dbo.SapUserRoles ur2 ON u.UserId = ur2.UserId
                INNER JOIN dbo.SapRoles r2 ON ur2.RoleName = r2.RoleName AND r2.IsRoleDeleted = 0
                WHERE r1.AuthorizationsHash = r2.AuthorizationsHash
                    AND r1.RoleName < r2.RoleName
                    AND r1.AuthorizationsHash IS NOT NULL
                    AND r1.AuthorizationsHash != ''
                    AND u.IsDeleted = 0
            )
            SELECT TOP 100
                SapUserName AS [SAP User Name],
                ISNULL(FullName, '') AS [Full Name],
                ISNULL(Department, '') AS [Department],
                COUNT(*) AS [Duplicate Role Pairs],
                COUNT(DISTINCT AuthorizationsHash) AS [Distinct Auth Hashes]
            FROM DuplicatePairs
            GROUP BY UserId, SapUserName, FullName, Department
            ORDER BY COUNT(*) DESC
            """
        ),

        ["unused"] = new(
            "Unused Roles Detection",
            "Finds roles that exist in the system but are not assigned to any user, indicating potential cleanup candidates.",
            """
            SELECT TOP 100
                sr.RoleName AS [Role Name],
                sr.Description AS [Description],
                rt.Description AS [Role Type],
                sr.MainApplicationArea AS [Application Area],
                sr.LastChanged AS [Last Changed],
                sr.LicenseType AS [License Type]
            FROM dbo.SapRoles sr
            LEFT JOIN dbo.SapUserRoles sur ON sr.RoleName = sur.RoleName
            LEFT JOIN dbo.RoleTypes rt ON sr.RoleTypeId = rt.RoleTypeId
            WHERE sur.RoleName IS NULL
                AND sr.IsRoleDeleted = 0
                AND sr.IsVirtual = 0
            ORDER BY sr.LastChanged ASC
            """
        ),

        ["overprivileged"] = new(
            "Overprivileged Users Detection",
            "Identifies users with excessive role assignments or roles granting all transaction codes, indicating potential security risks.",
            """
            ;WITH UserRoleCounts AS (
                SELECT 
                    u.UserId,
                    u.SapUserName,
                    u.FullName,
                    u.Department,
                    COUNT(sur.RoleName) AS RoleCount,
                    SUM(CASE WHEN sr.ContainAllTcodes = 1 THEN 1 ELSE 0 END) AS HighPrivRoles
                FROM dbo.Users u
                INNER JOIN dbo.SapUserRoles sur ON u.UserId = sur.UserId
                LEFT JOIN dbo.SapRoles sr ON sur.RoleName = sr.RoleName AND sr.SystemId = u.SystemId
                WHERE u.IsDeleted = 0
                GROUP BY u.UserId, u.SapUserName, u.FullName, u.Department
            )
            SELECT TOP 50
                SapUserName AS [User Name],
                FullName AS [Full Name],
                Department,
                RoleCount AS [Total Roles],
                HighPrivRoles AS [High Privilege Roles],
                CASE 
                    WHEN HighPrivRoles > 0 THEN 'CRITICAL - Has roles with ALL transaction codes'
                    WHEN RoleCount > 20 THEN 'WARNING - Excessive role count'
                    WHEN RoleCount > 10 THEN 'REVIEW - Above average role count'
                    ELSE 'OK'
                END AS [Risk Level]
            FROM UserRoleCounts
            WHERE RoleCount > 10 OR HighPrivRoles > 0
            ORDER BY HighPrivRoles DESC, RoleCount DESC
            """
        ),

        ["expired"] = new(
            "Expired Role Assignments",
            "Finds role assignments that have passed their expiry date but are still in the system.",
            """
            SELECT TOP 100
                u.SapUserName AS [User Name],
                u.FullName AS [Full Name],
                u.Department,
                sur.RoleName AS [Role Name],
                sur.AssignmentDate AS [Assigned On],
                sur.RoleUntilDate AS [Expired On],
                DATEDIFF(DAY, sur.RoleUntilDate, GETDATE()) AS [Days Overdue],
                sur.AssignmentBy AS [Assigned By]
            FROM dbo.SapUserRoles sur
            INNER JOIN dbo.Users u ON sur.UserId = u.UserId
            WHERE sur.RoleUntilDate IS NOT NULL 
                AND sur.RoleUntilDate < GETDATE()
                AND u.IsDeleted = 0
            ORDER BY sur.RoleUntilDate ASC
            """
        ),

        ["orphaned"] = new(
            "Orphaned Role Assignments",
            "Finds role assignments where the role name doesn't match any existing role definition.",
            """
            SELECT TOP 100
                u.SapUserName AS [User Name],
                u.FullName AS [Full Name],
                sur.RoleName AS [Orphaned Role Name],
                sur.AssignmentDate AS [Assigned On],
                sur.AssignmentBy AS [Assigned By]
            FROM dbo.SapUserRoles sur
            INNER JOIN dbo.Users u ON sur.UserId = u.UserId
            LEFT JOIN dbo.SapRoles sr ON sur.RoleName = sr.RoleName
            WHERE sr.RoleName IS NULL
                AND u.IsDeleted = 0
            ORDER BY sur.RoleName
            """
        ),

        ["role-distribution"] = new(
            "Role Distribution by Type",
            "Shows the distribution of roles across different role types and application areas.",
            """
            SELECT 
                ISNULL(rt.Description, 'Unclassified') AS [Role Type],
                sr.MainApplicationArea AS [Application Area],
                COUNT(*) AS [Role Count],
                SUM(CASE WHEN sr.ContainAllTcodes = 1 THEN 1 ELSE 0 END) AS [Full Access Roles],
                SUM(CASE WHEN sr.IsRoleCanBeRemoved = 1 THEN 1 ELSE 0 END) AS [Removable Roles]
            FROM dbo.SapRoles sr
            LEFT JOIN dbo.RoleTypes rt ON sr.RoleTypeId = rt.RoleTypeId
            WHERE sr.IsRoleDeleted = 0
            GROUP BY rt.Description, sr.MainApplicationArea
            ORDER BY COUNT(*) DESC
            """
        ),

        ["user-risk-score"] = new(
            "User Risk Score Summary",
            "Calculates a risk score for each user based on role count, high-privilege roles, and expired assignments.",
            """
            ;WITH UserMetrics AS (
                SELECT 
                    u.UserId,
                    u.SapUserName,
                    u.FullName,
                    u.Department,
                    u.LastLogon,
                    COUNT(DISTINCT sur.RoleName) AS TotalRoles,
                    SUM(CASE WHEN sr.ContainAllTcodes = 1 THEN 1 ELSE 0 END) AS CriticalRoles,
                    SUM(CASE WHEN sur.RoleUntilDate < GETDATE() THEN 1 ELSE 0 END) AS ExpiredRoles,
                    SUM(CASE WHEN sur.IsRoleFromCompositeRole = 1 THEN 1 ELSE 0 END) AS InheritedRoles
                FROM dbo.Users u
                INNER JOIN dbo.SapUserRoles sur ON u.UserId = sur.UserId
                LEFT JOIN dbo.SapRoles sr ON sur.RoleName = sr.RoleName AND sr.SystemId = u.SystemId
                WHERE u.IsDeleted = 0
                GROUP BY u.UserId, u.SapUserName, u.FullName, u.Department, u.LastLogon
            )
            SELECT TOP 50
                SapUserName AS [User],
                FullName AS [Full Name],
                Department,
                TotalRoles AS [Total Roles],
                CriticalRoles AS [Critical Roles],
                ExpiredRoles AS [Expired Roles],
                InheritedRoles AS [Inherited Roles],
                (TotalRoles * 1 + CriticalRoles * 10 + ExpiredRoles * 5) AS [Risk Score],
                LastLogon AS [Last Logon]
            FROM UserMetrics
            ORDER BY (TotalRoles * 1 + CriticalRoles * 10 + ExpiredRoles * 5) DESC
            """
        )
    };

    public AnalysisDefinition? GetAnalysis(string type) =>
        Analyses.TryGetValue(type.ToLowerInvariant(), out var analysis) ? analysis : null;

    public Dictionary<string, string> GetAvailableAnalyses() =>
        Analyses.ToDictionary(kvp => kvp.Key, kvp => kvp.Value.Description);
}
