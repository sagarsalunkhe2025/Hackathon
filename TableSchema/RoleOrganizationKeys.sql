CREATE TABLE [dbo].[RoleOrganizationKeys]
(
    [Id] bigint NOT NULL IDENTITY(1,1),
    [RoleId] bigint NOT NULL,
    [OrganizationKeyId] nvarchar(20) NOT NULL,
    [Infotype] nvarchar(50) NOT NULL,
    [Subtype] nvarchar(50) NOT NULL,
    [Action] nvarchar(5) NOT NULL
);
