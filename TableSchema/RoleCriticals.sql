CREATE TABLE [dbo].[RoleCriticals]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [Reason] nvarchar(MAX) NOT NULL,
    [SystemId] bigint NOT NULL,
    [RoleName] nvarchar(400) NOT NULL,
    [RiskLevelId] bigint NOT NULL
);
