CREATE TABLE [dbo].[RoleAuthorizationSetCoverage]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [Object] nvarchar(100) NOT NULL,
    [HighRiskAuthorizationsId] bigint NOT NULL,
    [LastModified] datetime NULL
);
