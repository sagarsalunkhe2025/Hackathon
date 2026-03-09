CREATE TABLE [dbo].[RoleAuthorizations]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [AuthorizationObject] nvarchar(200) NOT NULL,
    [AuthorizationField] nvarchar(200) NOT NULL,
    [AuthorizationLowValue] nvarchar(410) NULL,
    [AuthorizationHighValue] nvarchar(200) NULL,
    [AuthIdentifier] nvarchar(400) NULL
);
